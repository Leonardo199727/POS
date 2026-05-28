from apps.core.permissions.permission_codes import PermissionCodes

"""
Matriz central de Roles → Permisos.
Resuelve la autorización estática evaluando `user.rol.nombre`.
"""

ROLE_PERMISSIONS = {
    "ADMIN": {
        PermissionCodes.VIEW_COST_PRICE,
        PermissionCodes.EDIT_PRICE,
        PermissionCodes.AUTHORIZE_CREDIT_EXCEED,
        PermissionCodes.AUTHORIZE_STOCK_OVERRIDE,
        PermissionCodes.VIEW_FINANCIAL_REPORTS,
        PermissionCodes.CLOSE_CASH_REGISTER,
    },
    "VENDEDOR": {
        PermissionCodes.EDIT_PRICE, # Único permiso delegado al vendedor según especificación
    }
}
