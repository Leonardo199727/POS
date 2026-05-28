from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


class IsAdminRole(BasePermission):
    """
    Permite el acceso exclusivamente a usuarios con rol ADMIN.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        return getattr(request.user.rol, 'nombre', '') == 'ADMIN'


class IsVendedorRole(BasePermission):
    """
    Permite el acceso exclusivamente a usuarios con rol VENDEDOR.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        return getattr(request.user.rol, 'nombre', '') == 'VENDEDOR'


class IsAdminOrVendedor(BasePermission):
    """
    Permite el acceso a usuarios con rol ADMIN o VENDEDOR.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        rol_nombre = getattr(request.user.rol, 'nombre', '')
        return rol_nombre in ['ADMIN', 'VENDEDOR']
