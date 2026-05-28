from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.models import MovimientoCredito
from apps.inventory.models import Inventario, MovimientoInventario
from apps.core.permissions.permission_codes import PermissionCodes
from apps.core.permissions.permission_service import PermissionService
from apps.products.models import PrecioProducto, VarianteProducto
from apps.sales.models import DetalleVenta, Venta

if TYPE_CHECKING:
    from apps.customers.models import Cliente


class VentaService:
    """
    Servicio de dominio para operaciones de venta.
    Toda la lógica de negocio reside aquí, no en los modelos.
    """

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    @staticmethod
    def crear_venta(
        *,
        usuario: User,
        tipo_venta: str,
        cliente=None,
    ) -> Venta:
        """
        Crea una nueva venta en estado EN_PROCESO.

        Args:
            usuario: Vendedor que crea la venta.
            tipo_venta: 'contado' o 'credito'.
            cliente: Cliente asociado (obligatorio para crédito, opcional contado).

        Returns:
            Venta creada con folio generado.
        """
        folio = VentaService._generar_folio()

        venta = Venta.objects.create(
            folio=folio,
            usuario=usuario,
            cliente=cliente,
            tipo_venta=tipo_venta,
            estado=Venta.Estado.EN_PROCESO,
            subtotal=Decimal('0.00'),
            total=Decimal('0.00'),
        )

        return venta

    @staticmethod
    def agregar_producto(
        *,
        venta_id: int,
        variante_id: int,
        cantidad: int,
    ) -> DetalleVenta:
        """
        Agrega un producto a una venta en proceso.

        - Obtiene el precio vigente de PrecioProducto.
        - Crea o actualiza el DetalleVenta.
        - Recalcula los totales de la venta.
        - NO toca inventario hasta finalizar_venta.

        Args:
            venta_id: ID de la venta.
            variante_id: ID de la variante a agregar.
            cantidad: Cantidad a agregar.

        Returns:
            DetalleVenta creado o actualizado.

        Raises:
            ValueError: Si la venta no está en proceso o no hay precio vigente.
        """
        venta = Venta.objects.get(pk=venta_id)

        if venta.estado != Venta.Estado.EN_PROCESO:
            raise ValueError(
                f'La venta {venta.folio} no está en proceso '
                f'(estado actual: {venta.get_estado_display()}).'
            )

        if cantidad <= 0:
            raise ValueError('La cantidad debe ser mayor a cero.')

        # Obtener variante y precio vigente
        variante = VarianteProducto.objects.get(pk=variante_id)

        precio_vigente = PrecioProducto.objects.filter(
            variante=variante,
            vigente=True,
        ).first()

        if precio_vigente is None:
            raise ValueError(
                f'No existe precio vigente para la variante "{variante}".'
            )

        # Validar precio a crédito
        if venta.tipo_venta == Venta.TipoVenta.CREDITO:
            if precio_vigente.precio_credito is None:
                raise ValueError(
                    f'Producto {variante} no tiene precio a crédito'
                )

        # Determinar precio según tipo de venta
        if (
            venta.tipo_venta == Venta.TipoVenta.CREDITO
            and precio_vigente.precio_credito is not None
        ):
            precio_unitario = precio_vigente.precio_credito
        else:
            precio_unitario = precio_vigente.precio_contado

        subtotal_linea = precio_unitario * cantidad

        # Crear o actualizar detalle
        detalle, created = DetalleVenta.objects.update_or_create(
            venta=venta,
            variante=variante,
            defaults={
                'cantidad': cantidad,
                'precio_unitario': precio_unitario,
                'subtotal': subtotal_linea,
            },
        )

        # Recalcular totales de la venta
        VentaService._recalcular_totales(venta)

        return detalle

    @staticmethod
    @transaction.atomic
    def finalizar_venta(
        *,
        venta_id: int,
        force_credit_override: bool = False,
        authorized_by: int | None = None,
    ) -> Venta:
        """
        Finaliza una venta: valida crédito, descuenta inventario,
        registra movimientos de crédito y cambia estado a COMPLETADA.

        Dentro de transaction.atomic:
        1. Valida estado EN_PROCESO
        2. Si es crédito → valida límite de crédito (o aplica override admin)
        3. Para cada detalle → descuenta stock, crea MovimientoInventario
        4. Si es crédito → actualiza saldo y crea MovimientoCredito
        5. Cambia estado a COMPLETADA

        Si falla cualquier validación → ValueError y atomic rollback.

        Args:
            venta_id: ID de la venta a finalizar.
            force_credit_override: Si True, omite bloqueo de límite y actualiza
                el limite_credito del cliente al nuevo saldo.
            authorized_by: ID del usuario admin que autoriza el override.

        Returns:
            Venta completada.

        Raises:
            ValueError: Estado incorrecto, stock insuficiente, o límite de crédito excedido.
        """
        venta = Venta.objects.select_for_update().select_related(
            'cliente', 'usuario',
        ).get(pk=venta_id)

        if venta.estado != Venta.Estado.EN_PROCESO:
            raise ValueError(
                f'La venta {venta.folio} no está en proceso '
                f'(estado actual: {venta.get_estado_display()}).'
            )

        detalles = venta.detalles.select_related('variante').all()

        if not detalles.exists():
            raise ValueError(
                f'La venta {venta.folio} no tiene productos.'
            )

        # ── 1. Validar crédito (si aplica) ──
        if venta.tipo_venta == Venta.TipoVenta.CREDITO:
            VentaService._validar_limite_credito(
                venta,
                force_override=force_credit_override,
                authorized_by=authorized_by,
            )

        # ── 2. Descontar inventario ──
        ahora = timezone.now()

        for detalle in detalles:
            try:
                inventario = Inventario.objects.select_for_update().get(
                    variante=detalle.variante,
                )
            except Inventario.DoesNotExist:
                raise ValueError(
                    f'No existe inventario para la variante '
                    f'"{detalle.variante}".'
                )

            if inventario.stock_actual < detalle.cantidad:
                # ── Validador RBAC: Autorización para forzar inventarios negativos ──
                PermissionService.check(venta.usuario, PermissionCodes.AUTHORIZE_STOCK_OVERRIDE)
                # Si el rol es VENDEDOR explotará en 403. 
                # Si el rol es ADMIN continuará con el flujo negativo de inventario local.

            stock_anterior = inventario.stock_actual
            stock_nuevo = stock_anterior - detalle.cantidad

            MovimientoInventario.objects.create(
                inventario=inventario,
                variante=detalle.variante,
                tipo_movimiento=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
                cantidad=-detalle.cantidad,
                stock_anterior=stock_anterior,
                stock_nuevo=stock_nuevo,
                referencia_id=venta.id,
                referencia_tipo=MovimientoInventario.ReferenciaTipo.VENTA,
                usuario=venta.usuario,
                fecha=ahora,
            )

            inventario.stock_actual = stock_nuevo
            inventario.save(update_fields=['stock_actual', 'updated_at'])

        # ── 3. Registrar crédito (si aplica) ──
        if venta.tipo_venta == Venta.TipoVenta.CREDITO:
            VentaService._registrar_movimiento_credito(venta)

        # ── 4. Completar venta ──
        venta.estado = Venta.Estado.COMPLETADA
        venta.save(update_fields=['estado', 'updated_at'])

        return venta

    # ------------------------------------------------------------------
    # Métodos privados — Crédito (extensibles a futuro)
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_limite_credito(
        venta: Venta,
        *,
        force_override: bool = False,
        authorized_by: int | None = None,
    ) -> None:
        """
        Valida que el cliente tenga crédito suficiente.

        Si force_override=True y authorized_by apunta a un usuario con
        permiso AUTHORIZE_CREDIT_EXCEED, se actualiza automáticamente
        el limite_credito del cliente al nuevo saldo resultante.

        Raises:
            ValueError: Si no hay cliente, excede límite sin override,
                o el autorizador no tiene permisos.
        """
        cliente = venta.cliente

        if cliente is None:
            raise ValueError(
                f'La venta a crédito {venta.folio} no tiene cliente asignado.'
            )

        nuevo_saldo = cliente.saldo_actual + venta.total

        if nuevo_saldo > cliente.limite_credito:
            if not force_override:
                raise ValueError(
                    f'Cliente "{cliente.nombre}" excede su límite de crédito. '
                    f'Límite=${cliente.limite_credito}, '
                    f'saldo actual=${cliente.saldo_actual}, '
                    f'venta=${venta.total}, '
                    f'saldo resultante=${nuevo_saldo}.'
                )

            # ── Override autorizado: validar permisos del autorizador ──
            if authorized_by is None:
                raise ValueError(
                    'Se requiere un usuario autorizador para forzar '
                    'el excedente de crédito.'
                )

            autorizador = User.objects.select_related('rol').get(pk=authorized_by)
            PermissionService.check(autorizador, PermissionCodes.AUTHORIZE_CREDIT_EXCEED)

            # Auto-actualizar limite_credito al nuevo saldo resultante
            limite_anterior = cliente.limite_credito
            cliente.limite_credito = nuevo_saldo
            cliente.save(update_fields=['limite_credito', 'updated_at'])
            # Log silencioso (se registra en el movimiento de crédito posterior)

    @staticmethod
    def _registrar_movimiento_credito(venta: Venta) -> None:
        """
        Registra cargo de crédito y actualiza saldo del cliente.

        Crea MovimientoCredito tipo CARGO_VENTA y actualiza
        cliente.saldo_actual con el nuevo saldo.

        Punto de extensión futuro:
        - Registrar autorizador en descripción.
        - Vincular con solicitud de autorización.
        """
        cliente = venta.cliente
        saldo_anterior = cliente.saldo_actual
        saldo_nuevo = saldo_anterior + venta.total

        MovimientoCredito.objects.create(
            cliente=cliente,
            venta=venta,
            tipo=MovimientoCredito.TipoMovimiento.CARGO_VENTA,
            monto=venta.total,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=saldo_nuevo,
            descripcion=f'Cargo por venta {venta.folio}',
            usuario=venta.usuario,
        )

        cliente.saldo_actual = saldo_nuevo
        cliente.save(update_fields=['saldo_actual', 'updated_at'])

    # ------------------------------------------------------------------
    # Métodos privados — Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def _generar_folio() -> str:
        """
        Genera folio secuencial: V-00001, V-00002, ...
        Basado en la última venta existente.
        """
        ultima_venta = (
            Venta.objects
            .order_by('-id')
            .values_list('folio', flat=True)
            .first()
        )

        if ultima_venta is None:
            return 'V-00001'

        try:
            ultimo_numero = int(ultima_venta.split('-')[1])
        except (IndexError, ValueError):
            ultimo_numero = 0

        nuevo_numero = ultimo_numero + 1
        return f'V-{nuevo_numero:05d}'

    @staticmethod
    def _recalcular_totales(venta: Venta) -> None:
        """Recalcula subtotal y total de la venta a partir de sus detalles."""
        from django.db.models import Sum

        resultado = venta.detalles.aggregate(total=Sum('subtotal'))
        subtotal = resultado['total'] or Decimal('0.00')

        venta.subtotal = subtotal
        venta.total = subtotal  # Sin descuentos por ahora
        venta.save(update_fields=['subtotal', 'total', 'updated_at'])
