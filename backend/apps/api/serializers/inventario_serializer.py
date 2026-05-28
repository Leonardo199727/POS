from rest_framework import serializers
from apps.inventory.models import Inventario


class StockCriticoSerializer(serializers.ModelSerializer):
    """
    Serializer plano para el endpoint de stock crítico.
    Aplana Inventario → VarianteProducto → Producto en un solo objeto.
    """
    id = serializers.IntegerField(source='pk', read_only=True)
    codigo_interno = serializers.CharField(
        source='variante.producto.codigo_interno',
        read_only=True,
    )
    producto_nombre = serializers.CharField(
        source='variante.producto.nombre',
        read_only=True,
    )
    stock_actual = serializers.IntegerField(read_only=True)
    stock_minimo = serializers.IntegerField(read_only=True)

    class Meta:
        model = Inventario
        fields = [
            'id',
            'codigo_interno',
            'producto_nombre',
            'stock_actual',
            'stock_minimo',
        ]


class UpdateStockSerializer(serializers.Serializer):
    """
    Serializer para actualizar únicamente el stock_actual
    de un registro de Inventario vía PATCH.
    """
    stock_actual = serializers.IntegerField(
        min_value=0,
        help_text='Nuevo valor de stock. Debe ser ≥ 0.',
    )
