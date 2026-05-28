import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.security.models import Rol
from apps.accounts.models import User

def recover_roles():
    print("Recuperando roles eliminados...")
    admin_rol, _ = Rol.objects.get_or_create(nombre='ADMIN', defaults={'descripcion': 'Administrador del sistema'})
    vendedor_rol, _ = Rol.objects.get_or_create(nombre='VENDEDOR', defaults={'descripcion': 'Vendedor del sistema'})
    
    # Check if there are users, assign ADMIN to superusers if missing
    for user in User.objects.all():
        if not user.rol_id:
            if user.is_superuser:
                user.rol = admin_rol
            else:
                user.rol = vendedor_rol
            user.save()
            print(f"Asignado rol a {user.username}")
    print("Recuperación completada.")

if __name__ == '__main__':
    recover_roles()
