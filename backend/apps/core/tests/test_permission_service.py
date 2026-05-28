from django.test import TestCase

from apps.accounts.models import User
from apps.security.models import Rol
from apps.core.exceptions import PermissionDeniedError
from apps.core.permissions.permission_codes import PermissionCodes
from apps.core.permissions.permission_service import PermissionService


class PermissionServiceTests(TestCase):
    """
    Tests puristas para el motor RBAC del dominio.
    Valida la lectura exacta de matriz estática.
    """

    @classmethod
    def setUpTestData(cls):
        # Configurar roles estáticos
        cls.rol_admin = Rol.objects.create(nombre='ADMIN', descripcion='Administrador General')
        cls.rol_vendedor = Rol.objects.create(nombre='VENDEDOR', descripcion='Vendedor de mostrador')
        
        # Crear usuarios para tests
        cls.user_admin = User.objects.create(
            username='admin_rbac', email='admin@rbac.com', rol=cls.rol_admin
        )
        cls.user_vendedor = User.objects.create(
            username='vendedor_rbac', email='vendedor@rbac.com', rol=cls.rol_vendedor
        )
        cls.user_sin_rol = User.objects.create(
            username='anon_rbac', email='anon@rbac.com'
        )

    def test_admin_puede_ejecutar_permiso_protegido(self):
        """ADMIN debe pasar limpiamente la verificación de permisos sin mutar ni arrojar nada."""
        try:
            # Seleccionamos un permiso aleatorio de los que tiene ADMIN
            PermissionService.check(self.user_admin, PermissionCodes.AUTHORIZE_CREDIT_EXCEED)
            PermissionService.check(self.user_admin, PermissionCodes.AUTHORIZE_STOCK_OVERRIDE)
            PermissionService.check(self.user_admin, PermissionCodes.VIEW_FINANCIAL_REPORTS)
        except PermissionDeniedError:
            self.fail("PermissionService.check arrojó PermissionDeniedError inesperadamente para ADMIN.")

    def test_vendedor_tiene_restringidos_permisos_administrativos(self):
        """VENDEDOR no debe poder pasar un check de permiso administrativo general."""
        with self.assertRaisesMessage(PermissionDeniedError, "No tienes permisos para realizar esta acción"):
            PermissionService.check(self.user_vendedor, PermissionCodes.AUTHORIZE_CREDIT_EXCEED)
            
        with self.assertRaisesMessage(PermissionDeniedError, "No tienes permisos para realizar esta acción"):
            PermissionService.check(self.user_vendedor, PermissionCodes.CLOSE_CASH_REGISTER)

    def test_vendedor_puede_ejecutar_solo_sus_permisos_en_matriz(self):
        """VENDEDOR tiene explícitamente EDIT_PRICE según el spec."""
        try:
            PermissionService.check(self.user_vendedor, PermissionCodes.EDIT_PRICE)
        except PermissionDeniedError:
            self.fail("PermissionService.check arrojó excepción para un permiso que el VENDEDOR sí posee.")

    def test_usuario_sin_rol_lanza_excepcion(self):
        """Usuarios con rol None son bloqueados tajantemente."""
        with self.assertRaisesMessage(PermissionDeniedError, "Tu usuario no tiene un rol asignado"):
            PermissionService.check(self.user_sin_rol, PermissionCodes.VIEW_FINANCIAL_REPORTS)
            
    def test_permiso_inexistente_lanza_excepcion(self):
        """Si un developer manda un str que no está en la matriz, por seguridad debe explotar 403."""
        with self.assertRaisesMessage(PermissionDeniedError, "No tienes permisos para realizar esta acción"):
            PermissionService.check(self.user_admin, "PERMISO_FALSO_INVENTADO")

    def test_check_no_muta_db_si_falla(self):
        """Garantizar la pureza del dominio, un permiso negado no crea registros."""
        counter_antes = User.objects.count()
        with self.assertRaises(PermissionDeniedError):
            PermissionService.check(self.user_vendedor, PermissionCodes.CLOSE_CASH_REGISTER)
        self.assertEqual(User.objects.count(), counter_antes)
