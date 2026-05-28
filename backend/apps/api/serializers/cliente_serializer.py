from rest_framework import serializers
from apps.customers.models import Cliente


class ClienteListSerializer(serializers.ModelSerializer):
    """
    Serializer de solo lectura para listar clientes en la tabla principal.
    Expone todos los campos necesarios para la vista de Gestión de Clientes.
    """

    class Meta:
        model = Cliente
        fields = [
            'id',
            'nombre',
            'telefono',
            'email',
            'direccion',
            'tipo_cliente',
            'limite_credito',
            'saldo_actual',
            'activo',
            'notas',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ClienteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear un nuevo cliente.
    POST /api/clientes/

    Campos requeridos: nombre.
    Campos opcionales: telefono, email, direccion, tipo_cliente, limite_credito.
    Campos de solo lectura (autogenerados): id, saldo_actual, activo, created_at, updated_at.
    """
    email = serializers.CharField(required=False, allow_blank=True, default='')
    telefono = serializers.CharField(required=False, allow_blank=True, default='')
    direccion = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = Cliente
        fields = [
            'id',
            'nombre',
            'telefono',
            'email',
            'direccion',
            'tipo_cliente',
            'limite_credito',
        ]
        read_only_fields = ['id']

    def validate_nombre(self, value: str) -> str:
        """Validar que el nombre no esté vacío después de limpiar espacios."""
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('El nombre del cliente es obligatorio.')
        return cleaned

    def validate_limite_credito(self, value):
        """Validar que el límite de crédito no sea negativo."""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                'El límite de crédito no puede ser negativo.'
            )
        return value


class ClienteUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar un cliente existente.
    PATCH /api/clientes/<id>/

    Todos los campos son opcionales (partial update por defecto).
    """
    email = serializers.CharField(required=False, allow_blank=True)
    telefono = serializers.CharField(required=False, allow_blank=True)
    direccion = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Cliente
        fields = [
            'nombre',
            'telefono',
            'email',
            'direccion',
            'tipo_cliente',
            'limite_credito',
        ]

    def validate_nombre(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('El nombre del cliente es obligatorio.')
        return cleaned

    def validate_limite_credito(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                'El límite de crédito no puede ser negativo.'
            )
        return value

