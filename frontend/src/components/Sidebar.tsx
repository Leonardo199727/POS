import { useContext, useState, useEffect } from "react";
import { AuthContext } from "../context/AuthContext";
import { useCaja } from "../context/CajaContext";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { getBusinessName } from "../pages/Settings";

export const Sidebar = () => {
    const { logout } = useContext(AuthContext);
    const { cajaAbierta, cerrarCaja, triggerCajaModal } = useCaja();
    const navigate = useNavigate();
    const location = useLocation();
    const [showCerrarModal, setShowCerrarModal] = useState(false);
    const [montoFinal, setMontoFinal] = useState('');
    const [isCerrandoCaja, setIsCerrandoCaja] = useState(false);
    const [businessName, setBusinessName] = useState(getBusinessName());

    // Re-read when navigating back from settings
    useEffect(() => {
        setBusinessName(getBusinessName());
    }, [location.pathname]);

    const handleLogout = () => {
        logout();
        navigate("/login");
    };

    const handleCerrarCaja = async () => {
        const monto = parseFloat(montoFinal);
        if (isNaN(monto) || monto < 0) {
            alert("Ingrese un monto válido (mayor o igual a 0).");
            return;
        }
        setIsCerrandoCaja(true);
        await cerrarCaja(monto);
        setIsCerrandoCaja(false);
        setShowCerrarModal(false);
        setMontoFinal('');
    };

    const getLinkClass = (path: string) => {
        const isActive = location.pathname === path || (path === '/products' && location.pathname.startsWith('/products'));
        return isActive
            ? "flex items-center gap-4 px-6 py-3 bg-slate-900 text-primary border-r-4 border-primary"
            : "flex items-center gap-4 px-6 py-3 text-slate-400 hover:text-slate-100 hover:bg-slate-900 transition-colors";
    };

    return (
        <>
            <aside className="w-64 flex flex-col border-r border-slate-800 bg-slate-950">
                <div className="p-6 border-b border-slate-800">
                    <h1 className="text-xl font-bold tracking-tighter text-primary flex items-center gap-2">
                        <span className="material-symbols-outlined">terminal</span>
                        {businessName}
                    </h1>
                    <p className="text-[10px] uppercase tracking-widest text-slate-500 mt-1">POS v0.0.1</p>
                </div>
                <nav className="flex-1 py-4 space-y-1">
                    <Link className={getLinkClass("/home")} to="/home">
                        <span className="material-symbols-outlined">point_of_sale</span>
                        <span className="text-sm font-semibold uppercase tracking-wide">POS</span>
                    </Link>
                    <Link className={getLinkClass("/ventas")} to="/ventas">
                        <span className="material-symbols-outlined">receipt_long</span>
                        <span className="text-sm font-semibold uppercase tracking-wide">Ventas</span>
                    </Link>
                    <Link className={getLinkClass("/abonos")} to="/abonos">
                        <span className="material-symbols-outlined">payments</span>
                        <span className="text-sm font-semibold uppercase tracking-wide">Cargos y Abonos</span>
                    </Link>
                    <Link className={getLinkClass("/clientes")} to="/clientes">
                        <span className="material-symbols-outlined">group</span>
                        <span className="text-sm font-semibold uppercase tracking-wide">Clientes</span>
                    </Link>
                    <Link className={getLinkClass("/products")} to="/products">
                        <span className="material-symbols-outlined">inventory_2</span>
                        <span className="text-sm font-semibold uppercase tracking-wide">Productos</span>
                    </Link>
                    <Link className={getLinkClass("/inventario")} to="/inventario">
                        <span className="material-symbols-outlined">warehouse</span>
                        <span className="text-sm font-semibold uppercase tracking-wide">Inventario</span>
                    </Link>
                    <Link className={getLinkClass("/reportes")} to="/reportes">
                        <span className="material-symbols-outlined">analytics</span>
                        <span className="text-sm font-semibold uppercase tracking-wide">Reportes y estadisticas</span>
                    </Link>
                </nav>
                <div className="p-4 border-t border-slate-800 space-y-2">
                    {/* Caja Status & Control */}
                    {cajaAbierta ? (
                        <button
                            onClick={() => setShowCerrarModal(true)}
                            className="w-full flex items-center gap-4 px-3 py-2 text-emerald-400/70 hover:text-emerald-300 hover:bg-emerald-950/30 rounded transition-colors text-left"
                        >
                            <span className="material-symbols-outlined text-xl">point_of_sale</span>
                            <div className="flex flex-col">
                                <span className="text-xs font-medium uppercase tracking-widest">Cerrar Caja</span>
                                <span className="text-[9px] text-emerald-500/50 font-mono uppercase">● Abierta</span>
                            </div>
                        </button>
                    ) : (
                        <button
                            onClick={triggerCajaModal}
                            className="w-full flex items-center gap-4 px-3 py-2 text-amber-400/70 hover:text-amber-300 hover:bg-amber-950/30 rounded transition-colors text-left"
                        >
                            <span className="material-symbols-outlined text-xl">point_of_sale</span>
                            <div className="flex flex-col">
                                <span className="text-xs font-medium uppercase tracking-widest">Abrir Caja</span>
                                <span className="text-[9px] text-amber-500/50 font-mono uppercase">● Cerrada</span>
                            </div>
                        </button>
                    )}

                    <Link 
                        to="/settings"
                        className={`w-full flex items-center gap-4 px-3 py-2 rounded transition-colors text-left ${
                            location.pathname === '/settings'
                                ? 'text-primary bg-slate-900'
                                : 'text-slate-500 hover:text-slate-100 hover:bg-slate-900'
                        }`}
                    >
                        <span className="material-symbols-outlined text-xl">settings</span>
                        <span className="text-xs font-medium uppercase">Configuración</span>
                    </Link>
                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-4 px-3 py-2 text-red-500/70 hover:text-red-400 hover:bg-red-950/30 rounded transition-colors text-left"
                    >
                        <span className="material-symbols-outlined text-xl">logout</span>
                        <span className="text-xs font-medium uppercase tracking-widest">Cerrar Sesión</span>
                    </button>
                </div>
            </aside>

            {/* Modal: Cerrar Caja */}
            {showCerrarModal && (
                <>
                    <div className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm" onClick={() => setShowCerrarModal(false)} />
                    <div className="fixed inset-0 z-[61] flex items-center justify-center p-4">
                        <div className="bg-slate-900 border border-slate-700 shadow-2xl rounded-sm w-full max-w-md overflow-hidden">
                            <div className="px-6 py-5 bg-slate-950 border-b border-slate-800 flex items-center gap-3">
                                <span className="material-symbols-outlined text-primary text-2xl">point_of_sale</span>
                                <div>
                                    <h3 className="text-lg font-bold text-slate-100 uppercase tracking-wider">Cierre de Caja</h3>
                                    <p className="text-[10px] text-slate-500 font-mono mt-0.5 uppercase tracking-widest">CONTEO FINAL DE EFECTIVO</p>
                                </div>
                            </div>
                            <div className="p-6 space-y-6">
                                <div className="text-center">
                                    <p className="text-slate-300 text-sm">¿Cuánto efectivo hay en caja?</p>
                                    <p className="text-slate-500 text-[10px] mt-1 uppercase tracking-widest">
                                        Ingrese el monto contado físicamente
                                    </p>
                                </div>
                                <div className="relative">
                                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-xl font-bold">$</span>
                                    <input
                                        autoFocus
                                        type="number"
                                        min="0"
                                        step="0.01"
                                        placeholder="0.00"
                                        value={montoFinal}
                                        onChange={(e) => setMontoFinal(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === 'Enter') handleCerrarCaja(); }}
                                        className="w-full bg-slate-800 border border-slate-700 text-slate-100 py-4 pl-10 pr-4 text-2xl font-mono text-center focus:border-primary focus:outline-none focus:ring-0 rounded-sm transition-all tracking-wider"
                                    />
                                </div>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => { setShowCerrarModal(false); setMontoFinal(''); }}
                                        className="flex-1 py-3 border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500 font-bold text-xs uppercase tracking-widest transition-colors rounded-sm"
                                    >
                                        Cancelar
                                    </button>
                                    <button
                                        onClick={handleCerrarCaja}
                                        disabled={isCerrandoCaja}
                                        className="flex-1 py-3 bg-red-600 hover:bg-red-500 text-white font-bold text-xs uppercase tracking-widest transition-colors rounded-sm shadow-lg shadow-red-600/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {isCerrandoCaja ? (
                                            <>
                                                <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
                                                Cerrando...
                                            </>
                                        ) : (
                                            <>
                                                <span className="material-symbols-outlined text-[16px]">lock</span>
                                                Cerrar Caja
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </>
    );
};
