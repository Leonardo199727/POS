from apps.products.models import Producto, Categoria, Marca, VarianteProducto
from rest_framework import serializers

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre']

class VarianteListSerializer(serializers.Serializer):
    """
    Exporta datos de Variante pero haciéndolos pasar por un "Producto" para el Frontend.
    (Flattening).
    """
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.SerializerMethodField()
    codigo_interno = serializers.SerializerMethodField()
    activo = serializers.BooleanField(read_only=True)
    
    def get_nombre(self, obj):
        if obj.nombre and obj.nombre.lower() not in ['principal', 'default', '']:
            return f"{obj.producto.nombre} - {obj.nombre}"
        return obj.producto.nombre
        
    def get_codigo_interno(self, obj):
        return obj.sku or obj.producto.codigo_interno
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        
        stock = instance.inventario.stock_actual if hasattr(instance, 'inventario') and instance.inventario else 0
        precio_contado = None
        precio_credito = None
        precio_compra = None
        
        precios = instance.precios.all()
        if precios:
            p = precios[0]
            precio_contado = p.precio_contado
            precio_credito = p.precio_credito
            precio_compra = p.precio_compra

        ret['precio_contado'] = precio_contado
        ret['precio_credito'] = precio_credito
        ret['stock_disponible'] = stock
        
        ret['marca'] = {'id': instance.producto.marca.id, 'nombre': instance.producto.marca.nombre} if instance.producto.marca else None
        ret['categoria'] = {'id': instance.producto.categoria.id, 'nombre': instance.producto.categoria.nombre} if instance.producto.categoria else None
        ret['variantes'] = []
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if getattr(request.user.rol, 'nombre', '') == 'ADMIN':
                ret['precio_compra'] = precio_compra
                
        return ret


class ProductoListSerializer(serializers.Serializer):
    """
    Serializador limpio de Producto.
    Aplica seguridad RBAC excluyendo precio_compra y margen si es VENDEDOR.
    Evita queries N+1 usando el _extract_prices que lee desde lo precargado.
    """
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    descripcion = serializers.CharField(read_only=True)
    codigo_interno = serializers.CharField(read_only=True)
    activo = serializers.BooleanField(read_only=True)
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        
        prices_and_stock = self._extract_prices(instance)
        
        ret['precio_contado'] = prices_and_stock['precio_contado']
        ret['precio_credito'] = prices_and_stock['precio_credito']
        ret['stock_disponible'] = prices_and_stock['stock_disponible']
        
        # Anidar información relacional para el frontend
        ret['marca'] = {'id': instance.marca.id, 'nombre': instance.marca.nombre} if instance.marca else None
        ret['categoria'] = {'id': instance.categoria.id, 'nombre': instance.categoria.nombre} if instance.categoria else None
        
        # Anidar información de variantes y stock granular
        ret['variantes'] = prices_and_stock['variantes_list']
        
        request = self.context.get('request')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            rol_nombre = getattr(request.user.rol, 'nombre', '')
            if rol_nombre == 'ADMIN':
                ret['precio_compra'] = prices_and_stock['precio_compra']
                ret['margen'] = prices_and_stock['margen']
                
        return ret
        
    def _extract_prices(self, producto):
        """
        Extrae precios e inventario SIN realizar queries adicionales a BD.
        Asume que 'variantes', 'variantes__inventario' y 'variantes__precios' 
        vienen provistos por un prefetch_related/select_related.
        """
        data = {
            'precio_contado': None,
            'precio_credito': None,
            'precio_compra': None,
            'margen': None,
            'stock_disponible': 0,
            'variantes_list': []
        }
        
        # Validamos en memoria con .all() del prefetch
        variantes = producto.variantes.all()
        if not variantes:
            return data
            
        variante_default = next((v for v in variantes if v.es_default), variantes[0])
        
        stock_total = 0
        
        # Procesar todas las variantes para el modal del frontend
        for var in variantes:
            var_data = {
                'id': var.id,
                'nombre': var.nombre,
                'sku': var.sku,
                'es_default': var.es_default,
                'precio_contado': None,
                'precio_credito': None,
                'precio_compra': None,
                'stock_actual': 0,
                'stock_minimo': 0,
                'codigo_barras': None
            }
            
            # Stock individual
            if hasattr(var, 'inventario') and var.inventario is not None:
                var_data['stock_actual'] = var.inventario.stock_actual
                var_data['stock_minimo'] = var.inventario.stock_minimo
                stock_total += var.inventario.stock_actual
                
            # Precios precargados individual
            var_precios = var.precios.all()
            if var_precios:
                var_data['precio_contado'] = var_precios[0].precio_contado
                var_data['precio_credito'] = var_precios[0].precio_credito
                var_data['precio_compra'] = var_precios[0].precio_compra
                
            # Codigos prefeheados individual
            # Se previene querie N+1 porque variades__codigos_barras no fue especificado aun en prefetch_related, 
            # Pero en la vista agregaremos el prefetch de codigos para que no cause error, sino fallbacks:
            if hasattr(var, 'codigos_barras'):
                cds = var.codigos_barras.all()
                if cds: var_data['codigo_barras'] = cds[0].codigo
            
            data['variantes_list'].append(var_data)
        
        # RBAC: Ocultar precio_compra de variantes si no es ADMIN
        request = self.context.get('request')
        is_admin = False
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            is_admin = getattr(request.user.rol, 'nombre', '') == 'ADMIN'
        
        if not is_admin:
            for vd in data['variantes_list']:
                vd.pop('precio_compra', None)
            
        data['stock_disponible'] = stock_total
        
        # Precios principales basados en variante por defecto
        precios_defecto = variante_default.precios.all()
        if precios_defecto:
            precio_vigente = precios_defecto[0]
            data['precio_contado'] = precio_vigente.precio_contado
            data['precio_credito'] = precio_vigente.precio_credito
            data['precio_compra'] = precio_vigente.precio_compra
        
        # Calcular margen solo para que esté disponible para ADMIN
        if data['precio_compra'] and data['precio_contado'] and data['precio_compra'] > 0:
            margen_num = ((data['precio_contado'] - data['precio_compra']) / data['precio_compra']) * 100
            data['margen'] = round(margen_num, 2)
            
        return data
