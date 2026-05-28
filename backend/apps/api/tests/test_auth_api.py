import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.accounts.models import User as Usuario
from apps.security.models import Rol

class AuthAPITest(APITestCase):
    def setUp(self):
        self.rol_admin = Rol.objects.create(nombre='ADMIN')
        self.rol_vendedor = Rol.objects.create(nombre='VENDEDOR')

        self.admin = Usuario.objects.create_user(
            username='admin_test', 
            password='password123', 
            rol=self.rol_admin
        )
        
        self.vendedor = Usuario.objects.create_user(
            username='vendedor_test', 
            password='password123', 
            rol=self.rol_vendedor
        )
        
        self.inactivo = Usuario.objects.create_user(
            username='blocked_test', 
            password='password123', 
            rol=self.rol_admin,
            is_active=False
        )

        self.login_url = reverse('api:api-login')
        self.logout_url = reverse('api:api-logout')

    def test_login_correcto_admin(self):
        data = {'username': 'admin_test', 'password': 'password123'}
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = response.json()
        
        # Validar estructura del contrato JSON
        self.assertTrue(json_data['success'])
        self.assertIn('token', json_data['data'])
        self.assertIn('user', json_data['data'])
        
        # Validar campos del usuario embebido
        user_data = json_data['data']['user']
        self.assertEqual(user_data['username'], 'admin_test')
        self.assertEqual(user_data['rol'], 'ADMIN')
        
        # Verificar que el token existe real en DB
        token = Token.objects.get(user=self.admin)
        self.assertEqual(json_data['data']['token'], token.key)

    def test_login_correcto_vendedor(self):
        data = {'username': 'vendedor_test', 'password': 'password123'}
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = response.json()
        
        self.assertTrue(json_data['success'])
        self.assertEqual(json_data['data']['user']['rol'], 'VENDEDOR')

    def test_login_invalido_credenciales(self):
        data = {'username': 'admin_test', 'password': 'wrongpassword'}
        response = self.client.post(self.login_url, data, format='json')
        
        # Debe fallar con nuestro propio Global Handler dictaminando 'INVALID_CREDENTIALS'
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        json_data = response.json()
        self.assertFalse(json_data['success'])
        self.assertEqual(json_data['error']['code'], 'INVALID_CREDENTIALS')

    def test_login_usuario_inactivo(self):
        data = {'username': 'blocked_test', 'password': 'password123'}
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        json_data = response.json()
        self.assertFalse(json_data['success'])
        self.assertEqual(json_data['error']['code'], 'INVALID_CREDENTIALS')

    def test_logout_correcto_invalida_token(self):
        # Generar sesion 
        token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        
        # Hacer logout
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['success'])
        
        # Confirmar que la sesion y token fueron invalidados real physical
        with self.assertRaises(Token.DoesNotExist):
            Token.objects.get(user=self.admin)

    def test_logout_fallido_sin_sesion(self):
        # Intento de logout sin token enviado
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
