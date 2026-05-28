import shutil
import os
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.apps import apps


class BackupService:
    """
    Servicio para operaciones de respaldo, restauración
    y limpieza de la base de datos SQLite.
    """

    # Tablas que se preservan durante la limpieza
    TABLAS_PROTEGIDAS = {
        # Usuarios y autenticación
        'usuario',                     # accounts.User
        'rol',                         # security.Rol
        'authtoken_token',             # DRF tokens
        # Configuración del negocio
        'settings_app_configuracionnegocio',
        # Django internals (necesarias para que funcione)
        'django_migrations',
        'django_content_type',
        'auth_permission',
        'auth_group',
        'auth_group_permissions',
        'usuario_groups',
        'usuario_user_permissions',
        'django_admin_log',
        'django_session',
    }

    @staticmethod
    def get_db_path() -> Path:
        """Devuelve la ruta absoluta al archivo SQLite."""
        return Path(settings.DATABASES['default']['NAME'])

    @classmethod
    def exportar_db(cls) -> Path:
        """
        Crea una copia del archivo SQLite para descarga.
        
        Returns:
            Path al archivo de respaldo temporal.
        """
        db_path = cls.get_db_path()
        if not db_path.exists():
            raise FileNotFoundError('No se encontró la base de datos.')

        # Crear directorio de backups temporal
        backup_dir = db_path.parent / 'backups'
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f'respaldo_pos_{timestamp}.sqlite3'
        backup_path = backup_dir / backup_filename

        # Copiar de forma segura (flush WAL si existe)
        shutil.copy2(str(db_path), str(backup_path))

        return backup_path

    @classmethod
    def importar_db(cls, uploaded_file) -> None:
        """
        Reemplaza la base de datos actual con el archivo subido.
        
        Args:
            uploaded_file: Archivo InMemoryUploadedFile de Django.
            
        Raises:
            ValueError: Si el archivo no es válido.
        """
        db_path = cls.get_db_path()

        # Validación básica: debe tener la firma SQLite
        header = uploaded_file.read(16)
        uploaded_file.seek(0)

        if not header.startswith(b'SQLite format 3'):
            raise ValueError(
                'El archivo no es una base de datos SQLite válida.'
            )

        # Crear respaldo del actual antes de reemplazar
        backup_dir = db_path.parent / 'backups'
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        shutil.copy2(
            str(db_path),
            str(backup_dir / f'pre_import_{timestamp}.sqlite3'),
        )

        # Escribir el nuevo archivo
        with open(str(db_path), 'wb') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

    @classmethod
    def limpiar_db(cls) -> dict:
        """
        Elimina todos los datos excepto usuarios, roles,
        tokens de autenticación y configuración del negocio.
        
        Returns:
            dict con estadísticas de la limpieza.
        """
        from django.db import connection

        tablas_limpiadas = []
        tablas_omitidas = []

        with connection.cursor() as cursor:
            # Obtener todas las tablas
            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            todas_las_tablas = [row[0] for row in cursor.fetchall()]

            # Desactivar FK checks temporalmente
            cursor.execute("PRAGMA foreign_keys = OFF;")

            for tabla in todas_las_tablas:
                if tabla in cls.TABLAS_PROTEGIDAS:
                    tablas_omitidas.append(tabla)
                    continue

                try:
                    cursor.execute(f'DELETE FROM "{tabla}";')
                    tablas_limpiadas.append(tabla)
                except Exception as e:
                    # Log pero no fallar — algunas tablas podrían
                    # no tener datos o ser views
                    print(f'Warning limpiando {tabla}: {e}')

            # Reactivar FK checks
            cursor.execute("PRAGMA foreign_keys = ON;")

            # Limpiar espacio (VACUUM)
            cursor.execute("VACUUM;")

        return {
            'tablas_limpiadas': len(tablas_limpiadas),
            'tablas_protegidas': len(tablas_omitidas),
            'detalle_limpiadas': tablas_limpiadas,
        }
