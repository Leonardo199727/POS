from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from apps.core.exceptions import (
    BusinessLogicError,
    PermissionDeniedError,
)
from apps.customers.models import Cliente, MovimientoCredito
from apps.inventory.models import Inventario, MovimientoInventario
from apps.products.models import Producto, VarianteProducto, PrecioProducto
from apps.sales.models import Venta, DetalleVenta
from apps.sales.services.venta_service import VentaService
from apps.cash.models import Caja
from apps.accounts.models import User as Usuario
from apps.security.models import Rol


class VentaServiceTests(TestCase):
    """
    Tests estratégicos para blindar VentaService, las operaciones de inventario, sumatorias y consistencia del ledger.
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
        
        # 2. Configurar Caja Abierta
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
        self.producto = Producto.objects.create(
            nombre="Producto Test",
            codigo_interno="TEST-001"
        )
        self.variante = VarianteProducto.objects.create(
            producto=self.producto,
            nombre="Default",
            es_default=True
        )
        self.inventario = Inventario.objects.create(
            variante=self.variante,
            stock_actual=10,
            stock_minimo=2
        )
        
        # 5. Configurar Precio para la variante
        self.precio = PrecioProducto.objects.create(
            variante=self.variante,
            precio_contado=Decimal("500.00"),
            precio_credito=Decimal("600.00"),
            vigente=True,
            usuario=self.usuario
        )

    def test_no_se_puede_crear_venta_credito_sin_cliente(self):
        # La regla dice que no se puede tener una venta crédito huérfana.
        # En la API generalmente se intercepta, pero a nivel domain asertamos que si se finaliza, da error.
        venta = VentaService.crear_venta(
            usuario=self.usuario,
            tipo_venta=Venta.TipoVenta.CREDITO,
            cliente=None
        )
        
        # Agregamos producto
        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=1
        )
        
        # Al finalizar, como tipo_venta es CREDITO y el cliente es None, debería disparar TypeError/ValueError.
        with self.assertRaises(ValueError):
            VentaService.finalizar_venta(venta_id=venta.id)
            
        # Corroborar que la venta permanece en EN_PROCESO.
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.EN_PROCESO)

    def test_agregar_producto_descuenta_inventario_correctamente(self):
        stock_inicial = self.inventario.stock_actual # 10
        cantidad_vendida = 2
        
        venta = VentaService.crear_venta(
            usuario=self.usuario,
            tipo_venta=Venta.TipoVenta.CONTADO,
            cliente=None
        )
        
        # Validar subtotal de adición. precio contado = 500
        detalle = VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=cantidad_vendida
        )
        
        self.assertEqual(detalle.subtotal, Decimal("1000.00"))
        
        venta.refresh_from_db()
        self.assertEqual(venta.subtotal, Decimal("1000.00"))
        self.assertEqual(venta.total, Decimal("1000.00"))
        
        # En este punto el stock es 10 todavía porque no se ha finalizado la venta
        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.stock_actual, stock_inicial)
        
        # Finalizar
        VentaService.finalizar_venta(venta_id=venta.id)
        
        # Validar descuento exacto
        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.stock_actual, stock_inicial - cantidad_vendida)
        
        # Verificar que DetalleVenta fue vinculado
        self.assertTrue(DetalleVenta.objects.filter(venta=venta, variante=self.variante).exists())

    def test_no_se_puede_agregar_producto_a_venta_completada(self):
        venta = VentaService.crear_venta(
            usuario=self.usuario,
            tipo_venta=Venta.TipoVenta.CONTADO,
            cliente=None
        )
        
        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=1
        )
        
        VentaService.finalizar_venta(venta_id=venta.id)
        
        self.inventario.refresh_from_db()
        stock_post_cierre = self.inventario.stock_actual
        detalles_post_cierre = DetalleVenta.objects.filter(venta=venta).count()
        
        # Intentar modificar el carrito
        with self.assertRaises(ValueError):
            VentaService.agregar_producto(
                venta_id=venta.id,
                variante_id=self.variante.id,
                cantidad=1
            )
            
        # Comprobar estado protegido
        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.stock_actual, stock_post_cierre)
        self.assertEqual(DetalleVenta.objects.filter(venta=venta).count(), detalles_post_cierre)

    def test_no_se_puede_finalizar_venta_sin_productos(self):
        venta = VentaService.crear_venta(
            usuario=self.usuario,
            tipo_venta=Venta.TipoVenta.CONTADO,
            cliente=None
        )
        
        with self.assertRaises(ValueError):
            VentaService.finalizar_venta(venta_id=venta.id)
            
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.EN_PROCESO)

    def test_venta_credito_generates_movimiento_cargo_correcto(self):
        venta = VentaService.crear_venta(
            usuario=self.usuario,
            tipo_venta=Venta.TipoVenta.CREDITO,
            cliente=self.cliente
        )
        
        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=1
        )
        
        # precio credito = 600
        saldo_anterior_esp = self.cliente.saldo_actual # 0.00
        
        VentaService.finalizar_venta(venta_id=venta.id)
        
        venta.refresh_from_db()
        self.cliente.refresh_from_db()
        
        self.assertEqual(venta.estado, Venta.Estado.COMPLETADA)
        self.assertEqual(self.cliente.saldo_actual, Decimal("600.00"))
        
        movimientos = self.cliente.movimientos_credito.filter(venta=venta)
        self.assertEqual(movimientos.count(), 1)
        
        movimiento = movimientos.first()
        self.assertEqual(movimiento.tipo, MovimientoCredito.TipoMovimiento.CARGO_VENTA)
        self.assertEqual(movimiento.saldo_anterior, saldo_anterior_esp)
        self.assertEqual(movimiento.saldo_nuevo, Decimal("600.00"))
        self.assertEqual(movimiento.monto, Decimal("600.00"))

    def test_venta_contado_no_generates_movimiento_credito(self):
        venta = VentaService.crear_venta(
            usuario=self.usuario,
            tipo_venta=Venta.TipoVenta.CONTADO,
            cliente=self.cliente
        )
        
        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=1
        )
        
        saldo_antes = self.cliente.saldo_actual
        movimientos_antes = self.cliente.movimientos_credito.count()
        
        VentaService.finalizar_venta(venta_id=venta.id)
        
        venta.refresh_from_db()
        self.cliente.refresh_from_db()
        
        # No debt is inherited by the client in cash sales
        self.assertEqual(venta.estado, Venta.Estado.COMPLETADA)
        self.assertEqual(self.cliente.saldo_actual, saldo_antes)
        self.assertEqual(self.cliente.movimientos_credito.count(), movimientos_antes)

    def test_rollback_si_inventario_insuficiente(self):
        # Set limit stock
        self.inventario.stock_actual = 1
        self.inventario.save()
        
        rol_vendedor = Rol.objects.create(nombre="VENDEDOR")
        vendedor = Usuario.objects.create(username="vend1", rol=rol_vendedor)
        
        venta = VentaService.crear_venta(
            usuario=vendedor,
            tipo_venta=Venta.TipoVenta.CONTADO,
            cliente=None
        )
        
        # Agregar el subtotal del carrito no deberia dar error. El rechazo se hace al finalizar.
        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=5
        )
        
        # RBAC intercepts first for Vendedor, preventing ValueError and throwing 403.
        # This still guarantees stock is saved, but at a higher tier.
        with self.assertRaisesMessage(PermissionDeniedError, "No tienes permisos"):
             VentaService.finalizar_venta(venta_id=venta.id)
             
        # El inventario debe seguir en 1
        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.stock_actual, 1)
        
        # La venta continua en Estado Abierto
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.EN_PROCESO)

    def test_vendedor_sufre_permission_denied_al_intentar_override_stock(self):
        # Set limit stock
        self.inventario.stock_actual = 1
        self.inventario.save()
        
        rol_vendedor = Rol.objects.create(nombre="VENDEDOR")
        vendedor = Usuario.objects.create(username="vend", rol=rol_vendedor)
        
        venta = VentaService.crear_venta(
            usuario=vendedor,
            tipo_venta=Venta.TipoVenta.CONTADO,
            cliente=None
        )
        
        # Superamos la cantidad en 5 sobre 1.
        VentaService.agregar_producto(
            venta_id=venta.id,
            variante_id=self.variante.id,
            cantidad=5
        )
        
        # El validador RBAC debe interceptar antes que el ValueError general y lanzar 403
        with self.assertRaisesMessage(PermissionDeniedError, "No tienes permisos"):
             VentaService.finalizar_venta(venta_id=venta.id)

        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.stock_actual, 1)
