from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.db import connection

from apps.security.models import Rol
from apps.accounts.models import User as Usuario
from apps.products.models import Producto, VarianteProducto, PrecioProducto
from apps.inventory.models import Inventario

class ProductoAPITest(APITestCase):
    
    def setUp(self):
        self.rol_admin = Rol.objects.create(nombre='ADMIN')
        self.rol_vendedor = Rol.objects.create(nombre='VENDEDOR')

        self.admin = Usuario.objects.create_user(
            username='admin_test_prod', password='123', rol=self.rol_admin
        )
        self.vendedor = Usuario.objects.create_user(
            username='vendedor_test_prod', password='123', rol=self.rol_vendedor
        )
        
        for i in range(5):
            prod = Producto.objects.create(
                nombre=f"Producto {i}", 
                codigo_interno=f"COD-{i}",
                activo=True
            )
            var = VarianteProducto.objects.create(
                producto=prod,
                nombre=f"Variante {i}",
                sku=f"SKU-{i}",
                es_default=True
            )
            PrecioProducto.objects.create(
                variante=var,
                precio_compra=Decimal('50.00'),
                precio_contado=Decimal('100.00'),
                precio_credito=Decimal('110.00'),
                usuario=self.admin,
                vigente=True
            )
            Inventario.objects.create(
                variante=var,
                stock_actual=10 + i,
                stock_minimo=2
            )

        self.url = reverse('api:producto-list')

    def test_vendedor_no_ve_precio_compra(self):
        self.client.force_authenticate(user=self.vendedor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        producto_data = data['data'][0]
        
        self.assertNotIn('precio_compra', producto_data)
        self.assertNotIn('margen', producto_data)

    def test_admin_ve_precio_compra(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        producto_data = data['data'][0]
        
        self.assertIn('precio_compra', producto_data)
        self.assertIn('margen', producto_data)
        self.assertEqual(float(producto_data['precio_compra']), 50.00)
        self.assertEqual(float(producto_data['margen']), 100.00)

    def test_vendedor_ve_precio_contado_y_credito(self):
        self.client.force_authenticate(user=self.vendedor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        producto_data = data['data'][0]
        
        self.assertIn('precio_contado', producto_data)
        self.assertIn('precio_credito', producto_data)
        self.assertIn('stock_disponible', producto_data)
        self.assertEqual(float(producto_data['precio_contado']), 100.00)
        self.assertEqual(float(producto_data['precio_credito']), 110.00)
        self.assertTrue(producto_data['stock_disponible'] >= 10)

    def test_no_n_plus_one_queries(self):
        self.client.force_authenticate(user=self.vendedor)
        
        # Una petición en caliente ('warming up') para ignorar queries de sesión si las hubiera.
        self.client.get(self.url)
        
        # Testeamos usando Django assertNumQueries 
        # Count, Producto, Variante(con inventario), Precio, y Codigos_Barras son 5 queries exactas de DB pre-fetching. No N+1.
        with self.assertNumQueries(5):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
