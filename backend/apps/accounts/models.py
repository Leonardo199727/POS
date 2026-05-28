from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Usuario del sistema POS.
    Tabla: usuario — según DB_model.md Módulo 1.
    Extiende AbstractUser de Django y agrega campos específicos del negocio.
    """
    rol = models.ForeignKey(
        'security.Rol',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name='Rol asignado',
    )
    nombre_completo = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name='Nombre completo',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
    )
    forzar_cambio_password = models.BooleanField(
        default=False,
        verbose_name='Forzar cambio de contraseña',
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name='Última modificación',
    )

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.username

    # ------------------------------------------------------------------
    # Métodos de validación de rol — Fase 1
    # ------------------------------------------------------------------

    def es_admin(self):
        """Verifica si el usuario tiene rol ADMIN."""
        return self.rol is not None and self.rol.nombre == 'ADMIN'

    def es_vendedor(self):
        """Verifica si el usuario tiene rol VENDEDOR."""
        return self.rol is not None and self.rol.nombre == 'VENDEDOR'
