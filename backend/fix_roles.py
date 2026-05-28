import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.security.models import Rol
from apps.accounts.models import User

def fix_all_user_roles():
    admin_rol = Rol.objects.get(nombre='ADMIN')
    vendedor_rol = Rol.objects.get(nombre='VENDEDOR')
    
    for user in User.objects.all():
        if user.is_superuser or 'admin' in user.username.lower():
            user.rol_id = admin_rol.id
        else:
            user.rol_id = vendedor_rol.id
        user.save()
        print(f"Asignado {user.rol.nombre} a {user.username}")

if __name__ == '__main__':
    fix_all_user_roles()
