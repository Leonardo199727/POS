from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class SalesSummaryDTO:
    """Resumen de ventas en un rango de fechas."""

    total_sales: Decimal
    total_contado: Decimal
    total_credito: Decimal
    total_ventas: int
    ticket_promedio: Decimal

    def to_dict(self) -> dict:
        return {
            'total_sales': self.total_sales,
            'total_contado': self.total_contado,
            'total_credito': self.total_credito,
            'total_ventas': self.total_ventas,
            'ticket_promedio': self.ticket_promedio,
        }


@dataclass
class TopProductDTO:
    """Producto más vendido dentro de un rango de fechas."""

    producto_id: int
    nombre: str
    cantidad_vendida: int
    total_generado: Decimal
    utilidad_generada: Decimal

    def to_dict(self) -> dict:
        return {
            'producto_id': self.producto_id,
            'nombre': self.nombre,
            'cantidad_vendida': self.cantidad_vendida,
            'total_generado': self.total_generado,
            'utilidad_generada': self.utilidad_generada,
        }


# ------------------------------------------------------------------
# Financial Reports DTOs
# ------------------------------------------------------------------

@dataclass
class GrossProfitDTO:
    """Utilidad bruta de un periodo."""

    total_ventas: Decimal
    costo_total: Decimal
    utilidad_bruta: Decimal
    margen_porcentual: Decimal

    def to_dict(self) -> dict:
        return {
            'total_ventas': self.total_ventas,
            'costo_total': self.costo_total,
            'utilidad_bruta': self.utilidad_bruta,
            'margen_porcentual': self.margen_porcentual,
        }


@dataclass
class PaymentMethodSummaryDTO:
    """Ingresos cobrados agrupados por método de pago."""

    efectivo: Decimal
    tarjeta: Decimal
    transferencia: Decimal
    total_ingresos: Decimal

    def to_dict(self) -> dict:
        return {
            'efectivo': self.efectivo,
            'tarjeta': self.tarjeta,
            'transferencia': self.transferencia,
            'total_ingresos': self.total_ingresos,
        }


@dataclass
class CashFlowDTO:
    """Flujo de efectivo real desde MovimientoCaja."""

    efectivo_neto: Decimal
    tarjeta_neto: Decimal
    transferencia_neto: Decimal
    flujo_total: Decimal

    def to_dict(self) -> dict:
        return {
            'efectivo_neto': self.efectivo_neto,
            'tarjeta_neto': self.tarjeta_neto,
            'transferencia_neto': self.transferencia_neto,
            'flujo_total': self.flujo_total,
        }


# ------------------------------------------------------------------
# Credit Reports DTOs
# ------------------------------------------------------------------

@dataclass
class CarteraGeneralDTO:
    """Estado general de la cartera de crédito."""

    total_credito_colocado: Decimal
    total_recuperado: Decimal
    saldo_cartera: Decimal
    total_clientes_con_deuda: int
    total_movimientos: int

    def to_dict(self) -> dict:
        return {
            'total_credito_colocado': self.total_credito_colocado,
            'total_recuperado': self.total_recuperado,
            'saldo_cartera': self.saldo_cartera,
            'total_clientes_con_deuda': self.total_clientes_con_deuda,
            'total_movimientos': self.total_movimientos,
        }


@dataclass
class MovimientoEstadoCuentaDTO:
    """Detalle de movimiento para estado de cuenta (Cliente final)."""

    fecha: str  # DD/MM/YYYY
    movimiento: str  # Compra / Pago / Ajuste
    detalle: str  # Lista de productos o descripción
    metodo: str  # Efectivo / Tarjeta / Transferencia / ""
    monto: Decimal
    saldo: Decimal
    referencia: str

    def to_dict(self) -> dict:
        return {
            'fecha': self.fecha,
            'movimiento': self.movimiento,
            'detalle': self.detalle,
            'metodo': self.metodo,
            'monto': self.monto,
            'saldo': self.saldo,
            'referencia': self.referencia,
        }


