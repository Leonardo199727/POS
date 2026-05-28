from django.conf import settings
from django.db import models


class Pago(models.Model):
    """
    Registro principal de pagos.
    Tabla: pago — Módulo Pagos.

    Un pago puede estar asociado a una venta (contado o crédito) o ser
    un abono libre a la cuenta de un cliente.

    - monto_cliente: monto que reduce la deuda del cliente.
    - cargo_tarjeta: suma de cargos por interés de tarjeta (NO afecta saldo).
    - total_cobrado: monto_cliente + cargo_tarjeta (lo que efectivamente se cobra).
    """
    venta = models.ForeignKey(
        'sales.Venta',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pagos',
        verbose_name='Venta asociada',
    )
    cliente = models.ForeignKey(
        'customers.Cliente',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pagos',
        verbose_name='Cliente',
    )
    monto_cliente = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Monto al cliente',
        help_text='Monto que reduce la deuda del cliente',
    )
    cargo_tarjeta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Cargo por tarjeta',
        help_text='Suma de cargos por interés de tarjeta',
    )
    total_cobrado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Total cobrado',
        help_text='monto_cliente + cargo_tarjeta',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='pagos',
        verbose_name='Registrado por',
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha del pago',
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
        db_table = 'pago'
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['venta'], name='idx_pago_venta'),
            models.Index(fields=['cliente'], name='idx_pago_cliente'),
        ]

    def __str__(self) -> str:
        if self.venta:
            return f'Pago #{self.pk} — Venta {self.venta.folio} — ${self.total_cobrado}'
        return f'Pago #{self.pk} — ${self.total_cobrado}'


class PagoDetalle(models.Model):
    """
    Desglose de métodos de pago dentro de un Pago.
    Tabla: pago_detalle — Módulo Pagos.

    Cada detalle representa un método de pago utilizado.
    Si metodo_pago == TARJETA y con_intereses == True, se calculan
    porcentaje_interes y cargo_generado.
    """

    class MetodoPago(models.TextChoices):
        EFECTIVO = 'efectivo', 'Efectivo'
        TARJETA = 'tarjeta', 'Tarjeta'
        TRANSFERENCIA = 'transferencia', 'Transferencia'

    pago = models.ForeignKey(
        Pago,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Pago',
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPago.choices,
        verbose_name='Método de pago',
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Monto',
    )
    con_intereses = models.BooleanField(
        default=False,
        verbose_name='Con intereses',
    )
    porcentaje_interes = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Porcentaje de interés',
    )
    cargo_generado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Cargo generado',
    )

    class Meta:
        db_table = 'pago_detalle'
        verbose_name = 'Detalle de pago'
        verbose_name_plural = 'Detalles de pago'

    def __str__(self) -> str:
        return (
            f'{self.get_metodo_pago_display()} — ${self.monto}'
            f'{f" (+${self.cargo_generado})" if self.cargo_generado else ""}'
        )
