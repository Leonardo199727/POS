from django.conf import settings
from django.db import models


class Inventario(models.Model):
    """
    Stock actual por variante. Un registro por variante de producto.
    Tabla: inventario — DB_model.md Módulo 4.
    """
    variante = models.OneToOneField(
        'products.VarianteProducto',
        on_delete=models.CASCADE,
        related_name='inventario',
        verbose_name='Variante',
    )
    stock_actual = models.IntegerField(
        default=0,
        verbose_name='Stock actual',
    )
    stock_minimo = models.IntegerField(
        default=0,
        verbose_name='Stock mínimo',
        help_text='Umbral para alerta de stock bajo',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización',
    )

    class Meta:
        db_table = 'inventario'
        verbose_name = 'Inventario'
        verbose_name_plural = 'Inventarios'
        indexes = [
            models.Index(fields=['stock_actual'], name='idx_inventario_stock'),
            models.Index(fields=['variante'], name='idx_inventario_variante'),
        ]

    def __str__(self) -> str:
        return f'{self.variante} — Stock: {self.stock_actual}'

    @property
    def stock_bajo(self) -> bool:
        """Indica si el stock está por debajo del mínimo."""
        return self.stock_actual <= self.stock_minimo


class MovimientoInventario(models.Model):
    """
    Historial completo de entradas, salidas y ajustes de inventario.
    Tabla: movimiento_inventario — DB_model.md Módulo 4.
    """

    class TipoMovimiento(models.TextChoices):
        ENTRADA_COMPRA = 'entrada_compra', 'Entrada por compra'
        ENTRADA_AJUSTE = 'entrada_ajuste', 'Entrada por ajuste'
        ENTRADA_DEVOLUCION = 'entrada_devolucion', 'Entrada por devolución'
        SALIDA_VENTA = 'salida_venta', 'Salida por venta'
        SALIDA_MERMA = 'salida_merma', 'Salida por merma'
        SALIDA_SIN_STOCK = 'salida_sin_stock', 'Salida sin stock'
        AJUSTE_MANUAL = 'ajuste_manual', 'Ajuste manual'

    class ReferenciaTipo(models.TextChoices):
        VENTA = 'venta', 'Venta'
        AJUSTE = 'ajuste', 'Ajuste'
        MERMA = 'merma', 'Merma'
        DEVOLUCION = 'devolucion', 'Devolución'

    inventario = models.ForeignKey(
        Inventario,
        on_delete=models.CASCADE,
        related_name='movimientos',
        verbose_name='Inventario',
    )
    variante = models.ForeignKey(
        'products.VarianteProducto',
        on_delete=models.CASCADE,
        related_name='movimientos_inventario',
        verbose_name='Variante',
        help_text='Redundancia para consultas rápidas',
    )
    tipo_movimiento = models.CharField(
        max_length=30,
        choices=TipoMovimiento.choices,
        db_index=True,
        verbose_name='Tipo de movimiento',
    )
    cantidad = models.IntegerField(
        verbose_name='Cantidad',
        help_text='Positivo = entrada, Negativo = salida',
    )
    stock_anterior = models.IntegerField(
        verbose_name='Stock antes del movimiento',
    )
    stock_nuevo = models.IntegerField(
        verbose_name='Stock después del movimiento',
    )
    referencia_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID de referencia',
        help_text='ID de venta/ajuste/devolución que originó',
    )
    referencia_tipo = models.CharField(
        max_length=30,
        choices=ReferenciaTipo.choices,
        null=True,
        blank=True,
        verbose_name='Tipo de referencia',
    )
    motivo = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Motivo',
        help_text='Obligatorio en ajustes y mermas',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='movimientos_inventario',
        verbose_name='Usuario responsable',
    )
    autorizacion_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID de autorización',
        help_text='Si requirió autorización',
    )
    fecha = models.DateTimeField(
        db_index=True,
        verbose_name='Fecha del movimiento',
    )

    class Meta:
        db_table = 'movimiento_inventario'
        verbose_name = 'Movimiento de inventario'
        verbose_name_plural = 'Movimientos de inventario'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['variante'], name='idx_mov_inv_variante'),
        ]

    def __str__(self) -> str:
        return (
            f'{self.get_tipo_movimiento_display()} — '
            f'{self.variante} — Cant: {self.cantidad}'
        )
