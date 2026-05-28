from django.conf import settings
from django.db import models


class Cliente(models.Model):
    """
    Información de clientes con control de crédito.
    Tabla: cliente — DB_model.md Módulo 2.
    """
    nombre = models.CharField(
        max_length=150,
        verbose_name='Nombre',
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        default='',
        db_index=True,
        verbose_name='Teléfono',
    )
    email = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Correo electrónico',
    )
    direccion = models.TextField(
        blank=True,
        default='',
        verbose_name='Dirección',
    )
    tipo_cliente = models.CharField(
        max_length=50,
        default='general',
        verbose_name='Tipo de cliente',
    )
    limite_credito = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Límite de crédito',
        help_text='0 = sin crédito',
    )
    saldo_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Saldo pendiente actual',
        help_text='Campo desnormalizado, recalculable desde movimiento_credito',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
    )
    notas = models.TextField(
        blank=True,
        default='',
        verbose_name='Observaciones',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de registro',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última modificación',
    )

    class Meta:
        db_table = 'cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre'], name='idx_cliente_nombre'),
            models.Index(fields=['telefono'], name='idx_cliente_telefono'),
        ]

    def __str__(self) -> str:
        return self.nombre


class MovimientoCredito(models.Model):
    """
    Historial completo de movimientos de crédito del cliente.
    Tabla: movimiento_credito — DB_model.md Módulo 2.
    """

    class TipoMovimiento(models.TextChoices):
        CARGO_VENTA = 'cargo', 'Cargo por venta'
        ABONO_PAGO = 'abono', 'Abono por pago'
        AJUSTE = 'ajuste', 'Ajuste manual'

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='movimientos_credito',
        verbose_name='Cliente',
    )
    venta = models.ForeignKey(
        'sales.Venta',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_credito',
        verbose_name='Venta asociada',
    )
    pago = models.ForeignKey(
        'payments.Pago',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_credito',
        verbose_name='Pago asociado',
    )
    devolucion_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID de devolución',
        help_text='FK lógica a devolución (módulo aún no implementado)',
    )
    tipo = models.CharField(
        max_length=30,
        choices=TipoMovimiento.choices,
        verbose_name='Tipo de movimiento',
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Monto',
        help_text='Siempre positivo',
    )
    saldo_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Saldo antes del movimiento',
    )
    saldo_nuevo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Saldo después del movimiento',
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Descripción',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='movimientos_credito',
        verbose_name='Registrado por',
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha del movimiento',
    )

    class Meta:
        db_table = 'movimiento_credito'
        verbose_name = 'Movimiento de crédito'
        verbose_name_plural = 'Movimientos de crédito'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['cliente'], name='idx_mov_credito_cliente'),
        ]

    def __str__(self) -> str:
        return (
            f'{self.get_tipo_display()} — {self.cliente.nombre} '
            f'— ${self.monto}'
        )

