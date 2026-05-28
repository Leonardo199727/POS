from apps.settings_app.models import ConfiguracionNegocio


class ConfiguracionService:
    """
    Capa de servicio para la configuración del negocio.
    
    Encapsula el acceso al modelo singleton, manteniendo
    los controladores delgados y la lógica centralizada.
    """

    @staticmethod
    def obtener_configuracion() -> dict:
        """
        Obtiene la configuración actual del negocio.
        
        Returns:
            dict con los campos de configuración.
        """
        config = ConfiguracionNegocio.load()
        return {
            'nombre_negocio': config.nombre_negocio,
        }

    @staticmethod
    def actualizar_configuracion(*, nombre_negocio: str | None = None) -> dict:
        """
        Actualiza uno o más campos de la configuración del negocio.
        
        Args:
            nombre_negocio: Nuevo nombre del negocio (opcional).
        
        Returns:
            dict con la configuración actualizada.
            
        Raises:
            ValueError: Si el nombre está vacío.
        """
        config = ConfiguracionNegocio.load()
        
        if nombre_negocio is not None:
            nombre_negocio = nombre_negocio.strip()
            if not nombre_negocio:
                raise ValueError('El nombre del negocio no puede estar vacío.')
            config.nombre_negocio = nombre_negocio
        
        config.save()
        
        return {
            'nombre_negocio': config.nombre_negocio,
        }
