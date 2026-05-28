from django.urls import path
from apps.api.views.auth_views import LoginAPIView, LogoutAPIView


from apps.api.views.venta_views import (
    AgregarProductoAPIView,
    CrearVentaAPIView,
    DetalleVentaAPIView,
    FinalizarVentaAPIView,
)

from apps.api.views.pago_views import (
    PagoContadoAPIView,
    PagoCreditoAPIView,
    PagoMixtoAPIView,
    PagoInicialAPIView,
)

from apps.api.views.caja_views import (
    AbrirCajaAPIView,
    IngresoRetiroCajaAPIView,
    CerrarCajaAPIView,
    EstadoCajaAPIView
)

from apps.api.views.reporte_views import (
    DashboardAPIView,
    EstadoCuentaClienteAPIView,
    ReportesFinancierosAPIView
)

from apps.api.views.producto_views import (
    ProductoListCreateAPIView,
    ProductoRetrieveUpdateDestroyAPIView,
    CategoriaListAPIView,
    MarcaListAPIView
)

from apps.api.views.cliente_views import (
    ClienteListAPIView,
    ClienteCreateAPIView,
    ClienteUpdateAPIView,
    ClienteAbonoAPIView,
    ClienteCargoAPIView,
    ClienteMovimientosAPIView,
)

from apps.api.views.inventario_views import (
    StockCriticoListAPIView,
    UpdateStockAPIView,
)

from apps.api.views.configuracion_views import ConfiguracionNegocioAPIView
from apps.api.views.backup_views import (
    ExportarDBAPIView,
    ImportarDBAPIView,
    LimpiarDBAPIView,
)

app_name = 'api'

urlpatterns = [
    # Rutas para el módulo de ventas
    path('ventas/', CrearVentaAPIView.as_view(), name='venta-crear'),
    path('ventas/<int:pk>/', DetalleVentaAPIView.as_view(), name='venta-detalle'),
    path('ventas/<int:pk>/agregar-producto/', AgregarProductoAPIView.as_view(), name='venta-agregar-producto'),
    path('ventas/<int:pk>/finalizar/', FinalizarVentaAPIView.as_view(), name='venta-finalizar'),

    # Rutas para el módulo de pagos
    path('pagos/contado/', PagoContadoAPIView.as_view(), name='pago-contado'),
    path('pagos/credito/', PagoCreditoAPIView.as_view(), name='pago-credito'),
    path('pagos/mixto/', PagoMixtoAPIView.as_view(), name='pago-mixto'),
    path('pagos/inicial/', PagoInicialAPIView.as_view(), name='pago-inicial'),

    # Rutas para el módulo de caja
    path('caja/estado/', EstadoCajaAPIView.as_view(), name='caja-estado'),
    path('caja/abrir/', AbrirCajaAPIView.as_view(), name='caja-abrir'),
    path('caja/movimiento/', IngresoRetiroCajaAPIView.as_view(), name='caja-movimiento'),
    path('caja/cerrar/', CerrarCajaAPIView.as_view(), name='caja-cerrar'),

    # Rutas para el módulo de reportes
    path('reportes/dashboard/', DashboardAPIView.as_view(), name='reportes-dashboard'),
    path('reportes/estado-cuenta/<int:cliente_id>/', EstadoCuentaClienteAPIView.as_view(), name='reportes-estado-cuenta'),
    path('reportes/financieros/', ReportesFinancierosAPIView.as_view(), name='reportes-financieros'),

    # Rutas para el módulo de productos
    path('productos/', ProductoListCreateAPIView.as_view(), name='producto-list-create'),
    path('productos/<int:pk>/', ProductoRetrieveUpdateDestroyAPIView.as_view(), name='producto-detail-update-destroy'),
    path('categorias/', CategoriaListAPIView.as_view(), name='categoria-list'),
    path('marcas/', MarcaListAPIView.as_view(), name='marca-list'),

    # Rutas para el módulo de clientes
    path('clientes/', ClienteListAPIView.as_view(), name='cliente-list'),
    path('clientes/crear/', ClienteCreateAPIView.as_view(), name='cliente-crear'),
    path('clientes/<int:pk>/', ClienteUpdateAPIView.as_view(), name='cliente-update'),
    path('clientes/<int:pk>/abono/', ClienteAbonoAPIView.as_view(), name='cliente-abono'),
    path('clientes/<int:pk>/cargo/', ClienteCargoAPIView.as_view(), name='cliente-cargo'),
    path('clientes/<int:pk>/movimientos/', ClienteMovimientosAPIView.as_view(), name='cliente-movimientos'),

    #Rutas para login
    path('login/', LoginAPIView.as_view(), name='api-login'),
    path('logout/', LogoutAPIView.as_view(), name='api-logout'),

    # Rutas para el módulo de inventario
    path('inventario/stock-critico/', StockCriticoListAPIView.as_view(), name='inventario-stock-critico'),
    path('inventario/<int:pk>/stock/', UpdateStockAPIView.as_view(), name='inventario-update-stock'),

    # Rutas para configuración
    path('configuracion/negocio/', ConfiguracionNegocioAPIView.as_view(), name='configuracion-negocio'),

    # Rutas para respaldo de base de datos
    path('configuracion/backup/exportar/', ExportarDBAPIView.as_view(), name='backup-exportar'),
    path('configuracion/backup/importar/', ImportarDBAPIView.as_view(), name='backup-importar'),
    path('configuracion/backup/limpiar/', LimpiarDBAPIView.as_view(), name='backup-limpiar'),
]