@dataclass
class EstadoCuentaClienteDTO:
    """Estado de cuenta profesional para cliente."""

    cliente_id: int
    nombre_cliente: str
    telefono: str
    direccion: str
    saldo_actual: Decimal
    fecha_generacion: str
    movimientos: list[MovimientoEstadoCuentaDTO]

    def to_dict(self) -> dict:
        return {
            'cliente_id': self.cliente_id,
            'nombre_cliente': self.nombre_cliente,
            'telefono': self.telefono,
            'direccion': self.direccion,
            'saldo_actual': self.saldo_actual,
            'fecha_generacion': self.fecha_generacion,
            'movimientos': [m.to_dict() for m in self.movimientos],
        }


@dataclass
class ClienteSaldoDTO:
    """Cliente con saldo pendiente."""

    cliente_id: int
    nombre: str
    saldo_actual: Decimal
    limite_credito: Decimal

    def to_dict(self) -> dict:
        return {
            'cliente_id': self.cliente_id,
            'nombre': self.nombre,
            'saldo_actual': self.saldo_actual,
            'limite_credito': self.limite_credito,
        }


@dataclass
class TopClienteCreditoDTO:
    """Top cliente por crédito utilizado."""

    cliente_id: int
    nombre: str
    total_credito: Decimal
    cantidad_cargos: int

    def to_dict(self) -> dict:
        return {
            'cliente_id': self.cliente_id,
            'nombre': self.nombre,
            'total_credito': self.total_credito,
            'cantidad_cargos': self.cantidad_cargos,
        }


# ------------------------------------------------------------------
# Cash Reports DTOs
# ------------------------------------------------------------------

@dataclass
class CajaResumenDTO:
    """Resumen completo de una caja (arqueo)."""

    caja_id: int
    usuario_apertura: str
    usuario_cierre: str | None
    estado: str
    monto_inicial: Decimal
    total_entradas_efectivo: Decimal
    total_entradas_tarjeta: Decimal
    total_entradas_transferencia: Decimal
    total_salidas: Decimal
    flujo_neto: Decimal
    # Esperados
    total_efectivo_esperado: Decimal | None
    total_tarjeta_esperado: Decimal | None
    total_transferencia_esperado: Decimal | None
    # Declarados
    total_efectivo_declarado: Decimal | None
    total_tarjeta_declarado: Decimal | None
    total_transferencia_declarado: Decimal | None
    # Diferencias
    diferencia_efectivo: Decimal | None
    diferencia_tarjeta: Decimal | None
    diferencia_transferencia: Decimal | None

    def to_dict(self) -> dict:
        return {
            'caja_id': self.caja_id,
            'usuario_apertura': self.usuario_apertura,
            'usuario_cierre': self.usuario_cierre,
            'estado': self.estado,
            'monto_inicial': self.monto_inicial,
            'total_entradas_efectivo': self.total_entradas_efectivo,
            'total_entradas_tarjeta': self.total_entradas_tarjeta,
            'total_entradas_transferencia': self.total_entradas_transferencia,
            'total_salidas': self.total_salidas,
            'flujo_neto': self.flujo_neto,
            'total_efectivo_esperado': self.total_efectivo_esperado,
            'total_tarjeta_esperado': self.total_tarjeta_esperado,
            'total_transferencia_esperado': self.total_transferencia_esperado,
            'total_efectivo_declarado': self.total_efectivo_declarado,
            'total_tarjeta_declarado': self.total_tarjeta_declarado,
            'total_transferencia_declarado': self.total_transferencia_declarado,
            'diferencia_efectivo': self.diferencia_efectivo,
            'diferencia_tarjeta': self.diferencia_tarjeta,
            'diferencia_transferencia': self.diferencia_transferencia,
        }


