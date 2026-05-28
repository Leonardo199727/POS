import { useState, useEffect, useContext } from "react";
import { Sidebar } from "../components/Sidebar";
import api from "../api/axios";
import { AuthContext } from "../context/AuthContext";
import { useRefresh } from "../context/RefreshContext";
import { useNavigate } from "react-router-dom";

interface EstadisticasRapidas {
    ventas_hoy: number;
    ventas_vs_ayer_porcentaje: number;
    clientes_activos_hoy: number;
    items_en_stock: number;
    items_bajo_stock_critico: number;
    utilidad_estimada: number | null;
    utilidad_margen: number | null;
}

const Reports = () => {
    const { token } = useContext(AuthContext);
    const { refreshKey } = useRefresh();
    const navigate = useNavigate();
    
    // Current time state for the footer
    const [currentTime, setCurrentTime] = useState(new Date());
    
    // Stats State
    const [estadisticas, setEstadisticas] = useState<EstadisticasRapidas>({
        ventas_hoy: 0,
        ventas_vs_ayer_porcentaje: 0,
        clientes_activos_hoy: 0,
        items_en_stock: 0,
        items_bajo_stock_critico: 0,
        utilidad_estimada: null,
        utilidad_margen: null,
    });
    const [isLoadingStats, setIsLoadingStats] = useState(true);

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        if (!token) return;
        const fetchDashboardData = async () => {
            setIsLoadingStats(true);
            try {
                const res = await api.get('reportes/dashboard/', {
                    headers: { Authorization: `Token ${token}` }
                });
                if (res.data.success && res.data.data.estadisticas_rapidas) {
                    setEstadisticas(res.data.data.estadisticas_rapidas);
                }
            } catch (error) {
                console.error("Error fetching dashboard stats:", error);
            } finally {
                setIsLoadingStats(false);
            }
        };
        fetchDashboardData();
    }, [token, refreshKey]);

    const formatCurrency = (amount: number | null) => {
        if (amount === null) return 'Restringido';
        return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background-dark text-slate-100 font-display">
            {/* Nav Lateral */}
            <Sidebar />

            {/* Contenido Principal */}
            <main className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#0f1523]">
                


                {/* Dashboard Scrollable Content */}
                <div className="flex-1 overflow-auto p-8">
                    
                    {/* Dashboard Statistics Row */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8 mt-2">
                        
                        <div className="bg-slate-900 p-5 rounded-sm border-l-4 border-primary relative overflow-hidden group">
                            <div className="absolute top-2 right-2 flex items-center gap-1">
                                <div className="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
                                <span className="text-[8px] font-mono text-primary opacity-60">LIVE</span>
                            </div>
                            <p className="text-[10px] uppercase tracking-widest text-slate-400 mb-1">Ventas Hoy</p>
                            <p className="text-2xl font-mono font-bold text-white tracking-tighter">
                                {isLoadingStats ? '...' : formatCurrency(estadisticas.ventas_hoy)}
                            </p>
                            <div className={`mt-4 flex items-center gap-1 text-[10px] ${estadisticas.ventas_vs_ayer_porcentaje >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                <span className="material-symbols-outlined text-xs">
                                    {estadisticas.ventas_vs_ayer_porcentaje >= 0 ? 'trending_up' : 'trending_down'}
                                </span>
                                <span className="font-mono">
                                    {estadisticas.ventas_vs_ayer_porcentaje > 0 ? '+' : ''}{estadisticas.ventas_vs_ayer_porcentaje.toFixed(1)}% vs ayer
                                </span>
                            </div>
                        </div>

                        <div className="bg-slate-900 p-5 rounded-sm border-l-4 border-sky-500 relative overflow-hidden">
                            <p className="text-[10px] uppercase tracking-widest text-slate-400 mb-1">Clientes Activos</p>
                            <p className="text-2xl font-mono font-bold text-white tracking-tighter">
                                {isLoadingStats ? '...' : estadisticas.clientes_activos_hoy.toLocaleString()}
                            </p>
                            <div className="mt-4 flex items-center gap-1 text-[10px] text-slate-500">
                                <span className="material-symbols-outlined text-xs">group</span>
                                <span className="font-mono">Movimientos de hoy</span>
                            </div>
                        </div>

                        <div className="bg-slate-900 p-5 rounded-sm border-l-4 border-slate-700 relative overflow-hidden">
                            <p className="text-[10px] uppercase tracking-widest text-slate-400 mb-1">Items en Stock</p>
                            <p className="text-2xl font-mono font-bold text-white tracking-tighter">
                                {isLoadingStats ? '...' : estadisticas.items_en_stock.toLocaleString()}
                            </p>
                            <div className="mt-4 flex items-center gap-1 text-[10px] text-red-400 font-mono">
                                <span className="material-symbols-outlined text-xs">warning</span>
                                <span>{estadisticas.items_bajo_stock_critico} bajo stock crítico</span>
                            </div>
                        </div>

                        <div className="bg-slate-900 p-5 rounded-sm border-l-4 border-primary relative overflow-hidden">
                            <p className="text-[10px] uppercase tracking-widest text-slate-400 mb-1">Utilidad Estimada</p>
                            <p className={`text-2xl font-mono font-bold tracking-tighter ${estadisticas.utilidad_estimada === null && !isLoadingStats ? 'text-rose-400 text-xl' : 'text-white'}`}>
                                {isLoadingStats ? '...' : formatCurrency(estadisticas.utilidad_estimada)}
                            </p>
                            <div className="mt-4 flex items-center gap-1 text-[10px] text-primary">
                                {estadisticas.utilidad_estimada !== null ? (
                                    <>
                                        <span className="material-symbols-outlined text-xs">analytics</span>
                                        <span className="font-mono">Margen: {estadisticas.utilidad_margen?.toFixed(1) || 0}%</span>
                                    </>
                                ) : (
                                    <>
                                        <span className="material-symbols-outlined text-xs text-rose-500">lock</span>
                                        <span className="font-mono text-rose-500">Solo Administradores</span>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Bento Grid: Report Modules */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        
                        {/* Module 1: Crédito y Cobranza */}
                        <button 
                            onClick={() => navigate('/reportes/credito-cobranza')}
                            className="text-left bg-slate-900 p-8 rounded-sm border border-slate-800 hover:border-primary/50 active:scale-[0.99] transition-all duration-300 flex flex-col justify-between group h-[320px] focus:outline-none focus:ring-1 focus:ring-primary/50"
                        >
                            <div>
                                <div className="flex items-start justify-between mb-6">
                                    <div className="w-12 h-12 bg-slate-800 flex items-center justify-center rounded-sm group-hover:bg-primary/10 transition-colors">
                                        <span className="material-symbols-outlined text-primary text-3xl">payments</span>
                                    </div>
                                    <span className="text-[10px] font-mono text-slate-500 bg-slate-950 px-2 py-1">ID: REP-001</span>
                                </div>
                                <h3 className="text-xl font-bold text-white mb-2 tracking-tight group-hover:text-primary transition-colors">Crédito y Cobranza</h3>
                                <p className="text-sm text-slate-400 leading-relaxed max-w-sm">Estado de cuenta, historial individual y sumatoria de deuda vencida. Análisis de antigüedad de saldos.</p>
                            </div>
                            <div className="mt-8 flex items-center justify-between w-full">
                                <div className="flex -space-x-2">
                                    <div className="w-6 h-6 rounded-full border-2 border-slate-900 bg-slate-700"></div>
                                    <div className="w-6 h-6 rounded-full border-2 border-slate-900 bg-slate-800"></div>
                                    <div className="w-6 h-6 rounded-full border-2 border-slate-900 bg-slate-950"></div>
                                </div>
                                <span className="text-slate-500 text-xs font-bold uppercase tracking-widest flex items-center gap-1 group-hover:text-primary transition-colors">
                                    Abrir Reporte <span className="material-symbols-outlined text-sm opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">arrow_forward</span>
                                </span>
                            </div>
                        </button>

                        {/* Module 2: Pagos y Ventas */}
                        <button className="text-left bg-slate-900 p-8 rounded-sm border border-slate-800 hover:border-primary/50 active:scale-[0.99] transition-all duration-300 flex flex-col justify-between group h-[320px] focus:outline-none focus:ring-1 focus:ring-primary/50">
                            <div>
                                <div className="flex items-start justify-between mb-6">
                                    <div className="w-12 h-12 bg-slate-800 flex items-center justify-center rounded-sm group-hover:bg-primary/10 transition-colors">
                                        <span className="material-symbols-outlined text-primary text-3xl">receipt_long</span>
                                    </div>
                                    <span className="text-[10px] font-mono text-slate-500 bg-slate-950 px-2 py-1">ID: REP-002</span>
                                </div>
                                <h3 className="text-xl font-bold text-white mb-2 tracking-tight group-hover:text-primary transition-colors">Pagos y Ventas</h3>
                                <p className="text-sm text-slate-400 leading-relaxed max-w-sm">Ingresos por método de pago y ventas detalladas del día. Comparativa histórica de flujos de caja.</p>
                            </div>
                            <div className="mt-8 flex items-center justify-between w-full">
                                <div className="flex items-center gap-4">
                                    <div className="text-[10px] font-mono text-sky-400">ACTUALIZADO: {currentTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}</div>
                                </div>
                                <span className="text-slate-500 text-xs font-bold uppercase tracking-widest flex items-center gap-1 group-hover:text-primary transition-colors">
                                    Abrir Reporte <span className="material-symbols-outlined text-sm opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">arrow_forward</span>
                                </span>
                            </div>
                        </button>

                        {/* Module 3: Rendimiento */}
                        <button className="text-left bg-slate-900 p-8 rounded-sm border border-slate-800 hover:border-primary/50 active:scale-[0.99] transition-all duration-300 flex flex-col justify-between group h-[320px] focus:outline-none focus:ring-1 focus:ring-primary/50">
                            <div>
                                <div className="flex items-start justify-between mb-6">
                                    <div className="w-12 h-12 bg-slate-800 flex items-center justify-center rounded-sm group-hover:bg-primary/10 transition-colors">
                                        <span className="material-symbols-outlined text-primary text-3xl">monitoring</span>
                                    </div>
                                    <span className="text-[10px] font-mono text-slate-500 bg-slate-950 px-2 py-1">ID: REP-003</span>
                                </div>
                                <h3 className="text-xl font-bold text-white mb-2 tracking-tight group-hover:text-primary transition-colors">Rendimiento</h3>
                                <p className="text-sm text-slate-400 leading-relaxed max-w-sm">Utilidad bruta estimada y márgenes netos por categoría. Identificación de productos de alta rotación.</p>
                            </div>
                            <div className="mt-8 flex items-center justify-between w-full">
                                <div className="flex gap-1 items-end h-4 group-hover:scale-110 origin-bottom transition-transform">
                                    <div className="w-1 h-2 bg-primary"></div>
                                    <div className="w-1 h-4 bg-primary/70"></div>
                                    <div className="w-1 h-3 bg-primary/40"></div>
                                </div>
                                <span className="text-slate-500 text-xs font-bold uppercase tracking-widest flex items-center gap-1 group-hover:text-primary transition-colors">
                                    Abrir Reporte <span className="material-symbols-outlined text-sm opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">arrow_forward</span>
                                </span>
                            </div>
                        </button>

                        {/* Module 4: Cierre de Caja Diario */}
                        <button className="text-left bg-slate-900 p-8 rounded-sm border border-slate-800 hover:border-primary/50 active:scale-[0.99] transition-all duration-300 flex flex-col justify-between group h-[320px] focus:outline-none focus:ring-1 focus:ring-primary/50">
                            <div>
                                <div className="flex items-start justify-between mb-6">
                                    <div className="w-12 h-12 bg-slate-800 flex items-center justify-center rounded-sm group-hover:bg-primary/10 transition-colors">
                                        <span className="material-symbols-outlined text-primary text-3xl">point_of_sale</span>
                                    </div>
                                    <span className="text-[10px] font-mono text-slate-500 bg-slate-950 px-2 py-1">ID: REP-004</span>
                                </div>
                                <h3 className="text-xl font-bold text-white mb-2 tracking-tight group-hover:text-primary transition-colors">Cierre de Caja Diario</h3>
                                <p className="text-sm text-slate-400 leading-relaxed max-w-sm">Corte Z, arqueo y cuadre de efectivo en turnos. Control de faltantes y sobrantes de caja.</p>
                            </div>
                            <div className="mt-8 flex items-center justify-between w-full">
                                <div className="px-2 py-1 bg-primary/10 rounded-sm">
                                    <span className="text-[10px] font-mono text-primary">LISTO PARA CIERRE</span>
                                </div>
                                <span className="text-slate-500 text-xs font-bold uppercase tracking-widest flex items-center gap-1 group-hover:text-primary transition-colors">
                                    Abrir Reporte <span className="material-symbols-outlined text-sm opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">arrow_forward</span>
                                </span>
                            </div>
                        </button>

                    </div>
                </div>

                {/* System Footer Info */}
                <footer className="h-8 bg-slate-950 border-t border-slate-800 px-4 flex items-center justify-between shrink-0 mt-auto">
                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2">
                            <div className="size-2 bg-green-500"></div>
                            <span className="text-[10px] font-bold text-slate-400 tracking-wider">SISTEMA ONLINE</span>
                        </div>
                        <div className="flex items-center gap-2 border-l border-slate-800 pl-4">
                            <span className="text-[10px] text-slate-500">ESTACIÓN:</span>
                            <span className="text-[10px] font-bold text-slate-300">POS-01</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 text-[10px] text-slate-400">
                            <span className="material-symbols-outlined text-xs">database</span>
                            <span>DB SYNC: OK</span>
                        </div>
                        <div className="flex items-center gap-2 border-l border-slate-800 pl-4 text-[10px] font-bold text-slate-300 tracking-widest">
                            {currentTime.toLocaleDateString('es-ES')} | {currentTime.toLocaleTimeString('es-ES')}
                        </div>
                    </div>
                </footer>
            </main>
        </div>
    );
};

export default Reports;
