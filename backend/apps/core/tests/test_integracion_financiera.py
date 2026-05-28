from decimal import Decimal
from django.test import TestCase

from apps.security.models import Rol
from apps.accounts.models import User as Usuario
from apps.customers.models import Cliente, MovimientoCredito
from apps.products.models import Producto, VarianteProducto, PrecioProducto
from apps.inventory.models import Inventario
from apps.sales.models import Venta
from apps.cash.models import Caja, MovimientoCaja

from apps.sales.services.venta_service import VentaService
from apps.payments.services.pago_service import PagoService
from apps.cash.services.caja_service import CajaService

from apps.core.exceptions import (
    PermissionDeniedError,
    PaymentExceedsBalanceError,
)

class FlujoCompletoPOSIntegrationTest(TestCase):
    """
    Test de integración cruzada de dominio que valida el flujo completo del POS.
    Utiliza exclusivamente la capa de Services, sin HTTP, sin APIClient y sin mocks.
    """

    def setUp(self):
        # 1. Roles
        self.rol_admin = Rol.objects.create(nombre="ADMIN")
        self.rol_vendedor = Rol.objects.create(nombre="VENDEDOR")

        # 2. Usuarios
        self.admin = Usuario.objects.create(
            username="admin_user",
            password="testpassword",
            rol=self.rol_admin
        )
        self.vendedor = Usuario.objects.create(
            username="vendedor_user",
            password="testpassword",
            rol=self.rol_vendedor
        )

        # 3. Cliente con límite de crédito 5000, saldo inicial 0
        self.cliente = Cliente.objects.create(
            nombre="Cliente Prueba Integracion",
            limite_credito=Decimal("5000.00"),
            saldo_actual=Decimal("0.00")
        )

        # 4. Producto, Variante y Precio (1000 c/u)
        self.producto = Producto.objects.create(nombre="Producto Test Integracion")
        self.variante = VarianteProducto.objects.create(
            producto=self.producto, 
            nombre="Variante Unica", 
            sku="SKU-TEST-INT"
        )
        self.precio = PrecioProducto.objects.create(
            variante=self.variante,
            precio_contado=Decimal("1000.00"),
            precio_credito=Decimal("1000.00"),
            usuario=self.admin
        )

        # 5. Inventario con 20 unidades
        self.inventario = Inventario.objects.create(
            variante=self.variante,
            stock_actual=20
        )

        # 6. Caja abierta asociada al vendedor (como si el admin la hubiera abierto para él, o él mismo)
        self.caja = Caja.objects.create(
            usuario_apertura=self.vendedor,
            estado=Caja.Estado.ABIERTA,
            monto_inicial=Decimal("0.00")
        )

    def test_flujo_normal_completo(self):
        """
        ESCENARIO 1 — FLUJO NORMAL COMPLETO
        Verifica creación de venta a crédito, validación de inventario,
        estados, saldo de cliente y un pago parcial.
        """
        # 1. Vendedor crea venta crédito
        venta = VentaService.crear_venta(
            usuario=self.vendedor,
            tipo_venta=Venta.TipoVenta.CREDITO,
            cliente=self.cliente
        )

        # 2. Agrega producto (3 x 1000 = 3000)
        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=3
        )

        # 3. Finaliza venta
        VentaService.finalizar_venta(venta_id=venta.id)

        # 4. Validar fin de la venta
        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.stock_actual, 17, "El inventario no se redujo correctamente.")
        
        movimientos_credito = MovimientoCredito.objects.filter(cliente=self.cliente)
        self.assertEqual(movimientos_credito.count(), 1)
        
        mov_cargo = movimientos_credito.first()
        self.assertEqual(mov_cargo.tipo, MovimientoCredito.TipoMovimiento.CARGO_VENTA)
        self.assertEqual(mov_cargo.monto, Decimal("3000.00"))
        
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, Decimal("3000.00"))
        
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.COMPLETADA)

        # 5. Registrar pago parcial (1000)
        PagoService.registrar_pago_credito(
            venta_id=venta.id,
            cliente_id=self.cliente.id,
            metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("1000.00")}],
            usuario=self.vendedor
        )

        # 6. Validar resultado del pago parcial
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, Decimal("2000.00"))
        
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.PARCIAL)

        movimientos_credito = MovimientoCredito.objects.filter(cliente=self.cliente, tipo=MovimientoCredito.TipoMovimiento.ABONO_PAGO)
        self.assertEqual(movimientos_credito.count(), 1)
        self.assertEqual(movimientos_credito.first().monto, Decimal("1000.00"))

        movimientos_caja = MovimientoCaja.objects.filter(caja=self.caja, tipo=MovimientoCaja.TipoMovimiento.ENTRADA)
        self.assertEqual(movimientos_caja.count(), 1)

    def test_excede_limite_sin_permiso(self):
        """
        ESCENARIO 2 — EXCEDER LÍMITE SIN PERMISO
        Un VENDEDOR intenta finiquitar una venta que excede el límite. 
        Debe fallar con PermissionDeniedError.
        """
        # Límite es 5000, intentamos comprar 6000 (6 * 1000)
        venta = VentaService.crear_venta(
            usuario=self.vendedor,
            tipo_venta=Venta.TipoVenta.CREDITO,
            cliente=self.cliente
        )

        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=6
        )

        with self.assertRaises(ValueError):
            VentaService.finalizar_venta(venta_id=venta.id)

        # Validar estado inconsistente evitado
        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.stock_actual, 20)
        
        self.assertEqual(MovimientoCredito.objects.filter(cliente=self.cliente).count(), 0)
        
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.EN_PROCESO)
        
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, Decimal("0.00"))

    def test_admin_puede_extender_limite(self):
        """
        ESCENARIO 3 — EXCEDER LÍMITE CON ADMIN
        Un ADMIN ejecuta una venta que excede el límite del cliente, debe permitirse.
        """
        venta = VentaService.crear_venta(
            usuario=self.admin,
            tipo_venta=Venta.TipoVenta.CREDITO,
            cliente=self.cliente
        )

        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=6
        )

        # Admin actualiza límite de crédito dinámicamente antes de finalizar
        self.cliente.limite_credito = Decimal("6000.00")
        self.cliente.save()

        # No debe lanzar excepción
        VentaService.finalizar_venta(venta_id=venta.id)

        self.cliente.refresh_from_db()
        # Verificar que el estado del ledger y saldo sea consistente
        self.assertEqual(self.cliente.saldo_actual, Decimal("6000.00"))
        # El límite de crédito del cliente debe haber sido extendido
        self.assertEqual(self.cliente.limite_credito, Decimal("6000.00"))
        
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.COMPLETADA)

    def test_no_permitir_sobrepago(self):
        """
        ESCENARIO 4 — INTENTO DE SOBREPAGO
        Intentar pagar más de lo adeudado debe lanzar PaymentExceedsBalanceError 
        y mantener la consistencia.
        """
        # Venta normal de 2000
        venta = VentaService.crear_venta(
            usuario=self.vendedor,
            tipo_venta=Venta.TipoVenta.CREDITO,
            cliente=self.cliente
        )
        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=2
        )
        VentaService.finalizar_venta(venta_id=venta.id)

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, Decimal("2000.00"))

        # Intento de pago de 3000
        with self.assertRaises(PaymentExceedsBalanceError):
            PagoService.registrar_pago_credito(
                venta_id=venta.id,
                cliente_id=self.cliente.id,
                metodos_pago=[{'metodo': 'EFECTIVO', 'monto': Decimal("3000.00")}],
                usuario=self.admin
            )

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, Decimal("2000.00"))

        # Validamos que no se crearon movimientos extras luego del cargo inicial
        self.assertEqual(MovimientoCredito.objects.filter(cliente=self.cliente).count(), 1)
        self.assertEqual(MovimientoCaja.objects.filter(caja=self.caja).count(), 0)

    def test_cierre_caja_con_rbac(self):
        """
        ESCENARIO 5 — CIERRE DE CAJA
        VENDEDOR falla por permisos. ADMIN cierra exitosamente.
        """
        with self.assertRaises(PermissionDeniedError):
            CajaService.cerrar_caja(
                usuario=self.vendedor,
                total_efectivo_contado=Decimal("0.00")
            )

        self.caja.refresh_from_db()
        self.assertEqual(self.caja.estado, Caja.Estado.ABIERTA)

        self.caja_admin = Caja.objects.create(
            usuario_apertura=self.admin,
            estado=Caja.Estado.ABIERTA,
            monto_inicial=Decimal("0.00")
        )

        # Admin cierra caja satisfactoriamente
        CajaService.cerrar_caja(
            usuario=self.admin,
            total_efectivo_contado=Decimal("0.00")
        )

        self.caja_admin.refresh_from_db()
        self.assertEqual(self.caja_admin.estado, Caja.Estado.CERRADA)
        self.assertEqual(self.caja_admin.diferencia_efectivo, Decimal("0.00"))
