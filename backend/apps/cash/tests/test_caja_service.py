from decimal import Decimal
from django.test import TestCase

from apps.accounts.models import User as Usuario
from apps.security.models import Rol
from apps.core.exceptions import PermissionDeniedError
from apps.cash.models import Caja, MovimientoCaja
from apps.cash.services.caja_service import CajaService


class CajaServiceTests(TestCase):
    """
    Tests estrátegicos para blindar el núcleo transaccional y el flujo interno contable del POS (CajaService).
    """
    def setUp(self):
        self.rol_admin = Rol.objects.create(nombre="ADMIN")
        # 1. Crear usuario base
        self.usuario = Usuario.objects.create(
            username="testcashier",
            password="testpassword",
            is_superuser=True,
            rol=self.rol_admin
        )

    def test_no_se_puede_abrir_dos_cajas_para_mismo_usuario(self):
        # Abrir caja 1
        CajaService.abrir_caja(
            usuario=self.usuario,
            monto_inicial=Decimal("500.00")
        )

        cajas_abiertas = Caja.objects.filter(usuario_apertura=self.usuario, estado=Caja.Estado.ABIERTA).count()
        self.assertEqual(cajas_abiertas, 1)

        # Intentar abrir la caja 2
        with self.assertRaises(ValueError):
            CajaService.abrir_caja(
                usuario=self.usuario,
                monto_inicial=Decimal("200.00")
            )

        # Verificar que solo exista 1 caja abierta en BD y no registros bugeados
        self.assertEqual(
            Caja.objects.filter(usuario_apertura=self.usuario, estado=Caja.Estado.ABIERTA).count(),
            1
        )

    def test_apertura_registra_monto_inicial_correctamente(self):
        caja = CajaService.abrir_caja(
            usuario=self.usuario,
            monto_inicial=Decimal("1000.00")
        )

        # Validaciones de la entidad
        caja.refresh_from_db()
        self.assertEqual(caja.estado, Caja.Estado.ABIERTA)
        self.assertEqual(caja.monto_inicial, Decimal("1000.00"))

        # Validar Movimiento asociado
        movimientos = MovimientoCaja.objects.filter(caja=caja)
        self.assertEqual(movimientos.count(), 1)
        
        movimiento_inicial = movimientos.first()
        self.assertEqual(movimiento_inicial.tipo, MovimientoCaja.TipoMovimiento.ENTRADA)
        self.assertEqual(movimiento_inicial.metodo_pago, MovimientoCaja.MetodoPago.EFECTIVO)
        self.assertEqual(movimiento_inicial.origen, MovimientoCaja.Origen.MANUAL)
        self.assertEqual(movimiento_inicial.monto, Decimal("1000.00"))

    def test_ingreso_manual_incrementa_flujo_correctamente(self):
        caja = CajaService.abrir_caja(
            usuario=self.usuario,
            monto_inicial=Decimal("1000.00")
        )

        CajaService.registrar_ingreso(
            usuario=self.usuario,
            monto=Decimal("200.00"),
            metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
            concepto="Venta menudeo extra",
            origen=MovimientoCaja.Origen.MANUAL
        )

        esperados = CajaService._calcular_totales_esperados(caja)
        
        # 1000 apertura + 200 ingreso 
        self.assertEqual(esperados['efectivo'], Decimal("1200.00"))
        # Otras carteras no debieron ser alteradas
        self.assertEqual(esperados['tarjeta'], Decimal("0.00"))
        self.assertEqual(esperados['transferencia'], Decimal("0.00"))
        
        self.assertEqual(MovimientoCaja.objects.filter(caja=caja).count(), 2)

    def test_retiro_manual_disminuye_flujo_correctamente(self):
        caja = CajaService.abrir_caja(
            usuario=self.usuario,
            monto_inicial=Decimal("1000.00")
        )

        CajaService.registrar_retiro(
            usuario=self.usuario,
            monto=Decimal("300.00"),
            concepto="Viáticos"
        )
        
        esperados = CajaService._calcular_totales_esperados(caja)
        self.assertEqual(esperados['efectivo'], Decimal("700.00"))

        # Validar generación del movimiento SALIDA
        movimientos_salida = MovimientoCaja.objects.filter(
            caja=caja,
            tipo=MovimientoCaja.TipoMovimiento.SALIDA
        )
        self.assertEqual(movimientos_salida.count(), 1)
        self.assertEqual(movimientos_salida.first().monto, Decimal("300.00"))

    def test_no_se_puede_operar_caja_cerrada(self):
        caja = CajaService.abrir_caja(
            usuario=self.usuario,
            monto_inicial=Decimal("1000.00")
        )

        # Cierre
        CajaService.cerrar_caja(
            usuario=self.usuario,
            total_efectivo_contado=Decimal("1000.00")
        )
        
        self.assertEqual(MovimientoCaja.objects.filter(caja=caja).count(), 1)

        # Intento de operación post-cierre (El servicio obtiene la abierta automáticamente y va a fallar)
        with self.assertRaises(ValueError):
            CajaService.registrar_ingreso(
                usuario=self.usuario,
                monto=Decimal("500.00"),
                metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
                concepto="Ingreso tardío",
            )
            
        # Comprobar que no se creó movimiento anómalo post close
        self.assertEqual(MovimientoCaja.objects.filter(caja=caja).count(), 1)

    def test_cierre_calcula_diferencias_correctamente(self):
        caja = CajaService.abrir_caja(
            usuario=self.usuario,
            monto_inicial=Decimal("1000.00")
        )

        # Ingreso
        CajaService.registrar_ingreso(
            usuario=self.usuario,
            monto=Decimal("500.00"),
            metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
            concepto="Venta base"
        )

        # Retiro
        CajaService.registrar_retiro(
            usuario=self.usuario,
            monto=Decimal("200.00"),
            concepto="Pago proveedor"
        )

        # Efectivo esperado al cierre: 1000 + 500 - 200 = 1300
        # Supongamos que declaran que hay un sobrante físico de $30.00. (es decir, el efectivo contó 1330).
        caja_cerrada = CajaService.cerrar_caja(
            usuario=self.usuario,
            total_efectivo_contado=Decimal("1330.00"),
            observaciones="Sobrante en billetes chicos"
        )

        caja_cerrada.refresh_from_db()
        self.assertEqual(caja_cerrada.estado, Caja.Estado.CERRADA)
        self.assertIsNotNone(caja_cerrada.fecha_cierre)
        
        # Validar cálculo matemático
        self.assertEqual(caja_cerrada.total_efectivo_esperado, Decimal("1300.00"))
        self.assertEqual(caja_cerrada.total_efectivo_contado, Decimal("1330.00"))
        
        # Diferencia es contado - esperado = +30.00
        self.assertEqual(caja_cerrada.diferencia_efectivo, Decimal("30.00"))

    def test_rollback_si_operacion_falla(self):
        caja = CajaService.abrir_caja(
            usuario=self.usuario,
            monto_inicial=Decimal("1000.00")
        )

        # Registrar un ingreso que es rechazado en la capa validación -> atomic rollback.
        
        movimientos_antes = MovimientoCaja.objects.count()
        
        with self.assertRaises(ValueError):
            CajaService.registrar_ingreso(
                usuario=self.usuario,
                monto=Decimal("-200.00"), # Monto negativo, debe rechazar
                metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
                concepto="Hacking the matrix"
            )
            
        # Comprobar estado inmutable
        self.assertEqual(MovimientoCaja.objects.count(), movimientos_antes)
        esperados = CajaService._calcular_totales_esperados(caja)
        self.assertEqual(esperados['efectivo'], Decimal("1000.00"))

    def test_vendedor_sufre_permission_denied_al_intentar_cerrar_caja(self):
        rol_vendedor = Rol.objects.create(nombre="VENDEDOR")
        vendedor = Usuario.objects.create(username="vendedor_caja", rol=rol_vendedor)
        
        caja = CajaService.abrir_caja(
            usuario=vendedor,
            monto_inicial=Decimal("500.00")
        )
        
        # Debe fallar instantaneamente por check en RBAC
        with self.assertRaisesMessage(PermissionDeniedError, "No tienes permisos"):
             CajaService.cerrar_caja(
                 usuario=vendedor,
                 total_efectivo_contado=Decimal("500.00")
             )
             
        caja.refresh_from_db()
        self.assertEqual(caja.estado, Caja.Estado.ABIERTA)
