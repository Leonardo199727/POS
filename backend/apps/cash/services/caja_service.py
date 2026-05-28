from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.cash.models import Caja, MovimientoCaja
from apps.core.permissions.permission_codes import PermissionCodes
from apps.core.permissions.permission_service import PermissionService

if TYPE_CHECKING:
    from apps.accounts.models import User


class CajaService:
    """
    Servicio de dominio para operaciones de caja.
    Toda la lógica de negocio reside aquí, no en los modelos.

    Reglas de negocio:
    - Una caja solo puede estar ABIERTA o CERRADA.
    - Una caja CERRADA NO puede reabrirse.
    - Un usuario solo puede tener UNA caja abierta al mismo tiempo.
    - Se registran movimientos de todos los métodos de pago
      para trazabilidad, pero solo EFECTIVO impacta el saldo teórico.
    - Toda operación crítica usa transaction.atomic.
    - Todos los montos son Decimal.
    """

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def abrir_caja(
        *,
        usuario: User,
        monto_inicial: Decimal,
        observaciones: str = '',
    ) -> Caja:
        """
        Abre una nueva caja para el usuario.

        Valida que el usuario no tenga una caja abierta.
        Crea la Caja en estado ABIERTA y registra un MovimientoCaja
        de tipo ENTRADA por el monto_inicial.

        Args:
            usuario: Usuario que abre la caja.
            monto_inicial: Efectivo inicial en caja.
            observaciones: Notas opcionales.

        Returns:
            Caja creada.

        Raises:
            ValueError: Si el usuario ya tiene una caja abierta,
                        o si monto_inicial < 0.
        """
        monto_inicial = Decimal(str(monto_inicial))

        if monto_inicial < Decimal('0'):
            raise ValueError(
                'El monto inicial no puede ser negativo.'
            )

        caja_existente = Caja.objects.filter(
            usuario_apertura=usuario,
            estado=Caja.Estado.ABIERTA,
        ).exists()

        if caja_existente:
            raise ValueError(
                f'El usuario "{usuario}" ya tiene una caja abierta. '
                f'Ciérrela antes de abrir una nueva.'
            )

        caja = Caja.objects.create(
            usuario_apertura=usuario,
            estado=Caja.Estado.ABIERTA,
            monto_inicial=monto_inicial,
            observaciones_cierre=observaciones,
        )

        if monto_inicial > Decimal('0'):
            MovimientoCaja.objects.create(
                caja=caja,
                tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
                metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
                monto=monto_inicial,
                concepto='Apertura de caja — monto inicial',
                origen=MovimientoCaja.Origen.MANUAL,
                usuario=usuario,
            )

        return caja

    @staticmethod
    @transaction.atomic
    def registrar_ingreso(
        *,
        usuario: User,
        monto: Decimal,
        metodo_pago: str,
        concepto: str,
        origen: str | None = None,
        referencia_id: int | None = None,
    ) -> MovimientoCaja:
        """
        Registra un ingreso (entrada) en la caja abierta del usuario.

        La caja se obtiene automáticamente desde el usuario.

        Args:
            usuario: Usuario que registra (su caja abierta se resuelve).
            monto: Monto del ingreso (> 0).
            metodo_pago: Método de pago (efectivo, tarjeta, transferencia).
            concepto: Descripción del movimiento.
            origen: Fuente del ingreso (venta, abono, manual, devolucion).
            referencia_id: ID de la entidad relacionada.

        Returns:
            MovimientoCaja creado.

        Raises:
            ValueError: Si no hay caja abierta, monto <= 0, o método inválido.
        """
        caja = CajaService._obtener_caja_abierta_o_error(usuario)

        CajaService._validar_monto_positivo(monto)
        metodo_db = CajaService._validar_metodo_pago(metodo_pago)
        origen_db = CajaService._validar_origen(origen) if origen else None

        movimiento = MovimientoCaja.objects.create(
            caja=caja,
            tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
            metodo_pago=metodo_db,
            monto=monto,
            concepto=concepto,
            origen=origen_db,
            referencia_id=referencia_id,
            usuario=usuario,
        )

        return movimiento

    @staticmethod
    @transaction.atomic
    def registrar_retiro(
        *,
        usuario: User,
        monto: Decimal,
        concepto: str,
    ) -> MovimientoCaja:
        """
        Registra un retiro (salida) de efectivo de la caja abierta del usuario.

        Los retiros siempre son en efectivo.
        La caja se obtiene automáticamente desde el usuario.

        Args:
            usuario: Usuario que registra (su caja abierta se resuelve).
            monto: Monto del retiro (> 0).
            concepto: Descripción/motivo del retiro.

        Returns:
            MovimientoCaja creado.

        Raises:
            ValueError: Si no hay caja abierta o monto <= 0.
        """
        caja = CajaService._obtener_caja_abierta_o_error(usuario)

        CajaService._validar_monto_positivo(monto)

        movimiento = MovimientoCaja.objects.create(
            caja=caja,
            tipo=MovimientoCaja.TipoMovimiento.SALIDA,
            metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
            monto=monto,
            concepto=concepto,
            origen=MovimientoCaja.Origen.MANUAL,
            usuario=usuario,
        )

        return movimiento

    @staticmethod
    @transaction.atomic
    def cerrar_caja(
        *,
        usuario: User,
        total_efectivo_contado: Decimal,
        total_tarjeta_declarado: Decimal = Decimal('0.00'),
        total_transferencia_declarado: Decimal = Decimal('0.00'),
        observaciones: str = '',
    ) -> Caja:
        """
        Cierra la caja abierta del usuario calculando totales y diferencias.

        La caja se obtiene automáticamente desde el usuario.

        Proceso:
        1. Obtiene la caja abierta del usuario
        2. Calcula totales esperados por método de pago desde MovimientoCaja
        3. Calcula diferencias (contado/declarado - esperado)
        4. Guarda todos los campos de cierre
        5. Cambia estado a CERRADA

        Una caja CERRADA no puede reabrirse.

        Args:
            usuario: Usuario que cierra la caja.
            total_efectivo_contado: Efectivo contado físicamente.
            total_tarjeta_declarado: Total de tarjeta declarado.
            total_transferencia_declarado: Total de transferencia declarado.
            observaciones: Notas del cierre.

        Returns:
            Caja cerrada con totales y diferencias calculados.

        Raises:
            ValueError: Si no hay caja abierta.
        """
        # ── Validador RBAC: Autorización para ejecutar corte de caja ──
        PermissionService.check(usuario, PermissionCodes.CLOSE_CASH_REGISTER)

        caja = CajaService._obtener_caja_abierta_o_error(usuario)

        total_efectivo_contado = Decimal(str(total_efectivo_contado))
        total_tarjeta_declarado = Decimal(str(total_tarjeta_declarado))
        total_transferencia_declarado = Decimal(str(total_transferencia_declarado))

        # ── Calcular totales esperados ──
        esperados = CajaService._calcular_totales_esperados(caja)

        # ── Calcular diferencias ──
        diferencia_efectivo = total_efectivo_contado - esperados['efectivo']
        diferencia_tarjeta = total_tarjeta_declarado - esperados['tarjeta']
        diferencia_transferencia = (
            total_transferencia_declarado - esperados['transferencia']
        )

        # ── Actualizar caja ──
        ahora = timezone.now()

        caja.usuario_cierre = usuario
        caja.estado = Caja.Estado.CERRADA
        caja.fecha_cierre = ahora

        caja.total_efectivo_esperado = esperados['efectivo']
        caja.total_tarjeta_esperado = esperados['tarjeta']
        caja.total_transferencia_esperado = esperados['transferencia']

        caja.total_efectivo_contado = total_efectivo_contado
        caja.total_tarjeta_declarado = total_tarjeta_declarado
        caja.total_transferencia_declarado = total_transferencia_declarado

        caja.diferencia_efectivo = diferencia_efectivo
        caja.diferencia_tarjeta = diferencia_tarjeta
        caja.diferencia_transferencia = diferencia_transferencia

        if observaciones:
            caja.observaciones_cierre = observaciones

        caja.save(update_fields=[
            'usuario_cierre',
            'estado',
            'fecha_cierre',
            'total_efectivo_esperado',
            'total_tarjeta_esperado',
            'total_transferencia_esperado',
            'total_efectivo_contado',
            'total_tarjeta_declarado',
            'total_transferencia_declarado',
            'diferencia_efectivo',
            'diferencia_tarjeta',
            'diferencia_transferencia',
            'observaciones_cierre',
            'updated_at',
        ])

        return caja

    @staticmethod
    def obtener_caja_abierta(usuario: User) -> Caja | None:
        """
        Retorna la caja abierta del usuario, o None si no tiene.

        Args:
            usuario: Usuario a consultar.

        Returns:
            Caja abierta o None.
        """
        return Caja.objects.filter(
            usuario_apertura=usuario,
            estado=Caja.Estado.ABIERTA,
        ).first()

    # ------------------------------------------------------------------
    # Métodos privados — Cálculos
    # ------------------------------------------------------------------

    @staticmethod
    def _calcular_totales_esperados(caja: Caja) -> dict[str, Decimal]:
        """
        Calcula los totales esperados por método de pago para una caja.

        Todos los cálculos se basan EXCLUSIVAMENTE en MovimientoCaja.
        monto_inicial NO se suma manualmente porque ya existe como movimiento.
        """

        movimientos = caja.movimientos.all()

        # ── EFECTIVO ──
        entradas_efectivo = movimientos.filter(
            tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
            metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        salidas_efectivo = movimientos.filter(
            tipo=MovimientoCaja.TipoMovimiento.SALIDA,
            metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        total_efectivo = (
            entradas_efectivo - salidas_efectivo
        ).quantize(Decimal('0.01'))

        # ── TARJETA ──
        total_tarjeta = (
            movimientos.filter(
                tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
                metodo_pago=MovimientoCaja.MetodoPago.TARJETA,
            ).aggregate(total=Sum('monto'))['total']
            or Decimal('0.00')
        ).quantize(Decimal('0.01'))

        # ── TRANSFERENCIA ──
        total_transferencia = (
            movimientos.filter(
                tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
                metodo_pago=MovimientoCaja.MetodoPago.TRANSFERENCIA,
            ).aggregate(total=Sum('monto'))['total']
            or Decimal('0.00')
        ).quantize(Decimal('0.01'))

        return {
            'efectivo': total_efectivo,
            'tarjeta': total_tarjeta,
            'transferencia': total_transferencia,
        }   


    # ------------------------------------------------------------------
    # Métodos privados — Validaciones
    # ------------------------------------------------------------------

    @staticmethod
    def _obtener_caja_abierta_o_error(usuario: User) -> Caja:
        """
        Obtiene la caja abierta del usuario con SELECT FOR UPDATE.

        Raises:
            ValueError: Si no existe caja abierta para el usuario,
                        o si hay más de una (protección).

        Returns:
            Caja abierta con lock de fila.
        """
        cajas = Caja.objects.select_for_update().filter(
            usuario_apertura=usuario,
            estado=Caja.Estado.ABIERTA,
        )

        count = cajas.count()

        if count == 0:
            raise ValueError(
                f'No existe caja abierta para el usuario "{usuario}". '
                f'Abra una caja antes de continuar.'
            )

        if count > 1:
            raise ValueError(
                f'El usuario "{usuario}" tiene {count} cajas abiertas. '
                f'Esto no debería ocurrir. Contacte al administrador.'
            )

        return cajas.first()

    @staticmethod
    def _validar_caja_abierta(caja: Caja) -> None:
        """
        Valida que la caja esté en estado ABIERTA.

        Raises:
            ValueError: Si la caja está cerrada.
        """
        if caja.estado != Caja.Estado.ABIERTA:
            raise ValueError(
                f'La caja #{caja.pk} está cerrada. '
                f'No se pueden registrar operaciones ni reabrirla.'
            )

    @staticmethod
    def _validar_monto_positivo(monto: Decimal) -> None:
        """
        Valida que el monto sea mayor a cero.

        Raises:
            ValueError: Si monto <= 0.
        """
        monto = Decimal(str(monto))
        if monto <= Decimal('0'):
            raise ValueError(
                f'El monto debe ser mayor a cero (recibido: ${monto}).'
            )

    @staticmethod
    def _validar_metodo_pago(metodo: str) -> str:
        """
        Valida y normaliza el método de pago.

        Returns:
            Valor del método de pago para la BD.

        Raises:
            ValueError: Si el método no es válido.
        """
        metodo_choices = {
            c.value.upper(): c.value
            for c in MovimientoCaja.MetodoPago
        }
        metodo_upper = metodo.upper()

        if metodo_upper not in metodo_choices:
            raise ValueError(
                f'Método de pago "{metodo}" no es válido. '
                f'Opciones: {", ".join(metodo_choices.keys())}.'
            )

        return metodo_choices[metodo_upper]

    @staticmethod
    def _validar_origen(origen: str) -> str:
        """
        Valida y normaliza el origen del movimiento.

        Returns:
            Valor del origen para la BD.

        Raises:
            ValueError: Si el origen no es válido.
        """
        origen_choices = {
            c.value.upper(): c.value
            for c in MovimientoCaja.Origen
        }
        origen_upper = origen.upper()

        if origen_upper not in origen_choices:
            raise ValueError(
                f'Origen "{origen}" no es válido. '
                f'Opciones: {", ".join(origen_choices.keys())}.'
            )

        return origen_choices[origen_upper]
