from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed

class LoginAPIView(APIView):
    """
    POST /api/login/
    Autentica al usuario usando username y password,
    crea/recupera su Token y retorna el contrato JSON.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        # 1. Utilizar manejador de auth Django
        user = authenticate(username=username, password=password)
        
        # 2. Manejo de Credenciales Inválidas
        if not user:
            # Nuestro global custom exception handler procesará el .detail e integrará 'code' al JSON general
            exc = AuthenticationFailed("Credenciales inválidas o cuenta desactivada")
            # Forzamos un código para que el front lo interprete y no tire 500
            exc.default_code = "INVALID_CREDENTIALS" 
            raise exc

        # 3. Restricción adicional explícita (pese a que authenticate por def ignora inactivos)
        if not user.is_active:
            exc = AuthenticationFailed("El usuario está inactivo.")
            exc.default_code = "INACTIVE_USER"
            raise exc

        # 4. Generación / Recuperación de sesión persistente con Token
        token, created = Token.objects.get_or_create(user=user)

        # 5. Respuesta JSON Consistente (Contrato: success, data, meta)
        user_data = {
            "id": user.id,
            "username": user.username,
            "rol": user.rol.nombre if user.rol else None
        }

        return Response({
            "success": True,
            "data": {
                "token": token.key,
                "user": user_data
            }
        }, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    """
    POST /api/logout/
    Invalida el token del auth logueado.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # request.user es la instancia y request.auth es la instancia literal de authtoken.models.Token inyectada por TokenAuthentication
        if getattr(request, 'auth', None):
            request.auth.delete()
            
        return Response({
            "success": True,
            "data": "Sesión cerrada exitosamente"
        }, status=status.HTTP_200_OK)
