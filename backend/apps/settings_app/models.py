from django.db import models


class ConfiguracionNegocio(models.Model):
    """
    Modelo Singleton — almacena la configuración global del negocio.
    
    Solo debe existir una fila en la tabla. El acceso a esta fila
    se gestiona a través del servicio ConfiguracionService.
    """
    nombre_negocio = models.CharField(
        max_length=100,
        default='LMSolutions',
        verbose_name='Nombre del negocio',
        help_text='Aparece en el encabezado de los tickets impresos.',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización',
    )

    class Meta:
        verbose_name = 'Configuración del Negocio'
        verbose_name_plural = 'Configuración del Negocio'

    def __str__(self):
        return f'Configuración: {self.nombre_negocio}'

    def save(self, *args, **kwargs):
        """Forzar singleton: siempre pk=1."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> 'ConfiguracionNegocio':
        """Obtiene o crea la instancia singleton."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
