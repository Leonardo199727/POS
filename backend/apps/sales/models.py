from django.conf import settings
from django.db import models


class Venta(models.Model):
    """
    Registro principal de ventas.
    Tabla: venta — DB_model.md Módulo 5.
    """

    class TipoVenta(models.TextChoices):
        CONTADO = 'contado', 'Contado'
        CREDITO = 'credito', 'Crédito'

    class Estado(models.TextChoices):
        EN_PROCESO = 'en_proceso', 'En proceso'
        COMPLETADA = 'completada', 'Completada'
        PARCIAL = 'parcial', 'Parcialmente pagada'
        LIQUIDADA = 'liquidada', 'Liquidada'
        CANCELADA = 'cancelada', 'Cancelada'

    folio = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        verbose_name='Folio',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ventas',
        verbose_name='Vendedor',
    )
    cliente = models.ForeignKey(
        'customers.Cliente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas',
        verbose_name='Cliente',
    )
    tipo_venta = models.CharField(
        max_length=20,
        choices=TipoVenta.choices,
        verbose_name='Tipo de venta',
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.EN_PROCESO,
        db_index=True,
        verbose_name='Estado',
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Subtotal',
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Total',
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
        db_table = 'venta'
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['folio'], name='idx_venta_folio'),
        ]

    def __str__(self) -> str:
        return f'{self.folio} — {self.get_estado_display()}'


class DetalleVenta(models.Model):
    """
    Productos incluidos en cada venta.
    Tabla: detalle_venta — DB_model.md Módulo 5.
    """
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Venta',
    )
    variante = models.ForeignKey(
        'products.VarianteProducto',
        on_delete=models.PROTECT,
        related_name='detalles_venta',
        verbose_name='Variante',
    )
    cantidad = models.IntegerField(
        verbose_name='Cantidad',
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Precio unitario',
        help_text='Precio congelado al momento de la venta',
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Subtotal línea',
    )

    class Meta:
        db_table = 'detalle_venta'
        verbose_name = 'Detalle de venta'
        verbose_name_plural = 'Detalles de venta'
        constraints = [
            models.UniqueConstraint(
                fields=['venta', 'variante'],
                name='uq_detalle_venta_variante',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.venta.folio} — {self.variante} x{self.cantidad}'
