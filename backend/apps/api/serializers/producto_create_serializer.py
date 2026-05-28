import uuid
from django.db import transaction
from rest_framework import serializers

from apps.products.models import (
    Producto, 
    VarianteProducto, 
    PrecioProducto, 
    CodigoBarras,
    TipoProducto,
    Categoria,
    Marca
)
from apps.inventory.models import Inventario
from apps.core.permissions.permission_codes import PermissionCodes
from apps.core.permissions.permission_service import PermissionService

class ProductoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer orquestador para creación atómica de productos y dependencias.
    Maneja el payload "plano" de la UI.
    """
    categoria_id = serializers.IntegerField(required=False, allow_null=True)
    marca_id = serializers.IntegerField(required=False, allow_null=True)
    marca_nombre = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    
    # Precios
    precio_compra = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    precio_contado = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    precio_credito = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    
    # Inventario
    stock_inicial = serializers.IntegerField(required=False, default=0)
    stock_minimo = serializers.IntegerField(required=False, default=0, allow_null=True)
    
    # Códigos y Autogeneración
    sku = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    codigo_barras = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    auto_generar_codigo = serializers.BooleanField(required=False, default=False)
    # Variantes opcionales
    tiene_variantes = serializers.BooleanField(required=False, default=False, write_only=True)
    variantes = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        write_only=True
    )

    class Meta:
        model = Producto
        fields = [
            'nombre', 'categoria_id', 'marca_id', 'marca_nombre', 
            'precio_compra', 'precio_contado', 'precio_credito',
            'stock_inicial', 'stock_minimo', 
            'sku', 'codigo_barras', 'auto_generar_codigo',
            'tiene_variantes', 'variantes'
        ]
        
    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        
        # Extracción de campos no pertenecientes a Producto maestro
        categoria_id = validated_data.pop('categoria_id', None)
        marca_id = validated_data.pop('marca_id', None)
        marca_nombre = validated_data.pop('marca_nombre', '').strip()
        
        precio_compra = validated_data.pop('precio_compra', None)
        precio_contado = validated_data.pop('precio_contado')
        precio_credito = validated_data.pop('precio_credito', None)
        
        stock_inicial = validated_data.pop('stock_inicial', 0)
        stock_minimo = validated_data.pop('stock_minimo', 0)
        if stock_minimo is None: stock_minimo = 0
        
        sku = validated_data.pop('sku', '')
        codigo_barras = validated_data.pop('codigo_barras', '')
        auto_generar_codigo = validated_data.pop('auto_generar_codigo', False)
        
        tiene_variantes = validated_data.pop('tiene_variantes', False)
        variantes_data = validated_data.pop('variantes', [])
        
        # Validar permisos de precio de compra
        # Si el usuario mandó precio_compra, verificamos que tenga permisos
        if precio_compra is not None:
            try:
                PermissionService.check(user, PermissionCodes.VIEW_COST_PRICE)
            except Exception:
                # Si no tiene permiso, ignoramos el valor del payload para protegerlo
                precio_compra = None
                
        # --- 1. Crear Porducto Maestro ---
        producto = Producto(
            nombre=validated_data['nombre'],
            activo=True
        )
        
        # Asignar relaciones FK
        if categoria_id:
            try:
                producto.categoria = Categoria.objects.get(pk=categoria_id)
            except Categoria.DoesNotExist:
                pass
        else:
            # Lógica Genérica Default (Optional fallback si requieres)
            pass
            
        if marca_id:
            try:
                producto.marca = Marca.objects.get(pk=marca_id)
            except Marca.DoesNotExist:
                pass
        elif marca_nombre:
            marca, _ = Marca.objects.get_or_create(
                nombre__iexact=marca_nombre, 
                defaults={'nombre': marca_nombre.upper(), 'activo': True}
            )
            producto.marca = marca
        
        # --- 2. Crear Variantes e Inventario ---
        if auto_generar_codigo or not sku:
            import random
            
            # 2 letras del producto
            prod_chars = producto.nombre.replace(" ", "")[:2].upper()
            prod_chars = prod_chars.ljust(2, 'X') # Rellenar con X si el nombre es muy corto
            
            # 2 letras de la marca
            marca_chars = "XX"
            if producto.marca and producto.marca.nombre:
                marca_chars = producto.marca.nombre.replace(" ", "")[:2].upper()
                marca_chars = marca_chars.ljust(2, 'X')
                
            # 3 números aleatorios
            ran_nums = f"{random.randint(0, 999):03d}"
            
            generated_code = f"{prod_chars}{marca_chars}{ran_nums}"
            
            producto.codigo_interno = generated_code
            base_sku = generated_code
        else:
            producto.codigo_interno = sku
            base_sku = sku
            
        producto.save()
        
        if not tiene_variantes or not variantes_data:
            # Producto Simple (1 sola variante por defecto)
            variante = VarianteProducto.objects.create(
                producto=producto,
                nombre="Principal", # Nombre default acordado
                sku=base_sku,
                es_default=True,
                activo=True
            )
            
            Inventario.objects.create(
                variante=variante,
                stock_actual=stock_inicial,
                stock_minimo=stock_minimo
            )
            
            PrecioProducto.objects.create(
                variante=variante,
                precio_compra=precio_compra,
                precio_contado=precio_contado,
                precio_credito=precio_credito,
                vigente=True,
                usuario=user,
                motivo_cambio='Precio inicial al crear producto.'
            )
            
            if codigo_barras:
                CodigoBarras.objects.create(
                    variante=variante,
                    codigo=codigo_barras,
                    principal=True
                )
        else:
            # Producto con Múltiples Variantes
            for index, var_data in enumerate(variantes_data):
                var_nombre = var_data.get('nombre', f"Var-{index+1}")
                var_sku = var_data.get('sku', '')
                if not var_sku:
                    var_sku = f"{base_sku}-{index+1}"
                    
                var_stock = int(var_data.get('stock_inicial', 0))
                var_codigo = var_data.get('codigo_barras', '')
                
                # Precios individuales por variante con fallback al precio global
                var_precio_contado = var_data.get('precio_contado') or precio_contado
                var_precio_credito = var_data.get('precio_credito') or precio_credito
                var_precio_compra = var_data.get('precio_compra') or precio_compra
                
                is_default = (index == 0) # La primera variante es la default
                
                variante = VarianteProducto.objects.create(
                    producto=producto,
                    nombre=var_nombre,
                    sku=var_sku,
                    es_default=is_default,
                    activo=True
                )
                
                Inventario.objects.create(
                    variante=variante,
                    stock_actual=var_stock,
                    stock_minimo=stock_minimo
                )
                
                PrecioProducto.objects.create(
                    variante=variante,
                    precio_compra=var_precio_compra,
                    precio_contado=var_precio_contado,
                    precio_credito=var_precio_credito,
                    vigente=True,
                    usuario=user,
                    motivo_cambio='Precio inicial de variante.'
                )
                
                if var_codigo:
                    CodigoBarras.objects.create(
                        variante=variante,
                        codigo=var_codigo,
                        principal=True
                    )
            
        return producto

    @transaction.atomic
    def update(self, instance, validated_data):
        user = self.context['request'].user
        
        categoria_id = validated_data.pop('categoria_id', None)
        marca_id = validated_data.pop('marca_id', None)
        marca_nombre = validated_data.pop('marca_nombre', '').strip()
        
        precio_compra = validated_data.pop('precio_compra', None)
        precio_contado = validated_data.pop('precio_contado', None)
        precio_credito = validated_data.pop('precio_credito', None)
        
        stock_inicial = validated_data.pop('stock_inicial', None)
        stock_minimo = validated_data.pop('stock_minimo', None)
        
        sku = validated_data.pop('sku', None)
        codigo_barras = validated_data.pop('codigo_barras', None)
        
        validated_data.pop('auto_generar_codigo', None)
        tiene_variantes = validated_data.pop('tiene_variantes', False)
        nuevas_variantes_data = validated_data.pop('variantes', [])
        
        variant_id = self.initial_data.get('variant_id')

        if 'nombre' in validated_data:
            instance.nombre = validated_data['nombre']

        if categoria_id:
            try:
                instance.categoria = Categoria.objects.get(pk=categoria_id)
            except Categoria.DoesNotExist:
                pass
        
        if marca_id:
            try:
                instance.marca = Marca.objects.get(pk=marca_id)
            except Marca.DoesNotExist:
                pass
        elif marca_nombre:
            marca, _ = Marca.objects.get_or_create(
                nombre__iexact=marca_nombre, 
                defaults={'nombre': marca_nombre.upper(), 'activo': True}
            )
            instance.marca = marca
            
        instance.save()
        
        if variant_id:
            try:
                variante = instance.variantes.get(id=variant_id)
            except VarianteProducto.DoesNotExist:
                variante = instance.variantes.filter(es_default=True).first()
        else:
            variante = instance.variantes.filter(es_default=True).first()
            
        if not variante:
            variante = instance.variantes.first()
            
        # Recuperar sku y código_barras directamente de initial_data para no perder strings vacíos
        sku = self.initial_data.get('sku')
        codigo_barras = self.initial_data.get('codigo_barras')
        
        if variante:
            if sku is not None:
                if sku == "":
                    variante.sku = ""
                    variante.save()
                else:
                    if VarianteProducto.objects.exclude(id=variante.id).filter(sku=sku).exists():
                        raise serializers.ValidationError({"sku": "Este SKU o Código Interno ya está en uso."})
                    variante.sku = sku
                    variante.save()
                
                # Sincronizar codigo_interno del producto padre con el SKU de la variante default
                if variante.es_default:
                    instance.codigo_interno = sku if sku else instance.codigo_interno
                    instance.save(update_fields=['codigo_interno'])
            
            if stock_inicial is not None or stock_minimo is not None:
                inv = getattr(variante, 'inventario', None)
                if inv:
                    if stock_inicial is not None:
                        inv.stock_actual = stock_inicial
                    if stock_minimo is not None:
                        inv.stock_minimo = stock_minimo
                    inv.save()
            
            if precio_contado is not None or precio_credito is not None or precio_compra is not None:
                active_price = variante.precios.filter(vigente=True).first()
                if active_price:
                    has_changes = False
                    if precio_contado is not None and active_price.precio_contado != precio_contado: 
                        has_changes = True
                    if precio_credito is not None and active_price.precio_credito != precio_credito: 
                        has_changes = True
                        
                    if precio_compra is not None:
                        try:
                            PermissionService.check(user, PermissionCodes.VIEW_COST_PRICE)
                            if active_price.precio_compra != precio_compra: has_changes = True
                        except Exception:
                            precio_compra = active_price.precio_compra
                    else:
                        precio_compra = active_price.precio_compra
                        
                    if has_changes:
                        active_price.vigente = False
                        active_price.save()
                        
                        PrecioProducto.objects.create(
                            variante=variante,
                            precio_compra=precio_compra if precio_compra is not None else active_price.precio_compra,
                            precio_contado=precio_contado if precio_contado is not None else active_price.precio_contado,
                            precio_credito=precio_credito if precio_credito is not None else active_price.precio_credito,
                            vigente=True,
                            usuario=user,
                            motivo_cambio='Actualizado en edición de producto'
                        )
                        
            if codigo_barras is not None:
                cb = variante.codigos_barras.filter(principal=True).first()
                if not cb:
                    cb = variante.codigos_barras.first()
                    
                if codigo_barras == "":
                    # El usuario vació el input, borramos el código
                    if cb:
                        cb.delete()
                else:
                    if CodigoBarras.objects.exclude(variante=variante).filter(codigo=codigo_barras).exists():
                        raise serializers.ValidationError({"codigo_barras": "El código de barras ya pertenece a otro registro de la base de datos."})
                        
                    if cb:
                        if cb.codigo != codigo_barras:
                            cb.codigo = codigo_barras
                            cb.save()
                    else:
                        CodigoBarras.objects.create(variante=variante, codigo=codigo_barras, principal=True)

        # === Crear nuevas variantes si se está expandiendo un producto simple ===
        if tiene_variantes and nuevas_variantes_data:
            base_sku = instance.codigo_interno or instance.nombre[:3].upper()
            existing_count = instance.variantes.count()
            
            # Obtener precios globales como fallback (del formulario o de la variante existente)
            global_precio_contado = precio_contado
            global_precio_credito = precio_credito
            global_precio_compra = precio_compra
            
            # Si no se enviaron precios globales, usar los de la variante default existente
            if not global_precio_contado or not global_precio_credito:
                default_var = instance.variantes.filter(es_default=True).first()
                if default_var:
                    active = default_var.precios.filter(vigente=True).first()
                    if active:
                        global_precio_contado = global_precio_contado or active.precio_contado
                        global_precio_credito = global_precio_credito or active.precio_credito
                        global_precio_compra = global_precio_compra or active.precio_compra
            
            for idx, var_data in enumerate(nuevas_variantes_data):
                var_nombre = var_data.get('nombre', f"Var-{existing_count + idx + 1}")
                var_sku = var_data.get('sku', '')
                if not var_sku:
                    var_sku = f"{base_sku}-{existing_count + idx + 1}"
                
                var_stock = int(var_data.get('stock_inicial', 0))
                var_codigo_barras = var_data.get('codigo_barras', '')
                
                # Precios individuales con fallback al global
                var_precio_contado = var_data.get('precio_contado') or global_precio_contado
                var_precio_credito = var_data.get('precio_credito') or global_precio_credito
                var_precio_compra = var_data.get('precio_compra') or global_precio_compra
                
                nueva_variante = VarianteProducto.objects.create(
                    producto=instance,
                    nombre=var_nombre,
                    sku=var_sku,
                    es_default=False,
                    activo=True
                )
                
                Inventario.objects.create(
                    variante=nueva_variante,
                    stock_actual=var_stock,
                    stock_minimo=stock_minimo or 0
                )
                
                PrecioProducto.objects.create(
                    variante=nueva_variante,
                    precio_compra=var_precio_compra,
                    precio_contado=var_precio_contado,
                    precio_credito=var_precio_credito,
                    vigente=True,
                    usuario=user,
                    motivo_cambio='Nueva variante agregada en edición.'
                )
                
                if var_codigo_barras:
                    CodigoBarras.objects.create(
                        variante=nueva_variante,
                        codigo=var_codigo_barras,
                        principal=True
                    )

        return instance

    def to_representation(self, instance):
        from apps.api.serializers.producto_serializer import ProductoListSerializer
        return ProductoListSerializer(instance, context=self.context).data
