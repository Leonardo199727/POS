import os

from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import IsAdminRole
from apps.settings_app.services.backup_service import BackupService


class ExportarDBAPIView(APIView):
    """
    GET /api/configuracion/backup/exportar/
    
    Descarga una copia del archivo SQLite como respaldo.
    Solo accesible para administradores.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        try:
            backup_path = BackupService.exportar_db()
            response = FileResponse(
                open(str(backup_path), 'rb'),
                content_type='application/x-sqlite3',
            )
            response['Content-Disposition'] = (
                f'attachment; filename="{backup_path.name}"'
            )
            return response
        except FileNotFoundError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )


class ImportarDBAPIView(APIView):
    """
    POST /api/configuracion/backup/importar/
    
    Recibe un archivo .sqlite3 y reemplaza la base de datos actual.
    Se crea un respaldo automático antes de reemplazar.
    Solo accesible para administradores.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    parser_classes = [MultiPartParser]

    def post(self, request):
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response(
                {'detail': 'No se proporcionó ningún archivo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            BackupService.importar_db(archivo)
            return Response({
                'success': True,
                'message': (
                    'Base de datos importada exitosamente. '
                    'Reinicie la aplicación para aplicar los cambios.'
                ),
            })
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LimpiarDBAPIView(APIView):
    """
    POST /api/configuracion/backup/limpiar/
    
    Elimina todos los datos excepto usuarios, roles y configuración.
    Solo accesible para administradores.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        # Requiere confirmación explícita
        confirmacion = request.data.get('confirmar', False)
        if not confirmacion:
            return Response(
                {'detail': 'Debe enviar "confirmar": true para limpiar la base de datos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            resultado = BackupService.limpiar_db()
            return Response({
                'success': True,
                'message': 'Base de datos limpiada exitosamente.',
                'data': resultado,
            })
        except Exception as e:
            return Response(
                {'detail': f'Error al limpiar la base de datos: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
