from decimal import Decimal
from rest_framework import serializers

class MetodoPagoSerializer(serializers.Serializer):
    """
    Estructura individual para un método de pago.
    """
    metodo = serializers.ChoiceField(
        choices=['EFECTIVO', 'TARJETA', 'TRANSFERENCIA'],
        error_messages={
            'invalid_choice': 'El método debe ser EFECTIVO, TARJETA o TRANSFERENCIA.',
            'required': 'El método de pago es obligatorio.'
        }
    )
    monto = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        error_messages={
            'min_value': 'El monto debe ser mayor a 0.',
            'required': 'El monto es obligatorio.'
        }
    )
    con_intereses = serializers.BooleanField(default=False)
    porcentaje_interes = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=0,
        max_value=100
    )

class PagoCreditoSerializer(serializers.Serializer):
    """
    Payload para registrar un abono a crédito.
    """
    cliente_id = serializers.IntegerField(
        required=True,
        error_messages={'required': 'El cliente_id es obligatorio para pagos a crédito.'}
    )
    venta_id = serializers.IntegerField(
        required=False,
        allow_null=True
    )
    metodos_pago = MetodoPagoSerializer(
        many=True,
        allow_empty=False,
        error_messages={'empty': 'Debe especificar al menos un método de pago.'}
    )

class PagoContadoSerializer(serializers.Serializer):
    """
    Payload para pagar una venta de contado completo.
    """
    venta_id = serializers.IntegerField(
        required=True,
        error_messages={'required': 'El venta_id es obligatorio para pagos de contado.'}
    )
    metodos_pago = MetodoPagoSerializer(
        many=True,
        allow_empty=False,
        error_messages={'empty': 'Debe especificar al menos un método de pago.'}
    )

class PagoMixtoSerializer(serializers.Serializer):
    """
    Payload para pagos fraccionados o distribuidos entre varios métodos.
    """
    venta_id = serializers.IntegerField(
        required=True,
        error_messages={'required': 'El venta_id es obligatorio para pagos mixtos.'}
    )
    metodos_pago = MetodoPagoSerializer(
        many=True,
        allow_empty=False,
        error_messages={'empty': 'Debe especificar al menos un método de pago.'}
    )

class PagoInicialSerializer(serializers.Serializer):
    """
    Payload para registrar el anticipo de una venta a crédito.
    """
    venta_id = serializers.IntegerField(
        required=True,
        error_messages={'required': 'El venta_id es obligatorio para el pago inicial.'}
    )
    metodos_pago = MetodoPagoSerializer(
        many=True,
        allow_empty=False,
        error_messages={'empty': 'Debe especificar al menos un método de pago.'}
    )
