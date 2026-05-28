import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.security.models import Rol
from apps.accounts.models import User

rol, _ = Rol.objects.get_or_create(nombre='VENDEDOR', defaults={'descripcion': 'Perfil Vendedor', 'activo': True})

try:
    user = User.objects.get(username='test_vendedor')
    user.set_password('1234')
    user.rol = rol
    user.is_active = True
    user.save()
    print('User test_vendedor updated.')
except User.DoesNotExist:
    user = User.objects.create_user(username='test_vendedor', password='1234', email='vendedor@pos.com', rol=rol)
    print('User test_vendedor created.')