@dataclass
class CorteCajaDTO:
    """Totales acumulados de cortes de caja en un periodo."""

    total_cajas: int
    total_efectivo_esperado: Decimal
    total_efectivo_contado: Decimal
    diferencia_efectivo: Decimal
    diferencia_tarjeta: Decimal
    diferencia_transferencia: Decimal

    def to_dict(self) -> dict:
        return {
            'total_cajas': self.total_cajas,
            'total_efectivo_esperado': self.total_efectivo_esperado,
            'total_efectivo_contado': self.total_efectivo_contado,
            'diferencia_efectivo': self.diferencia_efectivo,
            'diferencia_tarjeta': self.diferencia_tarjeta,
            'diferencia_transferencia': self.diferencia_transferencia,
        }


@dataclass
class DiferenciaAcumuladaDTO:
    """Análisis histórico de diferencias (sobrantes/faltantes)."""

    total_diferencia_efectivo: Decimal
    total_diferencia_tarjeta: Decimal
    total_diferencia_transferencia: Decimal
    cantidad_cajas_con_diferencia: int
    promedio_diferencia_efectivo: Decimal

    def to_dict(self) -> dict:
        return {
            'total_diferencia_efectivo': self.total_diferencia_efectivo,
            'total_diferencia_tarjeta': self.total_diferencia_tarjeta,
            'total_diferencia_transferencia': self.total_diferencia_transferencia,
            'cantidad_cajas_con_diferencia': self.cantidad_cajas_con_diferencia,
            'promedio_diferencia_efectivo': self.promedio_diferencia_efectivo,
        }


@dataclass
class UsuarioCajaDTO:
    """ Rendimiento de usuario en caja."""

    usuario_id: int
    nombre: str
    total_entradas: Decimal
    total_salidas: Decimal
    flujo_neto: Decimal
    total_movimientos: int

    def to_dict(self) -> dict:
        return {
            'usuario_id': self.usuario_id,
            'nombre': self.nombre,
            'total_entradas': self.total_entradas,
            'total_salidas': self.total_salidas,
            'flujo_neto': self.flujo_neto,
            'total_movimientos': self.total_movimientos,
        }


# ------------------------------------------------------------------
# Inventory Reports DTOs
# ------------------------------------------------------------------

@dataclass
class BajoStockDTO:
    """Producto con stock por debajo del mínimo."""

    producto_id: int
    nombre: str
    stock_actual: int
    stock_minimo: int
    diferencia: int  # stock_minimo - stock_actual

    def to_dict(self) -> dict:
        return {
            'producto_id': self.producto_id,
            'nombre': self.nombre,
            'stock_actual': self.stock_actual,
            'stock_minimo': self.stock_minimo,
            'diferencia': self.diferencia,
        }


@dataclass
class SinStockDTO:
    """Producto sin existencia (stock = 0)."""

    producto_id: int
    nombre: str
    stock_actual: int

    def to_dict(self) -> dict:
        return {
            'producto_id': self.producto_id,
            'nombre': self.nombre,
            'stock_actual': self.stock_actual,
        }


@dataclass
class RotacionProductoDTO:
    """Análisis de rotación de inventario."""

    producto_id: int
    nombre: str
    unidades_vendidas: int
    stock_actual: int
    rotacion: Decimal

    def to_dict(self) -> dict:
        return {
            'producto_id': self.producto_id,
            'nombre': self.nombre,
            'unidades_vendidas': self.unidades_vendidas,
            'stock_actual': self.stock_actual,
            'rotacion': self.rotacion,
        }


@dataclass
class UtilidadProductoDTO:
    """Análisis de rentabilidad por producto."""

    producto_id: int
    nombre: str
    unidades_vendidas: int
    total_ingresos: Decimal
    costo_total: Decimal
    utilidad_total: Decimal
    margen_porcentual: Decimal

    def to_dict(self) -> dict:
        return {
            'producto_id': self.producto_id,
            'nombre': self.nombre,
            'unidades_vendidas': self.unidades_vendidas,
            'total_ingresos': self.total_ingresos,
            'costo_total': self.costo_total,
            'utilidad_total': self.utilidad_total,
            'margen_porcentual': self.margen_porcentual,
        }
