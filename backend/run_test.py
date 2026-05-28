import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.payments.tests.test_pago_service import PagoServiceTests

test = PagoServiceTests('test_vendedor_sufre_permission_denied_al_exceder_credito')
test.setUp()
test.test_vendedor_sufre_permission_denied_al_exceder_credito()
print("Success running alone")
