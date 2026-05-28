from rest_framework import serializers

class CrearVentaSerializer(serializers.Serializer):
    """
    Serializer para validación de entrada al crear una venta.
    No contiene lógica de negocio, solo validación de tipos y campos requeridos.
    """
    tipo_venta = serializers.ChoiceField(
        choices=[('contado', 'Contado'), ('credito', 'Crédito')],
        required=True,
        error_messages={
            'required': 'El tipo de venta es obligatorio.',
            'invalid_choice': 'El tipo de venta debe ser "contado" o "credito".'
        }
    )
    cliente_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID del cliente (obligatorio si tipo_venta es credito)"
    )

    def validate(self, data):
        """
        Validación básica cruzada: si es crédito, debe traer cliente.
        Esta regla podría estar en VentaService, pero es sano filtrarla aquí a nivel HTTP.
        """
        tipo = data.get('tipo_venta')
        cliente_id = data.get('cliente_id')

        if tipo == 'credito' and not cliente_id:
            raise serializers.ValidationError({
                "cliente_id": "Se requiere especificar el cliente para las ventas a crédito."
            })
            
        return data


class AgregarProductoSerializer(serializers.Serializer):
    """
    Serializer para agregar una variante de producto a una venta.
    """
    variante_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            'required': 'El ID de la variante es obligatorio.'
        }
    )
    cantidad = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            'required': 'La cantidad es obligatoria.',
            'min_value': 'La cantidad debe ser mayor a 0.'
        }
    )


class FinalizarVentaSerializer(serializers.Serializer):
    """
    Serializer para finalizar una venta.
    Campos opcionales permiten el flujo de autorización administrativa
    para ventas a crédito que exceden el límite del cliente.
    """
    force_credit_override = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Si True, omite la validación de límite de crédito (requiere authorized_by)."
    )
    authorized_by = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="ID del usuario admin que autoriza el excedente de crédito."
    )

    def validate(self, data):
        """Si force_credit_override es True, authorized_by es obligatorio."""
        if data.get('force_credit_override') and not data.get('authorized_by'):
            raise serializers.ValidationError({
                "authorized_by": "Se requiere el ID del admin autorizador cuando force_credit_override es True."
            })
        return data

