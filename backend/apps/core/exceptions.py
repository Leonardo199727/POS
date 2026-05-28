import logging
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotAuthenticated, AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


class BusinessLogicError(Exception):
    """
    Excepción base para errores de lógica de negocio en Services.
    Permite definir código, mensaje y status_code HTTP estructurados.
    """
    def __init__(self, message: str, code: str = "BUSINESS_ERROR", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class PermissionDeniedError(BusinessLogicError):
    """Lanzado cuando un usuario no tiene los permisos suficientes en la matriz de roles."""
    def __init__(self, message: str = "No tienes permisos para realizar esta acción."):
        super().__init__(
            message=message, 
            code="PERMISSION_DENIED", 
            status_code=status.HTTP_403_FORBIDDEN
        )




class CreditLimitError(BusinessLogicError):
    """Lanzado cuando un cliente excede su límite de crédito disponible."""
    def __init__(self, message: str, code: str = "CREDIT_LIMIT_EXCEEDED", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class StockError(BusinessLogicError):
    """Lanzado cuando no hay inventario suficiente para un producto."""
    def __init__(self, message: str, code: str = "INSUFFICIENT_STOCK", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class VentaNoEnProcesoError(BusinessLogicError):
    """Lanzado cuando se intenta agregar productos o finalizar una venta que ya cerró o se canceló."""
    def __init__(self, message: str, code: str = "SALE_NOT_IN_PROCESS", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class CajaCerradaError(BusinessLogicError):
    """Lanzado cuando se requiere caja abierta pero el cajero tiene la caja cerrada."""
    def __init__(self, message: str, code: str = "CASH_REGISTER_CLOSED", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class NotFoundError(BusinessLogicError):
    """Lanzado cuando la entidad del dominio solicitada no existe."""
    def __init__(self, message: str, code: str = "RESOURCE_NOT_FOUND", status_code: int = status.HTTP_404_NOT_FOUND):
        super().__init__(message, code, status_code)


class PaymentExceedsBalanceError(BusinessLogicError):
    """Lanzado cuando el monto del pago excede el saldo de la cuenta o venta."""
    def __init__(self, message: str, code: str = "PAYMENT_EXCEEDS_BALANCE", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class SaleNotPayableError(BusinessLogicError):
    """Lanzado cuando la venta no está en un estado válido para recibir pagos."""
    def __init__(self, message: str, code: str = "SALE_NOT_PAYABLE", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class PaymentAlreadyProcessedError(BusinessLogicError):
    """Lanzado cuando un pago ya fue procesado o la venta ya está liquidada."""
    def __init__(self, message: str, code: str = "PAYMENT_ALREADY_PROCESSED", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class InvalidPaymentMethodError(BusinessLogicError):
    """Lanzado cuando el método de pago especificado no existe o es inválido."""
    def __init__(self, message: str, code: str = "INVALID_PAYMENT_METHOD", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class InvalidPaymentDataError(BusinessLogicError):
    """Lanzado cuando los datos del pago (monto, porcentajes) son inválidos."""
    def __init__(self, message: str, code: str = "INVALID_PAYMENT_DATA", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class ClientRequiredError(BusinessLogicError):
    """Lanzado cuando una operación (ej. pago a crédito) requiere un cliente obligatoriamente."""
    def __init__(self, message: str, code: str = "CLIENT_REQUIRED", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


class SaleOwnershipError(BusinessLogicError):
    """Lanzado cuando se intenta aplicar un pago a una venta que no pertenece al cliente especificado."""
    def __init__(self, message: str, code: str = "SALE_OWNERSHIP_MISMATCH", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, code, status_code)


def _format_error_response(code: str, message: str, status_code: int) -> Response:
    """Helper interno para construir la estructura uniforme de respuesta"""
    data = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    return Response(data, status=status_code)


def custom_exception_handler(exc, context):
    """
    Manejador global para formatear excepciones bajo un esquema uniforme.
    
    Esquema JSON:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Mensaje legible del error"
        }
    }
    """
    # 1) Primero delegamos a DRF para que nos dé su pre-formateo estándar.
    response = exception_handler(exc, context)

    # 2) Manejo específico de excepciones nativas de Django (404, 403)
    # DRF maneja a veces el Http404 y PermissionDenied llamando a su base. 
    # Por seguridad, si isinstance entra primero en los DRF, interceptamos su output base y reformateamos.
    
    # 3) Manejar excepciones de DRF
    if response is not None:
        if isinstance(exc, Http404):
            return _format_error_response("RESOURCE_NOT_FOUND", "El recurso solicitado no existe.", status.HTTP_404_NOT_FOUND)
            
        if isinstance(exc, PermissionDenied):
            return _format_error_response("PERMISSION_DENIED", "No tienes permisos para realizar esta acción.", status.HTTP_403_FORBIDDEN)
            
        if isinstance(exc, NotAuthenticated) or isinstance(exc, AuthenticationFailed):
            # En DRF si no mandas header Auth a veces lanza 403, forzamos 401 según nuestro contrato JSON unit tests
            code = getattr(exc, 'default_code', 'AUTHENTICATION_FAILED')
            msg = getattr(exc, 'detail', 'Credenciales inválidas o no proporcionadas.')
            return _format_error_response(code, str(msg), status.HTTP_401_UNAUTHORIZED)
            
        if isinstance(exc, ValidationError):
            # DRF ValidationError: extraemos detalle
            if isinstance(response.data, dict) and "detail" in response.data:
                error_message = response.data.get("detail")
            elif isinstance(response.data, dict):
                # Errores en diccionarios anidados: los aplastamos a str legibles
                error_message = response.data
            elif isinstance(response.data, list) and len(response.data) > 0:
                error_message = response.data[0]
            else:
                error_message = str(response.data)
                
            return _format_error_response("VALIDATION_ERROR", error_message, status.HTTP_400_BAD_REQUEST)
            
        # Para otras excepciones de DRF controladas, usamos error genérico de DRF
        return _format_error_response("API_ERROR", str(response.data.get('detail', 'Error en la solicitud.')), response.status_code)

    # 4) Excepciones nativas personalizadas de negocio
    if isinstance(exc, BusinessLogicError):
        return _format_error_response(exc.code, exc.message, exc.status_code)

    # Compatibilidad con legacy Services que arrojan ValueError crudo
    if isinstance(exc, ValueError):
        return _format_error_response("VALIDATION_ERROR", str(exc), status.HTTP_400_BAD_REQUEST)
        
    # Catching Django native Http404 that bypass DRF response builder sometimes
    if isinstance(exc, Http404):
        return _format_error_response("RESOURCE_NOT_FOUND", "El recurso solicitado no existe.", status.HTTP_404_NOT_FOUND)
        
    if isinstance(exc, PermissionDenied):
         return _format_error_response("PERMISSION_DENIED", "No tienes permisos para realizar esta acción.", status.HTTP_403_FORBIDDEN)

    # 5) Cualquier otro error interno 500
    # Log the full traceback locally for debugging, don't leak it to client
    logger.error("Error Interno del Servidor: %s", exc, exc_info=True)
    return _format_error_response("INTERNAL_SERVER_ERROR", "Error inesperado del lado del servidor.", status.HTTP_500_INTERNAL_SERVER_ERROR)
