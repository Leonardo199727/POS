from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Sum

from apps.cash.services.caja_service import CajaService
from apps.core.exceptions import (
    ClientRequiredError,
    InvalidPaymentDataError,
    InvalidPaymentMethodError,
    PaymentExceedsBalanceError,
    SaleNotPayableError,
    SaleOwnershipError,
)
from apps.core.permissions.permission_codes import PermissionCodes
from apps.core.permissions.permission_service import PermissionService
from apps.customers.models import Cliente, MovimientoCredito
from apps.payments.models import Pago, PagoDetalle
from apps.sales.models import Venta

if TYPE_CHECKING:
    from apps.accounts.models import User


class PagoService:
    """
    Servicio de dominio para operaciones de pago.
    Toda la lógica de negocio reside aquí, no en los modelos.

    Reglas financieras:
    - Solo monto_cliente reduce saldo_actual del cliente.
    - cargo_tarjeta se cobra al cliente pero NO afecta su deuda.
    - total_cobrado = monto_cliente + cargo_tarjeta.
    - El cargo por tarjeta solo aplica si con_intereses == True.
    - El porcentaje de tarjeta es 4.5% por defecto.

    Estados financieros de ventas a crédito:
    - COMPLETADA: venta finalizada, sin pagos aplicados aún.
    - PARCIAL: se han realizado pagos parciales, saldo pendiente > 0.
    - LIQUIDADA: saldo pendiente == 0, deuda completamente cubierta.
    """

    DEFAULT_TARJETA_INTERES = Decimal('4.5')

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def registrar_pago_contado(
        *,
        venta_id: int,
        metodos_pago: list[dict],
        usuario: User,
    ) -> Pago:
        """
        Registra el pago completo de una venta de contado.

        No afecta saldo_actual del cliente porque es contado.
        No modifica el estado de la venta (permanece COMPLETADA).

        Args:
            venta_id: ID de la venta a pagar.
            metodos_pago: Lista de dicts con metodo, monto, con_intereses, porcentaje_interes.
            usuario: Usuario que registra el pago.

        Returns:
            Pago registrado.

        Raises:
            ValueError: Si la venta no está completada o no es de contado.
        """
        venta = Venta.objects.select_related('cliente').get(pk=venta_id)

        PagoService._validar_venta_pagable(venta)

        if venta.tipo_venta != Venta.TipoVenta.CONTADO:
            raise SaleNotPayableError(
                message=f'La venta {venta.folio} no es de contado. '
                f'Use registrar_pago_credito o registrar_pago_mixto.'
            )

        monto_cliente, cargo_tarjeta, detalles_data = (
            PagoService._calcular_cargos(metodos_pago)
        )

        if monto_cliente != venta.total:
            raise InvalidPaymentDataError(
                message=f'El monto del pago (${monto_cliente}) no coincide '
                f'con el total de la venta (${venta.total}).'
            )

        pago = PagoService._crear_pago_con_detalles(
            venta=venta,
            cliente=venta.cliente,
            monto_cliente=monto_cliente,
            cargo_tarjeta=cargo_tarjeta,
            detalles_data=detalles_data,
            usuario=usuario,
        )

        PagoService._registrar_movimientos_caja(
            pago=pago,
            venta=venta,
            detalles_data=detalles_data,
            origen='venta',
            usuario=usuario,
        )

        return pago

    @staticmethod
    @transaction.atomic
    def registrar_pago_credito(
        *,
        cliente_id: int,
        metodos_pago: list[dict],
        usuario: User,
        venta_id: int | None = None,
    ) -> Pago:
        """
        Registra un abono a la cuenta de crédito de un cliente.

        Reduce saldo_actual del cliente, crea MovimientoCredito ABONO_PAGO,
        y actualiza el estado financiero de la venta (si aplica).

        Args:
            cliente_id: ID del cliente que abona.
            metodos_pago: Lista de dicts con metodo, monto, con_intereses, porcentaje_interes.
            usuario: Usuario que registra el pago.
            venta_id: Opcional, ID de la venta a la que se abona.

        Returns:
            Pago registrado.

        Raises:
            ValueError: Si el cliente no existe, monto excede saldo, o venta inválida.
        """
        cliente = Cliente.objects.select_for_update().get(pk=cliente_id)
        venta = None

        if venta_id is not None:
            venta = Venta.objects.select_for_update().select_related(
                'cliente',
            ).get(pk=venta_id)
            PagoService._validar_venta_pagable(venta)

            if venta.tipo_venta != Venta.TipoVenta.CREDITO:
                raise SaleNotPayableError(
                    message=f'La venta {venta.folio} no es de crédito.'
                )

            if venta.cliente_id != cliente.pk:
                raise SaleOwnershipError(
                    message=f'La venta {venta.folio} no pertenece al cliente '
                    f'"{cliente.nombre}".'
                )

        monto_cliente, cargo_tarjeta, detalles_data = (
            PagoService._calcular_cargos(metodos_pago)
        )

        # ── Validador RBAC: Autorización para exceder el límite de crédito del cliente ──
        if monto_cliente > cliente.saldo_actual:
            PermissionService.check(usuario, PermissionCodes.AUTHORIZE_CREDIT_EXCEED)
        else:
            PagoService._validar_monto_no_excede_saldo(cliente, monto_cliente)

        if venta is not None:
            PagoService._validar_pago_no_excede_saldo_venta(
                venta, monto_cliente,
            )

        pago = PagoService._crear_pago_con_detalles(
            venta=venta,
            cliente=cliente,
            monto_cliente=monto_cliente,
            cargo_tarjeta=cargo_tarjeta,
            detalles_data=detalles_data,
            usuario=usuario,
        )

        PagoService._registrar_abono_credito(
            pago=pago,
            cliente=cliente,
            venta=venta,
            monto=monto_cliente,
            usuario=usuario,
        )

        if venta is not None:
            PagoService._actualizar_estado_venta_credito(venta)

        PagoService._registrar_movimientos_caja(
            pago=pago,
            venta=venta,
            detalles_data=detalles_data,
            origen='abono',
            usuario=usuario,
        )

        return pago

    @staticmethod
    @transaction.atomic
    def registrar_pago_mixto(
        *,
        venta_id: int,
        metodos_pago: list[dict],
        usuario: User,
    ) -> Pago:
        """
        Registra un pago con múltiples métodos de pago.

        Si la venta es de crédito, reduce saldo_actual, crea MovimientoCredito,
        y actualiza el estado financiero de la venta.

        Args:
            venta_id: ID de la venta.
            metodos_pago: Lista de dicts con metodo, monto, con_intereses, porcentaje_interes.
            usuario: Usuario que registra el pago.

        Returns:
            Pago registrado.

        Raises:
            ValueError: Si la venta no está completada/parcial o montos no cuadran.
        """
        venta = Venta.objects.select_for_update().select_related(
            'cliente',
        ).get(pk=venta_id)

        PagoService._validar_venta_pagable(venta)

        monto_cliente, cargo_tarjeta, detalles_data = (
            PagoService._calcular_cargos(metodos_pago)
        )

        cliente = venta.cliente

        if venta.tipo_venta == Venta.TipoVenta.CREDITO:
            if cliente is None:
                raise ClientRequiredError(
                    message=f'La venta a crédito {venta.folio} no tiene '
                    f'cliente asignado.'
                )
            # ── Validador RBAC: Autorización para exceder el límite de crédito ──
            if monto_cliente > cliente.saldo_actual:
                PermissionService.check(usuario, PermissionCodes.AUTHORIZE_CREDIT_EXCEED)
            else:
                PagoService._validar_monto_no_excede_saldo(cliente, monto_cliente)
                
            PagoService._validar_pago_no_excede_saldo_venta(
                venta, monto_cliente,
            )
        else:
            if monto_cliente != venta.total:
                raise InvalidPaymentDataError(
                    message=f'La suma de montos base (${monto_cliente}) no coincide '
                    f'con el total de la venta (${venta.total}).'
                )

        pago = PagoService._crear_pago_con_detalles(
            venta=venta,
            cliente=cliente,
            monto_cliente=monto_cliente,
            cargo_tarjeta=cargo_tarjeta,
            detalles_data=detalles_data,
            usuario=usuario,
        )

        if venta.tipo_venta == Venta.TipoVenta.CREDITO:
            PagoService._registrar_abono_credito(
                pago=pago,
                cliente=cliente,
                venta=venta,
                monto=monto_cliente,
                usuario=usuario,
            )
            PagoService._actualizar_estado_venta_credito(venta)

        PagoService._registrar_movimientos_caja(
            pago=pago,
            venta=venta,
            detalles_data=detalles_data,
            origen='venta' if venta.tipo_venta == Venta.TipoVenta.CONTADO else 'abono',
            usuario=usuario,
        )

        return pago

    @staticmethod
    @transaction.atomic
    def registrar_pago_inicial(
        *,
        venta_id: int,
        metodos_pago: list[dict],
        usuario: User,
    ) -> Pago:
        """
        Registra un anticipo (pago inicial) para una venta a crédito.

        El anticipo reduce inmediatamente el saldo_actual del cliente,
        crea un MovimientoCredito tipo ABONO_PAGO, y actualiza el
        estado financiero de la venta.

        Args:
            venta_id: ID de la venta a crédito.
            metodos_pago: Lista de dicts con metodo, monto, con_intereses, porcentaje_interes.
            usuario: Usuario que registra el pago.

        Returns:
            Pago registrado.

        Raises:
            ValueError: Si la venta no es crédito, no está completada/parcial,
                       o el monto excede el saldo.
        """
        venta = Venta.objects.select_for_update().select_related(
            'cliente',
        ).get(pk=venta_id)

        PagoService._validar_venta_pagable(venta)

        if venta.tipo_venta != Venta.TipoVenta.CREDITO:
            raise SaleNotPayableError(
                message=f'La venta {venta.folio} no es de crédito. '
                f'El pago inicial solo aplica para ventas a crédito.'
            )

        cliente = venta.cliente

        if cliente is None:
            raise ClientRequiredError(
                message=f'La venta a crédito {venta.folio} no tiene '
                f'cliente asignado.'
            )

        monto_cliente, cargo_tarjeta, detalles_data = (
            PagoService._calcular_cargos(metodos_pago)
        )

        # ── Validador RBAC: Autorización para exceder el límite de crédito ──
        if monto_cliente > cliente.saldo_actual:
            PermissionService.check(usuario, PermissionCodes.AUTHORIZE_CREDIT_EXCEED)
        else:
            PagoService._validar_monto_no_excede_saldo(cliente, monto_cliente)
            
        PagoService._validar_pago_no_excede_saldo_venta(
            venta, monto_cliente,
        )

        pago = PagoService._crear_pago_con_detalles(
            venta=venta,
            cliente=cliente,
            monto_cliente=monto_cliente,
            cargo_tarjeta=cargo_tarjeta,
            detalles_data=detalles_data,
            usuario=usuario,
        )

        PagoService._registrar_abono_credito(
            pago=pago,
            cliente=cliente,
            venta=venta,
            monto=monto_cliente,
            usuario=usuario,
        )

        PagoService._actualizar_estado_venta_credito(venta)

        PagoService._registrar_movimientos_caja(
            pago=pago,
            venta=venta,
            detalles_data=detalles_data,
            origen='abono',
            usuario=usuario,
        )

        return pago

    # ------------------------------------------------------------------
    # Métodos privados — Cálculos
    # ------------------------------------------------------------------

    @staticmethod
    def _calcular_cargos(
        metodos_pago: list[dict],
    ) -> tuple[Decimal, Decimal, list[dict]]:
        """
        Calcula monto_cliente, cargo_tarjeta y prepara datos de detalle.

        Acepta "porcentaje_interes" (oficial) o "porcentaje" (alias legacy).
        Si ambas claves están presentes en el mismo dict, lanza ValueError.

        Returns:
            Tupla (monto_cliente, cargo_tarjeta, detalles_data).

        Raises:
            ValueError: Si metodos_pago está vacío o contiene datos inválidos.
        """
        if not metodos_pago:
            raise InvalidPaymentDataError(message='Debe especificar al menos un método de pago.')

        monto_cliente = Decimal('0.00')
        cargo_tarjeta = Decimal('0.00')
        detalles_data = []

        metodo_choices = {c.value.upper(): c for c in PagoDetalle.MetodoPago}

        for idx, mp in enumerate(metodos_pago, start=1):
            metodo = mp.get('metodo', '').upper()
            monto = mp.get('monto')

            if monto is None:
                raise InvalidPaymentDataError(
                    message=f'Método de pago #{idx}: falta el campo "monto".'
                )

            monto = Decimal(str(monto))

            if monto <= Decimal('0'):
                raise InvalidPaymentDataError(
                    message=f'Método de pago #{idx}: el monto debe ser mayor a cero.'
                )

            if metodo not in metodo_choices:
                raise InvalidPaymentMethodError(
                    message=f'Método de pago #{idx}: "{metodo}" no es válido. '
                    f'Opciones: {", ".join(metodo_choices.keys())}.'
                )
            metodo_db = metodo_choices[metodo].value

            con_intereses = mp.get('con_intereses', False)
            porcentaje_interes = None
            cargo_generado = Decimal('0.00')

            if metodo == 'TARJETA' and con_intereses:
                porcentaje_interes = PagoService._resolver_porcentaje(mp, idx)
                cargo_generado = (
                    monto * (porcentaje_interes / Decimal('100'))
                ).quantize(Decimal('0.01'))

            monto_cliente += monto
            cargo_tarjeta += cargo_generado

            detalles_data.append({
                'metodo_pago': metodo_db,
                'monto': monto,
                'con_intereses': con_intereses if metodo == 'TARJETA' else False,
                'porcentaje_interes': porcentaje_interes,
                'cargo_generado': cargo_generado,
            })

        return monto_cliente, cargo_tarjeta, detalles_data

    @staticmethod
    def _resolver_porcentaje(mp: dict, idx: int) -> Decimal:
        """
        Resuelve el porcentaje de interés desde el dict de método de pago.

        Claves aceptadas:
        - "porcentaje_interes" (oficial)
        - "porcentaje" (alias legacy)

        Raises:
            ValueError: Si ambas claves están presentes, o el valor es inválido.
        """
        tiene_oficial = 'porcentaje_interes' in mp
        tiene_legacy = 'porcentaje' in mp

        if tiene_oficial and tiene_legacy:
            raise InvalidPaymentDataError(
                message=f'Método de pago #{idx}: se enviaron ambas claves '
                f'"porcentaje_interes" y "porcentaje". Use solo una.'
            )

        porcentaje_raw = mp.get('porcentaje_interes') if tiene_oficial else mp.get('porcentaje')

        if porcentaje_raw is None:
            return PagoService.DEFAULT_TARJETA_INTERES

        porcentaje = Decimal(str(porcentaje_raw))

        if porcentaje < Decimal('0'):
            raise InvalidPaymentDataError(
                message=f'Método de pago #{idx}: el porcentaje no puede ser negativo '
                f'(recibido: {porcentaje}).'
            )

        if porcentaje > Decimal('100'):
            raise InvalidPaymentDataError(
                message=f'Método de pago #{idx}: el porcentaje no puede ser mayor '
                f'a 100 (recibido: {porcentaje}).'
            )

        return porcentaje

    # ------------------------------------------------------------------
    # Métodos privados — Creación
    # ------------------------------------------------------------------

    @staticmethod
    def _crear_pago_con_detalles(
        *,
        venta: Venta | None,
        cliente: Cliente | None,
        monto_cliente: Decimal,
        cargo_tarjeta: Decimal,
        detalles_data: list[dict],
        usuario: User,
    ) -> Pago:
        """
        Crea el registro Pago y sus PagoDetalle asociados.

        Args:
            venta: Venta asociada (puede ser None para abonos libres).
            cliente: Cliente asociado.
            monto_cliente: Suma de montos base.
            cargo_tarjeta: Suma de cargos por interés.
            detalles_data: Lista de dicts preparados por _calcular_cargos.
            usuario: Usuario que registra.

        Returns:
            Pago creado con sus detalles.
        """
        total_cobrado = monto_cliente + cargo_tarjeta

        pago = Pago.objects.create(
            venta=venta,
            cliente=cliente,
            monto_cliente=monto_cliente,
            cargo_tarjeta=cargo_tarjeta,
            total_cobrado=total_cobrado,
            usuario=usuario,
        )

        detalles_objs = [
            PagoDetalle(pago=pago, **detalle)
            for detalle in detalles_data
        ]
        PagoDetalle.objects.bulk_create(detalles_objs)

        return pago

    # ------------------------------------------------------------------
    # Métodos privados — Crédito y estados financieros
    # ------------------------------------------------------------------

    @staticmethod
    def _registrar_abono_credito(
        *,
        pago: Pago,
        cliente: Cliente,
        venta: Venta | None,
        monto: Decimal,
        usuario: User,
    ) -> MovimientoCredito:
        """
        Crea MovimientoCredito tipo ABONO_PAGO y actualiza saldo del cliente.

        Solo monto_cliente reduce saldo_actual (cargo_tarjeta NO).

        Args:
            pago: Pago registrado.
            cliente: Cliente al que se abona.
            venta: Venta asociada (puede ser None).
            monto: Monto que reduce el saldo (monto_cliente).
            usuario: Usuario que registra.

        Returns:
            MovimientoCredito creado.
        """
        saldo_anterior = cliente.saldo_actual
        saldo_nuevo = saldo_anterior - monto

        descripcion = f'Abono por pago #{pago.pk}'
        if venta is not None:
            descripcion += f' — Venta {venta.folio}'

        movimiento = MovimientoCredito.objects.create(
            cliente=cliente,
            venta=venta,
            pago=pago,
            tipo=MovimientoCredito.TipoMovimiento.ABONO_PAGO,
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=saldo_nuevo,
            descripcion=descripcion,
            usuario=usuario,
        )

        cliente.saldo_actual = saldo_nuevo
        cliente.save(update_fields=['saldo_actual', 'updated_at'])

        return movimiento

    @staticmethod
    def _calcular_saldo_pendiente_venta(venta: Venta) -> Decimal:
        """
        Calcula el saldo pendiente de una venta a crédito.

        Fórmula: venta.total - sum(pagos.monto_cliente)

        Se calcula dinámicamente desde los pagos registrados para
        garantizar consistencia (no se almacena en la BD).

        Args:
            venta: Venta a evaluar.

        Returns:
            Saldo pendiente como Decimal. Siempre >= 0.
        """
        total_pagado = Pago.objects.filter(
            venta=venta,
        ).aggregate(
            total=Sum('monto_cliente'),
        )['total'] or Decimal('0.00')

        saldo_pendiente = venta.total - total_pagado

        return max(saldo_pendiente, Decimal('0.00'))

    @staticmethod
    def _actualizar_estado_venta_credito(venta: Venta) -> None:
        """
        Actualiza el estado financiero de una venta a crédito según
        los pagos registrados.

        Reglas de transición:
        - saldo_pendiente == venta.total → COMPLETADA (sin pagos)
        - 0 < saldo_pendiente < venta.total → PARCIAL
        - saldo_pendiente == 0 → LIQUIDADA

        Este método SOLO se invoca para ventas a crédito y SIEMPRE
        dentro de transaction.atomic (heredado del método público).

        No modifica ventas de contado ni ventas canceladas.
        No recalcula ventas históricas.

        Args:
            venta: Venta a crédito cuyo estado se debe actualizar.
        """
        if venta.tipo_venta != Venta.TipoVenta.CREDITO:
            return

        saldo_pendiente = PagoService._calcular_saldo_pendiente_venta(venta)

        if saldo_pendiente == Decimal('0.00'):
            nuevo_estado = Venta.Estado.LIQUIDADA
        elif saldo_pendiente < venta.total:
            nuevo_estado = Venta.Estado.PARCIAL
        else:
            nuevo_estado = Venta.Estado.COMPLETADA

        if venta.estado != nuevo_estado:
            venta.estado = nuevo_estado
            venta.save(update_fields=['estado', 'updated_at'])

    # ------------------------------------------------------------------
    # Métodos privados — Integración con caja
    # ------------------------------------------------------------------

    @staticmethod
    def _registrar_movimientos_caja(
        *,
        pago: Pago,
        venta: Venta | None,
        detalles_data: list[dict],
        origen: str,
        usuario: User,
    ) -> None:
        """
        Registra los movimientos de caja correspondientes al pago.

        Crea un MovimientoCaja por cada método de pago utilizado.
        CajaService.registrar_ingreso resuelve la caja abierta
        automáticamente desde el usuario.

        Args:
            pago: Pago registrado.
            venta: Venta asociada (puede ser None).
            detalles_data: Lista de dicts con metodo_pago y monto.
            origen: Origen del movimiento (venta, abono).
            usuario: Usuario que registra.

        Raises:
            ValueError: Si no hay caja abierta para el usuario.
        """
        folio_venta = venta.folio if venta else 'sin venta'

        for detalle in detalles_data:
            metodo = detalle['metodo_pago']
            monto = Decimal(str(detalle['monto']))

            concepto = f'Pago #{pago.pk} — {folio_venta} ({metodo})'

            CajaService.registrar_ingreso(
                usuario=usuario,
                monto=monto,
                metodo_pago=metodo,
                concepto=concepto,
                origen=origen,
                referencia_id=pago.pk,
            )

    # ------------------------------------------------------------------
    # Métodos privados — Validaciones
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_venta_pagable(venta: Venta) -> None:
        """
        Valida que la venta esté en un estado que permita recibir pagos.

        Estados válidos:
        - COMPLETADA: venta finalizada, aún sin pagos parciales.
        - PARCIAL: venta con pagos parciales, aún tiene saldo pendiente.

        Raises:
            ValueError: Si la venta no está en estado pagable.
        """
        estados_pagables = {
            Venta.Estado.COMPLETADA,
            Venta.Estado.PARCIAL,
        }

        if venta.estado not in estados_pagables:
            raise SaleNotPayableError(
                message=f'La venta {venta.folio} no puede recibir pagos '
                f'(estado actual: {venta.get_estado_display()}).'
            )

    @staticmethod
    def _validar_monto_no_excede_saldo(
        cliente: Cliente,
        monto: Decimal,
    ) -> None:
        """
        Valida que el monto del pago no exceda el saldo actual del cliente.

        Raises:
            ValueError: Si monto > saldo_actual.
        """
        if monto > cliente.saldo_actual:
            raise PaymentExceedsBalanceError(
                message=f'El monto del pago (${monto}) excede el saldo actual '
                f'del cliente "{cliente.nombre}" (${cliente.saldo_actual}).'
            )

    @staticmethod
    def _validar_pago_no_excede_saldo_venta(
        venta: Venta,
        monto: Decimal,
    ) -> None:
        """
        Valida que el monto del pago no exceda el saldo pendiente
        de la venta específica.

        Previene sobrepagos a nivel de venta individual.

        Raises:
            ValueError: Si monto > saldo_pendiente de la venta.
        """
        saldo_pendiente = PagoService._calcular_saldo_pendiente_venta(venta)

        if monto > saldo_pendiente:
            raise PaymentExceedsBalanceError(
                message=f'El monto del pago (${monto}) excede el saldo pendiente '
                f'de la venta {venta.folio} (${saldo_pendiente}).'
            )
