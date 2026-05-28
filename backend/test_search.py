import os
import sys
import django

sys.path.insert(0, '/Users/leonardomataolvera/Desktop/LMSolutions/POS/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.api.views.producto_views import ProductoListCreateAPIView
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()
request = factory.get('/api/productos/?search=cargo')

view = ProductoListCreateAPIView.as_view()
response = view(request)
print("Status:", response.status_code)
if response.status_code != 200:
    print("Error:", response.data)
else:
    print("Total Results Found by Pagination Engine:", response.data.get('count', 0))
    print("Items Printed:", len(response.data.get('results', [])))
    for r in response.data.get('results', []):
        print(" ->", r['nombre'], "|", r['codigo_interno'])
