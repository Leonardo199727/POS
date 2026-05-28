from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.db.models import (
    F,
    Sum,
    DecimalField,
)
from django.db.models.functions import Coalesce

from apps.inventory.models import Inventario
from apps.products.models import PrecioProducto, VarianteProducto
from apps.sales.models import DetalleVenta, Venta
from apps.reports.dto import (
    BajoStockDTO,
    SinStockDTO,
    RotacionProductoDTO,
    UtilidadProductoDTO,
)

_ZERO = Decimal('0.00')
_Q2 = Decimal('0.01')


class InventoryReportService:
    """
    Servicio de reportes de inventario — lectura pura.

    Reglas:
    - Sin escrituras.
    - Sin transaction.atomic.
    - Retorna DTOs.
    - Decimal quantizado a 0.01.
    - Usa Inventario y DetalleVenta como fuentes de verdad.
    - Evita N+1 usando queries en batch.
    """

    # ------------------------------------------------------------------
    # 1. Productos bajo stock
    # ------------------------------------------------------------------

    @staticmethod
    def productos_bajo_stock() -> list[BajoStockDTO]:
        """
        Retorna productos donde stock_actual <= stock_minimo y stock_actual > 0.
        """
        qs = (
            Inventario.objects
            .select_related('variante', 'variante__producto')
            .filter(stock_actual__lte=F('stock_minimo'), stock_actual__gt=0)
        )

        resultado = []
        for inv in qs:
            diferencia = inv.stock_minimo - inv.stock_actual
            # Construir nombre completo: Producto + (Variante si aplica)
            nombre = str(inv.variante)

            resultado.append(BajoStockDTO(
                producto_id=inv.variante.producto_id,
                nombre=nombre,
                stock_actual=inv.stock_actual,
                stock_minimo=inv.stock_minimo,
                diferencia=diferencia,
            ))
        return resultado

    # ------------------------------------------------------------------
    # 2. Productos sin stock
    # ------------------------------------------------------------------

    @staticmethod
    def productos_sin_stock() -> list[SinStockDTO]:
        """
        Retorna productos con stock_actual == 0.
        """
        qs = (
            Inventario.objects
            .select_related('variante', 'variante__producto')
            .filter(stock_actual=0)
        )

        resultado = []
        for inv in qs:
            nombre = str(inv.variante)
            resultado.append(SinStockDTO(
                producto_id=inv.variante.producto_id,
                nombre=nombre,
                stock_actual=inv.stock_actual,
            ))
        return resultado

    # ------------------------------------------------------------------
    # 3. Rotación de inventario
    # ------------------------------------------------------------------

    @staticmethod
    def rotacion_inventario(
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> list[RotacionProductoDTO]:
        """
        Calcula rotación = unidades_vendidas / stock_actual.
        Solo incluye productos con ventas en el periodo.
        """
        # 1. Obtener unidades vendidas por variante en el rango (solo ventas válidas)
        ventas_agg = (
            DetalleVenta.objects
            .filter(
                venta__created_at__range=(fecha_inicio, fecha_fin),
                venta__estado__in=[
                    Venta.Estado.COMPLETADA,
                    Venta.Estado.PARCIAL,
                    Venta.Estado.LIQUIDADA
                ]
            )
            .values('variante_id', 'variante__producto__nombre', 'variante__nombre')
            .annotate(total_unidades=Sum('cantidad'))
            .filter(total_unidades__gt=0)
        )

        if not ventas_agg:
            return []

        # 2. Obtener stocks actuales de esas variantes (Batch Query)
        variantes_ids = [v['variante_id'] for v in ventas_agg]
        inventarios = {
            inv.variante_id: inv.stock_actual
            for inv in Inventario.objects.filter(variante_id__in=variantes_ids)
        }

        # 3. Calcular rotación en memoria
        resultado = []
        for item in ventas_agg:
            vid = item['variante_id']
            unidades = item['total_unidades']
            stock = inventarios.get(vid, 0)
            
            # Nombre compuesto si variante tiene nombre específico
            prod_nom = item['variante__producto__nombre']
            var_nom = item['variante__nombre']
            nombre = f"{prod_nom} - {var_nom}" if var_nom != 'Única' else prod_nom

            # Evitar división por cero
            if stock > 0:
                rotacion = Decimal(unidades) / Decimal(stock)
            else:
                rotacion = Decimal('0.00')

            resultado.append(RotacionProductoDTO(
                producto_id=vid, # Usamos ID de variante como referencia única
                nombre=nombre,
                unidades_vendidas=unidades,
                stock_actual=stock,
                rotacion=rotacion.quantize(_Q2),
            ))

        # Opcional: ordenar por rotación descendente
        resultado.sort(key=lambda x: x.rotacion, reverse=True)
        return resultado

    # ------------------------------------------------------------------
    # 4. Utilidad por producto
    # ------------------------------------------------------------------

    @staticmethod
    def utilidad_por_producto(
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> list[UtilidadProductoDTO]:
        """
        Calcula utilidad bruta = Ingresos (subtotal) - Costo (cantidad * precio_compra_vigente).
        """
        # 1. Agrupar ventas por variante
        ventas_agg = (
            DetalleVenta.objects
            .filter(
                venta__created_at__range=(fecha_inicio, fecha_fin),
                venta__estado__in=[
                    Venta.Estado.COMPLETADA,
                    Venta.Estado.PARCIAL,
                    Venta.Estado.LIQUIDADA
                ]
            )
            .values('variante_id', 'variante__producto__nombre', 'variante__nombre')
            .annotate(
                total_ingresos=Sum('subtotal'),
                total_unidades=Sum('cantidad')
            )
        )

        if not ventas_agg:
            return []

        # 2. Obtener precios de compra vigentes (Batch Query)
        variantes_ids = [v['variante_id'] for v in ventas_agg]
        # Si hay múltiples precios vigentes (error data), tomamos el primero/último o promedio?
        # Asumimos integridad: un solo vigente. Si hay varios, distinct('variante') en Postgres o iterar.
        # Usaremos iteración segura.
        precios_qs = PrecioProducto.objects.filter(
            variante_id__in=variantes_ids, 
            vigente=True
        ).values('variante_id', 'precio_compra')
        
        precios_compra = {p['variante_id']: p['precio_compra'] for p in precios_qs}

        # 3. Construir DTOs
        resultado = []
        for item in ventas_agg:
            vid = item['variante_id']
            ingresos = Decimal(str(item['total_ingresos']))
            unidades = item['total_unidades']
            
            # Costo
            precio_compra = precios_compra.get(vid)
            if precio_compra:
                costo_total = ingresos - (ingresos - (Decimal(precio_compra) * unidades)) # Error logic here?
                # No, costo_total = precio_compra * unidades
                costo_total = Decimal(precio_compra) * unidades
            else:
                costo_total = _ZERO

            utilidad = ingresos - costo_total

            # Margen %
            if ingresos > 0:
                margen = (utilidad / ingresos) * 100
            else:
                margen = _ZERO

            prod_nom = item['variante__producto__nombre']
            var_nom = item['variante__nombre']
            nombre = f"{prod_nom} - {var_nom}" if var_nom != 'Única' else prod_nom

            resultado.append(UtilidadProductoDTO(
                producto_id=vid,
                nombre=nombre,
                unidades_vendidas=unidades,
                total_ingresos=ingresos.quantize(_Q2),
                costo_total=costo_total.quantize(_Q2),
                utilidad_total=utilidad.quantize(_Q2),
                margen_porcentual=margen.quantize(_Q2),
            ))

        resultado.sort(key=lambda x: x.utilidad_total, reverse=True)
        return resultado
