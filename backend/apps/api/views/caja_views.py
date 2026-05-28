from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.api.permissions import IsAdminRole, IsAdminOrVendedor
from rest_framework.permissions import IsAuthenticated

from apps.cash.services.caja_service import CajaService


class EstadoCajaAPIView(APIView):
    """
    GET /api/caja/estado/
    Retorna si el usuario autenticado tiene una caja abierta.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def get(self, request, *args, **kwargs):
        caja = CajaService.obtener_caja_abierta(request.user)
        if caja:
            return Response({
                "success": True,
                "caja_abierta": True,
                "data": {"id": caja.id, "estado": caja.estado, "monto_inicial": str(caja.monto_inicial)}
            }, status=status.HTTP_200_OK)
        return Response({
            "success": True,
            "caja_abierta": False,
        }, status=status.HTTP_200_OK)


class AbrirCajaAPIView(APIView):
    """
    POST /api/caja/abrir/
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, *args, **kwargs):
        monto_inicial = request.data.get('monto_inicial', 0.0)
        caja = CajaService.abrir_caja(
            usuario=request.user,
            monto_inicial=monto_inicial
        )
        return Response({
            "success": True,
            "data": {"id": caja.id, "estado": caja.estado}
        }, status=status.HTTP_201_CREATED)


class IngresoRetiroCajaAPIView(APIView):
    """
    POST /api/caja/movimiento/
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, *args, **kwargs):
        tipo = request.data.get('tipo', 'ENTRADA')
        monto = request.data.get('monto', 0.0)
        concepto = request.data.get('concepto', '')
        
        # Validar tipo de movimiento antes de pasarlo al service o capturar error

        if tipo == 'ENTRADA':
            movimiento = CajaService.registrar_ingreso(
                usuario=request.user,
                monto=monto,
                concepto=concepto
            )
        else:
            movimiento = CajaService.registrar_retiro(
                usuario=request.user,
                monto=monto,
                concepto=concepto
            )

        return Response({
            "success": True,
            "data": {"id": movimiento.id, "tipo": movimiento.tipo, "monto": str(movimiento.monto)}
        }, status=status.HTTP_201_CREATED)


class CerrarCajaAPIView(APIView):
    """
    POST /api/caja/cerrar/
    Solo accesible por ADMIN.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, *args, **kwargs):
        total_efectivo_contado = request.data.get('monto_final_real', 0.0)
        usuario_caja_id = request.data.get('usuario_id', request.user.id) # Puede cerrar de otros si es admin?
        
        # El service ya valida roles internos pero aseguramos la capa con la clase de permiso
        caja = CajaService.cerrar_caja(
            usuario=request.user, # Aquí la firma en Service asume el usuario actual como el evaluado en Role Matrix
            total_efectivo_contado=total_efectivo_contado
        )
        
        return Response({
            "success": True,
            "data": {"id": caja.id, "estado": caja.estado, "diferencia": str(caja.diferencia_efectivo)}
        }, status=status.HTTP_200_OK)
