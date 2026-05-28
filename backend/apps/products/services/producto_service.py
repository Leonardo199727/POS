from __future__ import annotations
from django.db import IntegrityError
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

from apps.inventory.models import Inventario
from apps.products.models import (
    Producto,
    PrecioProducto,
    VarianteProducto,
)

if TYPE_CHECKING:
    from apps.accounts.models import User


class ProductoService:
    """
    Servicio de dominio para operaciones con Producto.
    Toda la lógica de negocio reside aquí, no en los modelos.
    """

    @staticmethod
    @transaction.atomic
    def crear_producto_completo(
        *,
        nombre: str,
        codigo_interno: str,
        precio_contado: Decimal,
        usuario: User,
        descripcion: str = '',
        tipo_producto_id: int | None = None,
        categoria_id: int | None = None,
        marca_id: int | None = None,
        precio_compra: Decimal | None = None,
        precio_credito: Decimal | None = None,
        porcentaje_ganancia: Decimal | None = None,
    ) -> Producto:
        """
        Crea un producto completo con:
        1. Producto
        2. Variante Default (nombre="Default", es_default=True)
        3. Inventario con stock 0
        4. PrecioProducto vigente

        Todo dentro de una transacción atómica.

        Args:
            nombre: Nombre del producto.
            codigo_interno: Código interno único.
            precio_contado: Precio de venta de contado (obligatorio).
            usuario: Usuario que realiza la operación.
            descripcion: Descripción del producto (opcional).
            tipo_producto_id: FK a TipoProducto (opcional).
            categoria_id: FK a Categoria (opcional).
            marca_id: FK a Marca (opcional).
            precio_compra: Precio de compra (opcional, solo admin).
            precio_credito: Precio de venta a crédito (opcional).
            porcentaje_ganancia: Porcentaje de ganancia (opcional).

        Returns:
            Producto creado con su variante, inventario y precio.

        Raises:
            django.db.IntegrityError: Si el codigo_interno ya existe.
        """

        # 1. Crear Producto
        producto = Producto.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            codigo_interno=codigo_interno,
            tipo_producto_id=tipo_producto_id,
            categoria_id=categoria_id,
            marca_id=marca_id,
        )

        # 2. Crear Variante Default
        variante = VarianteProducto.objects.create(
            producto=producto,
            nombre='Default',
            es_default=True,
        )

        # 3. Crear Inventario con stock 0
        Inventario.objects.create(
            variante=variante,
            stock_actual=0,
            stock_minimo=0,
        )

        # 4. Crear PrecioProducto vigente
        PrecioProducto.objects.create(
            variante=variante,
            precio_compra=precio_compra,
            precio_contado=precio_contado,
            precio_credito=precio_credito,
            porcentaje_ganancia=porcentaje_ganancia,
            vigente=True,
            usuario=usuario,
            motivo_cambio='Precio inicial',
        )

        return producto
