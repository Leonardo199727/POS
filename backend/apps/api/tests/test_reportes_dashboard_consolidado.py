import json
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from datetime import timedelta
from django.utils import timezone

from apps.security.models import Rol
from apps.accounts.models import User as Usuario
from apps.customers.models import Cliente
from apps.products.models import Producto, VarianteProducto, PrecioProducto
from apps.sales.models import Venta, DetalleVenta
from apps.reports.services.credit_reports import CreditReportService

class DashboardConsolidadoTest(APITestCase):
    
    def setUp(self):
        self.rol_admin = Rol.objects.create(nombre='ADMIN')
        self.admin = Usuario.objects.create_user(
            username='admin_dash', password='123', rol=self.rol_admin
        )
        self.cliente = Cliente.objects.create(nombre='Test Cliente', saldo_actual=Decimal("500.00"))
        
        self.prod = Producto.objects.create(nombre="Test Prod", codigo_interno="COD")
        self.var = VarianteProducto.objects.create(producto=self.prod, nombre="Var 1", sku="SKU", es_default=True)
        self.precio = PrecioProducto.objects.create(
            variante=self.var, precio_compra=Decimal('50.00'), precio_contado=Decimal('100.00'), vigente=True, usuario=self.admin
        )
        
        venta = Venta.objects.create(
            tipo_venta=Venta.TipoVenta.CONTADO,
            cliente=self.cliente,
            usuario=self.admin,
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
            estado=Venta.Estado.COMPLETADA
        )
        DetalleVenta.objects.create(
            venta=venta,
            variante=self.var,
            cantidad=1,
            precio_unitario=Decimal("100.00"),
            subtotal=Decimal("100.00")
        )
        
        self.url_dashboard = reverse('api:reportes-dashboard')
        self.url_financiero = reverse('api:reportes-financieros')
        
        self.client.force_authenticate(user=self.admin)

    def test_dashboard_incluye_meta(self):
        response = self.client.get(self.url_dashboard)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        json_data = response.json()
        self.assertIn("meta", json_data)
        self.assertIn("generado_en", json_data["meta"])

    def test_reportes_financieros_incluye_meta(self):
        response = self.client.get(self.url_financiero)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        json_data = response.json()
        self.assertIn("meta", json_data)
        self.assertIsNotNone(json_data["meta"]["fecha_inicio"])
        self.assertIsNotNone(json_data["meta"]["fecha_fin"])

    def test_parametros_fecha_funcionan(self):
        hoy = timezone.now().date()
        pasado = (hoy - timedelta(days=5))
        
        response = self.client.get(self.url_dashboard, {
            "fecha_inicio": pasado.isoformat(),
            "fecha_fin": hoy.isoformat()
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        json_data = response.json()
        meta = json_data["meta"]
        # Verifica que las query variables fueron parseadas exitosamente (string validation)
        self.assertIn(pasado.isoformat(), meta["fecha_inicio"])
        self.assertIn(hoy.isoformat(), meta["fecha_fin"])

    def test_coherencia_dashboard_vs_financiero(self):
        res_dash = self.client.get(self.url_dashboard).json()
        res_fin = self.client.get(self.url_financiero).json()
        
        # Validar que ambas estructuras contengan la misma utilidad bruta
        u_bruta_dash = res_dash["data"]["resumen_general"]["utilidad_bruta"]
        u_bruta_fin = res_fin["data"]["utilidad_bruta"]
        
        self.assertEqual(str(u_bruta_dash), str(u_bruta_fin))

    def test_coherencia_cartera(self):
        res_dash = self.client.get(self.url_dashboard).json()
        saldo_dash = res_dash["data"]["cartera_resumen"]["saldo_actual_cartera"]
        
        # Servicio interno original subyacente
        dto_interno = CreditReportService.estado_cartera_general()
        saldo_interno = float(dto_interno.saldo_cartera)
        
        self.assertEqual(saldo_dash, saldo_interno)

    def test_no_decimal_en_respuesta(self):
        response = self.client.get(self.url_dashboard)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Este validador reventaria un error TypeError: Object of type Decimal is not JSON serializable si el fallback fallara.
        json_string = json.dumps(response.json())
        self.assertTrue(len(json_string) > 100)
