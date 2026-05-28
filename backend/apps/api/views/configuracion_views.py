from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settings_app.services.configuracion_service import ConfiguracionService
from apps.api.permissions import IsAdminRole


class ConfiguracionNegocioAPIView(APIView):
    """
    GET  /api/configuracion/negocio/  → Obtiene la configuración actual.
    PUT  /api/configuracion/negocio/  → Actualiza la configuración (solo Admin).
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]

    def get(self, request):
        data = ConfiguracionService.obtener_configuracion()
        return Response({'success': True, 'data': data})

    def put(self, request):
        nombre_negocio = request.data.get('nombre_negocio')

        try:
            data = ConfiguracionService.actualizar_configuracion(
                nombre_negocio=nombre_negocio,
            )
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({'success': True, 'data': data})
