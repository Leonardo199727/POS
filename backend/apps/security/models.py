from django.db import models


class Rol(models.Model):
    """
    Roles del sistema (ADMIN, VENDEDOR).
    Tabla: rol — según DB_model.md Módulo 1.
    """
    nombre = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name='Nombre del rol',
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Descripción',
    )
    activo = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Activo',
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Última modificación',
    )

    class Meta:
        db_table = 'rol'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['nombre'],
                name='uq_rol_nombre',
            ),
        ]

    def __str__(self):
        return self.nombre
