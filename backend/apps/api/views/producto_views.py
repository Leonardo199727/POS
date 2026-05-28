import re
from rest_framework import status, generics, filters
from rest_framework.response import Response
from apps.api.permissions import IsAdminOrVendedor
from rest_framework.permissions import IsAuthenticated

from django.db.models import Prefetch, Q
from apps.products.models import Producto, VarianteProducto, PrecioProducto, Categoria, Marca
from apps.api.serializers.producto_serializer import ProductoListSerializer, CategoriaSerializer, MarcaSerializer
from apps.api.serializers.producto_create_serializer import ProductoCreateSerializer
from apps.api.pagination import CustomPagination

def build_accent_regex(term):
    accents = {
        'a': '[aáAÁ]',
        'e': '[eéEÉ]',
        'i': '[iíIÍ]',
        'o': '[oóOÓ]',
        'u': '[uúUÚüÜ]',
    }
    res = ""
    for char in term.lower():
        if char in accents:
            res += accents[char]
        else:
            res += re.escape(char)
    return res

class AccentInsensitiveSearchFilter(filters.SearchFilter):
    def get_search_terms(self, request):
        params = request.query_params.get(self.search_param, '')
        params = params.replace('\x00', '')  # strip null characters
        params = params.replace(',', ' ')
        terms = params.split()
        return [build_accent_regex(term) for term in terms]

class ProductoListCreateAPIView(generics.ListCreateAPIView):
    """
    GET /api/productos/
    POST /api/productos/
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductoCreateSerializer
        return ProductoListSerializer
    pagination_class = CustomPagination
    filter_backends = [AccentInsensitiveSearchFilter]
    # Configure precise text-matching via Database Level explicitly using Django SearchFilter with Regex ($)
    search_fields = ['$nombre', '$codigo_interno', '$variantes__sku', '$variantes__nombre', '$variantes__codigos_barras__codigo']

    def get_queryset(self):
        # Evitar N+1: Prefetch todas las variantes activas, su inventario, precio vigente y códigos de barras
        variantes_prefetch = Prefetch(
            'variantes',
            queryset=VarianteProducto.objects.filter(activo=True).select_related('inventario').prefetch_related(
                Prefetch(
                    'precios',
                    queryset=PrecioProducto.objects.filter(vigente=True)
                ),
                'codigos_barras'
            )
        )
        
        qs = Producto.objects.filter(activo=True).select_related('marca', 'categoria').prefetch_related(variantes_prefetch)
        
        marca_id = self.request.query_params.get('marca')
        if marca_id and marca_id.isdigit():
            qs = qs.filter(marca_id=marca_id)
            
        return qs.distinct()

class ProductoRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/productos/<id>/
    PUT/PATCH /api/productos/<id>/
    DELETE /api/productos/<id>/
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]
    
    def get_serializer_class(self):
        # We can reuse the create serializer for full updates (nested variants logic)
        return ProductoCreateSerializer

    def get_queryset(self):
        # Prefetches to avoid N+1 reading the target product
        variantes_prefetch = Prefetch(
            'variantes',
            queryset=VarianteProducto.objects.filter(activo=True).select_related('inventario').prefetch_related(
                Prefetch(
                    'precios',
                    queryset=PrecioProducto.objects.filter(vigente=True)
                ),
                'codigos_barras'
            )
        )
        return Producto.objects.filter(activo=True).select_related('marca', 'categoria').prefetch_related(variantes_prefetch)

class CategoriaListAPIView(generics.ListCreateAPIView):
    """ GET /api/categorias/ — POST /api/categorias/ """
    permission_classes = [IsAuthenticated]
    serializer_class = CategoriaSerializer
    pagination_class = None

    def get_queryset(self):
        return Categoria.objects.filter(activo=True).order_by('nombre')

class MarcaListAPIView(generics.ListCreateAPIView):
    """ GET /api/marcas/ — POST /api/marcas/ """
    permission_classes = [IsAuthenticated]
    serializer_class = MarcaSerializer
    pagination_class = None

    def get_queryset(self):
        return Marca.objects.filter(activo=True).order_by('nombre')
