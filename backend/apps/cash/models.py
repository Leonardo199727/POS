from __future__ import annotations

from django.db import models
from django.utils import timezone


class Caja(models.Model):
    """
    Registro de apertura y cierre de caja.

    Una sola caja abierta por usuario durante la jornada.
    El cierre calcula los totales esperados por método de pago
    y el usuario declara los totales contados para determinar diferencias.

    Toda la lógica de negocio reside en CajaService.
    """

    class Estado(models.TextChoices):
        ABIERTA = 'abierta', 'Abierta'
        CERRADA = 'cerrada', 'Cerrada'

    usuario_apertura = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='cajas_abiertas',
        verbose_name='usuario apertura',
    )
    usuario_cierre = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='cajas_cerradas',
        null=True,
        blank=True,
        verbose_name='usuario cierre',
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ABIERTA,
    )
    fecha_apertura = models.DateTimeField(default=timezone.now)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    monto_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='monto inicial',
    )

    # ── Totales esperados (calculados por el sistema al cierre) ──
    total_efectivo_esperado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    total_tarjeta_esperado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    total_transferencia_esperado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )

    # ── Totales contados/declarados (ingresados por el usuario al cierre) ──
    total_efectivo_contado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    total_tarjeta_declarado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    total_transferencia_declarado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )

    # ── Diferencias (contado - esperado) ──
    diferencia_efectivo = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    diferencia_tarjeta = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    diferencia_transferencia = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )

    observaciones_cierre = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'caja'
        constraints = [
            models.UniqueConstraint(
                fields=['usuario_apertura'],
                condition=models.Q(estado='abierta'),
                name='unique_caja_abierta_por_usuario',
            ),
        ]
        indexes = [
            models.Index(
                fields=['usuario_apertura'],
                name='idx_caja_usuario',
            ),
            models.Index(
                fields=['estado'],
                name='idx_caja_estado',
            ),
        ]

    def __str__(self) -> str:
        return (
            f'Caja #{self.pk} — {self.get_estado_display()} '
            f'({self.usuario_apertura})'
        )


class MovimientoCaja(models.Model):
    """
    Registro de entradas y salidas de dinero asociadas a la caja.

    Se registran TODOS los métodos de pago para trazabilidad completa.
    El campo `tipo` indica si es entrada o salida.
    El campo `metodo_pago` indica el medio (efectivo, tarjeta, transferencia).
    El campo `origen` indica la fuente (venta, abono, manual, devolucion).

    Toda la lógica de negocio reside en CajaService.
    """

    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SALIDA = 'salida', 'Salida'

    class MetodoPago(models.TextChoices):
        EFECTIVO = 'efectivo', 'Efectivo'
        TARJETA = 'tarjeta', 'Tarjeta'
        TRANSFERENCIA = 'transferencia', 'Transferencia'

    class Origen(models.TextChoices):
        VENTA = 'venta', 'Venta'
        ABONO = 'abono', 'Abono'
        MANUAL = 'manual', 'Manual'
        DEVOLUCION = 'devolucion', 'Devolución'

    caja = models.ForeignKey(
        Caja,
        on_delete=models.PROTECT,
        related_name='movimientos',
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoMovimiento.choices,
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPago.choices,
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    concepto = models.CharField(max_length=200)
    origen = models.CharField(
        max_length=30,
        choices=Origen.choices,
        null=True,
        blank=True,
    )
    referencia_id = models.IntegerField(null=True, blank=True)
    usuario = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='movimientos_caja',
    )
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'movimiento_caja'
        indexes = [
            models.Index(
                fields=['caja'],
                name='idx_movimiento_caja_caja',
            ),
        ]

    def __str__(self) -> str:
        return (
            f'{self.get_tipo_display()} — ${self.monto} '
            f'({self.get_metodo_pago_display()})'
        )
