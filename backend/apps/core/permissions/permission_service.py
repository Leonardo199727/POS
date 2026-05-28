from apps.core.exceptions import PermissionDeniedError
from apps.core.permissions.role_matrix import ROLE_PERMISSIONS


class PermissionService:
    """
    Servicio puro de dominio para autorización.
    Sin queries ORM, sin efectos colaterales.
    Solo levanta `PermissionDeniedError` si falla la validación.
    """

    @staticmethod
    def check(user, permission_code: str) -> None:
        """
        Valida que el usuario tenga el rol y el permiso requerido.
        
        Args:
            user: Instancia del User model.
            permission_code: Constante de PermissionCodes.
            
        Raises:
            PermissionDeniedError: Si no hay rol, si el permiso no existe 
            o si no lo posee en la matriz `ROLE_PERMISSIONS`. 
        """
        if user.rol is None:
            raise PermissionDeniedError("Tu usuario no tiene un rol asignado para realizar esta acción.")
            
        role_name = user.rol.nombre
        
        # Validar si el rol existe en la matriz
        if role_name not in ROLE_PERMISSIONS:
            raise PermissionDeniedError(f"El rol '{role_name}' no posee permisos en el sistema.")
            
        # Validar si el permiso concedido es afirmativo
        if permission_code not in ROLE_PERMISSIONS[role_name]:
            raise PermissionDeniedError("No tienes permisos para realizar esta acción.")

        # Si pasa todas las validaciones retorna silenciosamente None
