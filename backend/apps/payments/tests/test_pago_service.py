from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from apps.core.exceptions import (
    BusinessLogicError,
    PermissionDeniedError,
    PaymentExceedsBalanceError,
    SaleNotPayableError,
)
from apps.customers.models import Cliente
from apps.inventory.models import Inventario
from apps.payments.models import Pago
from apps.payments.services.pago_service import PagoService
from apps.sales.models import Venta, DetalleVenta
from apps.sales.services.venta_service import VentaService
from apps.cash.models import Caja
from apps.accounts.models import User as Usuario
from apps.security.models import Rol


class PagoServiceTests(TestCase):
    """
    Tests estrátegicos para blindar el núcleo financiero de PagoService.
    Se prueba directamente la capa de negocio usando Decimal y transacciones reales.
    """

    def setUp(self):
        self.rol_admin = Rol.objects.create(nombre="ADMIN")
        # 1. Crear usuario base
        self.usuario = Usuario.objects.create(
            username="testuser",
            password="testpassword",
            is_superuser=True,
            rol=self.rol_admin
        )
        
        # 2. Configurar Caja Abierta (necesaria para registrar_ingreso)
        self.caja = Caja.objects.create(
            usuario_apertura=self.usuario,
            estado=Caja.Estado.ABIERTA,
            monto_inicial=Decimal("1000.00")
        )

        # 3. Crear Cliente con límite de crédito
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            limite_credito=Decimal("5000.00"),
            saldo_actual=Decimal("0.00")
        )

        # 4. Configurar Inventario
        from apps.products.models import Producto, VarianteProducto
        producto = Producto.objects.create(
            nombre="Producto Test",
            codigo_interno="TEST-001"
        )
        self.variante = VarianteProducto.objects.create(
            producto=producto,
            nombre="Default",
            es_default=True
        )
        self.inventario = Inventario.objects.create(
            variante=self.variante,
            stock_actual=10,
            stock_minimo=2
        )

    def _crear_venta_credito(self) -> Venta:
        """Helper para crear una venta a crédito estandarizada en los tests."""
        venta = Venta.objects.create(
            folio="TEST-V-001",
            usuario=self.usuario,
            cliente=self.cliente,
            tipo_venta=Venta.TipoVenta.CREDITO,
            estado=Venta.Estado.EN_PROCESO,
            subtotal=Decimal("0.00"),
            total=Decimal("0.00")
        )
        # Añadir un detalle que suba el total a 1100.00 M.N.
        DetalleVenta.objects.create(
            venta=venta,
            variante=self.variante,
            cantidad=1,
            precio_unitario=Decimal("1100.00"),
            subtotal=Decimal("1100.00")
        )
        venta.total = Decimal("1100.00")
        venta.subtotal = Decimal("1100.00")
        venta.save()
        
        # Simular finalización de venta
        VentaService.finalizar_venta(
            venta_id=venta.id
        )
        
        venta.refresh_from_db()
        self.cliente.refresh_from_db()
        return venta

    def test_pago_parcial_deja_venta_en_parcial(self):
        venta = self._crear_venta_credito()
        saldo_inicial = self.cliente.saldo_actual  # 1100.00
        monto_pago = Decimal("500.00")

        pago = PagoService.registrar_pago_credito(
            venta_id=venta.id,
            cliente_id=self.cliente.id,
            metodos_pago=[{'metodo': 'EFECTIVO', 'monto': monto_pago}],
            usuario=self.usuario,
        )

        venta.refresh_from_db()
        self.cliente.refresh_from_db()

        self.assertEqual(venta.estado, Venta.Estado.PARCIAL)
        monto_calculado = venta.total - PagoService._calcular_saldo_pendiente_venta(venta)
        self.assertEqual(monto_calculado, monto_pago)
        
        saldo_esperado = saldo_inicial - monto_pago
        self.assertEqual(self.cliente.saldo_actual, saldo_esperado)

        movimientos = self.cliente.movimientos_credito.order_by('-fecha')
        ultimo_movimiento = movimientos.first()
        self.assertIsNotNone(ultimo_movimiento)
        self.assertEqual(ultimo_movimiento.tipo, 'abono')
        self.assertEqual(ultimo_movimiento.monto, monto_pago)

    def test_pago_total_liquida_venta(self):
        venta = self._crear_venta_credito()
        monto_total = Decimal("1100.00")

        pago = PagoService.registrar_pago_credito(
            venta_id=venta.id,
            cliente_id=self.cliente.id,
            metodos_pago=[{'metodo': 'EFECTIVO', 'monto': monto_total}],
            usuario=self.usuario,
        )

        venta.refresh_from_db()
        self.cliente.refresh_from_db()

        self.assertEqual(venta.estado, Venta.Estado.LIQUIDADA)
        monto_calculado = venta.total - PagoService._calcular_saldo_pendiente_venta(venta)
        self.assertEqual(monto_calculado, monto_total)
        self.assertEqual(self.cliente.saldo_actual, Decimal("0.00"))

    def test_pago_excede_saldo_lanza_excepcion(self):
        venta = self._crear_venta_credito()
        saldo_antes = self.cliente.saldo_actual # 1100.00
        movimientos_antes = self.cliente.movimientos_credito.count()

        monto_excesivo = Decimal("1500.00")

        with self.assertRaises(PaymentExceedsBalanceError):
            PagoService.registrar_pago_credito(
                venta_id=venta.id,
                cliente_id=self.cliente.id,
                metodos_pago=[{'metodo': 'EFECTIVO', 'monto': monto_excesivo}],
                usuario=self.usuario,
            )

        venta.refresh_from_db()
        self.cliente.refresh_from_db()

        self.assertEqual(venta.estado, Venta.Estado.COMPLETADA)
        self.assertEqual(self.cliente.saldo_actual, saldo_antes)
        self.assertEqual(self.cliente.movimientos_credito.count(), movimientos_antes)

    def test_pago_sin_caja_abierta_lanza_error(self):
        venta = self._crear_venta_credito()
        
        # Cerrar la caja explícitamente simulando fin del día
        self.caja.estado = Caja.Estado.CERRADA
        self.caja.save()

        # Debe lanzar excepción porque el usuario no tiene caja abierta (Exception o BusinessLogicError/CajaCerradaError)
        with self.assertRaises(Exception):
            PagoService.registrar_pago_credito(
                venta_id=venta.id,
                cliente_id=self.cliente.id,
                metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("100.00")}],
                usuario=self.usuario,
            )
            
        venta.refresh_from_db()
        monto_calculado = venta.total - PagoService._calcular_saldo_pendiente_venta(venta)
        self.assertEqual(monto_calculado, Decimal("0.00"))

    def test_ledger_consistencia_post_pago(self):
        venta = self._crear_venta_credito()
        
        # Abono 1: $400.00
        PagoService.registrar_pago_credito(
            venta_id=venta.id,
            cliente_id=self.cliente.id,
            metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("400.00")}],
            usuario=self.usuario,
        )
        
        # Abono 2: $300.00
        PagoService.registrar_pago_credito(
            venta_id=venta.id,
            cliente_id=self.cliente.id,
            metodos_pago=[{'metodo': 'TRANSFERENCIA', 'monto': Decimal("300.00")}],
            usuario=self.usuario,
        )

        self.cliente.refresh_from_db()
        
        self.assertEqual(self.cliente.saldo_actual, Decimal("400.00"))

        movimientos = list(self.cliente.movimientos_credito.order_by('fecha', 'id'))
        self.assertEqual(len(movimientos), 3)

        m1 = movimientos[0]
        self.assertEqual(m1.tipo, 'cargo')
        self.assertEqual(m1.saldo_nuevo, Decimal("1100.00"))

        m2 = movimientos[1]
        self.assertEqual(m2.tipo, 'abono')
        self.assertEqual(m2.monto, Decimal("400.00"))
        self.assertEqual(m2.saldo_anterior, Decimal("1100.00"))
        self.assertEqual(m2.saldo_nuevo, Decimal("700.00"))

        m3 = movimientos[2]
        self.assertEqual(m3.tipo, 'abono')
        self.assertEqual(m3.monto, Decimal("300.00"))
        self.assertEqual(m3.saldo_anterior, Decimal("700.00"))
        self.assertEqual(m3.saldo_nuevo, Decimal("400.00"))

    def test_pago_exacto_sobre_venta_parcial_liquida_correctamente(self):
        venta = self._crear_venta_credito()
        
        # Abono 1: $400.00 (deja saldo de $700.00 y venta en PARCIAL)
        PagoService.registrar_pago_credito(
            venta_id=venta.id,
            cliente_id=self.cliente.id,
            metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("400.00")}],
            usuario=self.usuario,
        )
        
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.PARCIAL)

        # Abono 2: $700.00 exactos
        PagoService.registrar_pago_credito(
            venta_id=venta.id,
            cliente_id=self.cliente.id,
            metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("700.00")}],
            usuario=self.usuario,
        )
        
        venta.refresh_from_db()
        self.cliente.refresh_from_db()

        self.assertEqual(venta.estado, Venta.Estado.LIQUIDADA)
        self.assertEqual(self.cliente.saldo_actual, Decimal("0.00"))

        movimientos = list(self.cliente.movimientos_credito.order_by('fecha', 'id'))
        self.assertEqual(len(movimientos), 3) # 1 cargo, 2 abonos
        
        m_final = movimientos[-1]
        self.assertEqual(m_final.saldo_nuevo, self.cliente.saldo_actual)

    def test_no_se_puede_pagar_venta_ya_liquidada(self):
        venta = self._crear_venta_credito()
        
        # Abono Total Inicial: $1100.00
        PagoService.registrar_pago_credito(
            venta_id=venta.id,
            cliente_id=self.cliente.id,
            metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("1100.00")}],
            usuario=self.usuario,
        )
        
        venta.refresh_from_db()
        self.cliente.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.LIQUIDADA)
        
        movimientos_antes = self.cliente.movimientos_credito.count()
        saldo_antes = self.cliente.saldo_actual

        # Intento de segundo abono sobre la misma venta
        with self.assertRaises(SaleNotPayableError):
            PagoService.registrar_pago_credito(
                venta_id=venta.id,
                cliente_id=self.cliente.id,
                metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("100.00")}],
                usuario=self.usuario,
            )

        venta.refresh_from_db()
        self.cliente.refresh_from_db()
        
        self.assertEqual(venta.estado, Venta.Estado.LIQUIDADA)
        self.assertEqual(self.cliente.saldo_actual, saldo_antes)
        self.assertEqual(self.cliente.movimientos_credito.count(), movimientos_antes)

    def test_rollback_total_si_pago_falla(self):
        venta = self._crear_venta_credito()
        
        pagos_antes = Pago.objects.count()
        movimientos_antes = self.cliente.movimientos_credito.count()
        saldo_antes = self.cliente.saldo_actual

        # Intento de abono excesivo que fallará y causará rollback
        monto_excesivo = Decimal("5000.00")
        
        with self.assertRaises(PaymentExceedsBalanceError):
            PagoService.registrar_pago_credito(
                venta_id=venta.id,
                cliente_id=self.cliente.id,
                metodos_pago=[{'metodo': 'EFECTIVO', 'monto': monto_excesivo}],
                usuario=self.usuario,
            )

        venta.refresh_from_db()
        self.cliente.refresh_from_db()

        # Verificar que la transacción fue totalmente revertida
        self.assertEqual(Pago.objects.count(), pagos_antes, "No se debió crear ningún Pago huérfano.")
        self.assertEqual(venta.estado, Venta.Estado.PARCIAL if venta.total - PagoService._calcular_saldo_pendiente_venta(venta) > 0 else Venta.Estado.COMPLETADA)
        self.assertEqual(self.cliente.saldo_actual, saldo_antes, "El saldo no debió alterarse tras un fallo.")
        self.assertEqual(self.cliente.movimientos_credito.count(), movimientos_antes, "No se debió registrar un Movimiento de Crédito.")

    def test_vendedor_sufre_permission_denied_al_exceder_credito(self):
        # Crear Vendedor
        rol_vendedor = Rol.objects.create(nombre="VENDEDOR")
        vendedor = Usuario.objects.create(
            username="vendedor_pago",
            password="pwd",
            rol=rol_vendedor
        )
        
        # Cliente existe con límite de 5000 y saldo_actual asciende a 1100 tras la venta
        self._crear_venta_credito()
        
        # El intento de pago a crédito del Vendedor excede intencionalmente el saldo deudor
        # 2000 > 1100 (el saldo actual). Vendedor DEBE lanzar 403 PermissionDeniedError
        with self.assertRaisesMessage(PermissionDeniedError, "No tienes permisos"):
             PagoService.registrar_pago_credito(
                 cliente_id=self.cliente.id,
                 metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("2000.00")}],
                 usuario=vendedor
             ) # Quitamos venta_id para que sea un abono general al cliente y cause sobrefinanciamiento
             
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, Decimal("1100.00"), "El Vendedor no debió poder forzar un sobregiro a favor")

    def test_admin_excede_credito_y_no_causa_excepcion(self):
        # Admin intenta abonar de más (superar el crédito a favor)
        # La venta setea la deuda a 1100
        self._crear_venta_credito()

        # Admin paga 2000 contra una deuda de 1100. 
        # Su permiso AUTHORIZE_CREDIT_EXCEED lo deja saltarse el error financiero proactivamente.
        try:
             PagoService.registrar_pago_credito(
                 cliente_id=self.cliente.id,
                 metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("2000.00")}],
                 usuario=self.usuario
             )
        except PaymentExceedsBalanceError:
             self.fail("Se lanzó PaymentExceedsBalanceError cuando el admin debió haberlo evitado.")
        except PermissionDeniedError:
             self.fail("Se lanzó PermissionDeniedError al admin invalido.")

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, Decimal("-900.00"), "El Admin debió poder forzar el cobro con sobregiro")
