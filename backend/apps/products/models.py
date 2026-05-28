from django.conf import settings
from django.db import models


# ──────────────────────────────────────────────────────────────────────
# Catálogos base
# ──────────────────────────────────────────────────────────────────────

class TipoProducto(models.Model):
    """
    Tipos genéricos de producto (ropa, alimento, perfume, etc.).
    Tabla: tipo_producto — DB_model.md Módulo 3.
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del tipo',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
    )

    class Meta:
        db_table = 'tipo_producto'
        verbose_name = 'Tipo de producto'
        verbose_name_plural = 'Tipos de producto'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre


class Categoria(models.Model):
    """
    Categorías de producto (camisas, pantalones, abarrotes, etc.).
    Tabla: categoria — DB_model.md Módulo 3.
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre de la categoría',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
    )

    class Meta:
        db_table = 'categoria'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre


class Marca(models.Model):
    """
    Marcas de producto (Nike, Adidas, etc.).
    Tabla: marca — DB_model.md Módulo 3.
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre de la marca',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
    )

    class Meta:
        db_table = 'marca'
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre


# ──────────────────────────────────────────────────────────────────────
# Producto y Variantes
# ──────────────────────────────────────────────────────────────────────

class Producto(models.Model):
    """
    Definición general de productos.
    Tabla: producto — DB_model.md Módulo 3.
    """
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre del producto',
    )
    descripcion = models.TextField(
        blank=True,
        default='',
        verbose_name='Descripción',
    )
    codigo_interno = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name='Código interno',
    )
    tipo_producto = models.ForeignKey(
        TipoProducto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        verbose_name='Tipo de producto',
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        verbose_name='Categoría',
    )
    marca = models.ForeignKey(
        Marca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        verbose_name='Marca',
    )
    activo = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Activo',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última modificación',
    )

    class Meta:
        db_table = 'producto'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']

    def __str__(self) -> str:
        return f'{self.codigo_interno} — {self.nombre}'


class VarianteProducto(models.Model):
    """
    Variantes específicas de un producto.
    Todo producto debe tener al menos una variante "Default".
    Tabla: variante_producto — DB_model.md Módulo 3.
    """
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='variantes',
        verbose_name='Producto',
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre de la variante',
    )
    sku = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='SKU',
    )
    atributos = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Atributos flexibles',
        help_text='Ej: {"talla": "S", "color": "Negro"}',
    )
    es_default = models.BooleanField(
        default=False,
        verbose_name='Variante por defecto',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última modificación',
    )

    class Meta:
        db_table = 'variante_producto'
        verbose_name = 'Variante de producto'
        verbose_name_plural = 'Variantes de producto'
        ordering = ['producto', 'nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'nombre'],
                name='uq_variante_producto_nombre',
            ),
        ]
        indexes = [
            models.Index(fields=['producto'], name='idx_variante_producto'),
        ]

    def __str__(self) -> str:
        return f'{self.producto.nombre} — {self.nombre}'


# ──────────────────────────────────────────────────────────────────────
# Precios y Códigos de Barras
# ──────────────────────────────────────────────────────────────────────

class PrecioProducto(models.Model):
    """
    Precios versionados por variante.
    Cada cambio crea un nuevo registro; el anterior se marca como vigente=False.
    Tabla: precio_producto — DB_model.md Módulo 3.
    """
    variante = models.ForeignKey(
        VarianteProducto,
        on_delete=models.CASCADE,
        related_name='precios',
        verbose_name='Variante',
    )
    precio_compra = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Precio de compra',
        help_text='Solo visible para administrador',
    )
    precio_contado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Precio de contado',
    )
    precio_credito = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Precio a crédito',
    )
    porcentaje_ganancia = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Porcentaje de ganancia',
    )
    vigente = models.BooleanField(
        default=True,
        verbose_name='Vigente',
        help_text='Solo un precio vigente por variante',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='precios_registrados',
        verbose_name='Registrado por',
    )
    motivo_cambio = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Motivo del cambio',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de registro',
    )

    class Meta:
        db_table = 'precio_producto'
        verbose_name = 'Precio de producto'
        verbose_name_plural = 'Precios de producto'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['variante', 'vigente'],
                name='idx_precio_vigente',
            ),
        ]

    def __str__(self) -> str:
        estado = '✓' if self.vigente else '✗'
        return f'{self.variante} — ${self.precio_contado} [{estado}]'


class CodigoBarras(models.Model):
    """
    Códigos de barras asociados a variantes.
    Un producto puede tener múltiples códigos.
    Tabla: codigo_barras — DB_model.md Módulo 3.
    """
    variante = models.ForeignKey(
        VarianteProducto,
        on_delete=models.CASCADE,
        related_name='codigos_barras',
        verbose_name='Variante',
    )
    codigo = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name='Código de barras',
    )
    principal = models.BooleanField(
        default=False,
        verbose_name='Código principal',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de registro',
    )

    class Meta:
        db_table = 'codigo_barras'
        verbose_name = 'Código de barras'
        verbose_name_plural = 'Códigos de barras'

    def __str__(self) -> str:
        marca = ' (principal)' if self.principal else ''
        return f'{self.codigo}{marca}'
