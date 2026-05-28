import { useState, useEffect, useContext } from 'react';
import { Sidebar } from '../components/Sidebar';
import { AuthContext } from '../context/AuthContext';
import api from '../api/axios';
import { useRefresh } from '../context/RefreshContext';

// ── Tipos ────────────────────────────────────────────────────────────
interface StockCriticoItem {
    id: number;
    codigo_interno: string;
    producto_nombre: string;
    stock_actual: number;
    stock_minimo: number;
}

interface PaginationMeta {
    count: number;
    total_pages: number;
    current_page: number;
    next: string | null;
    previous: string | null;
}

interface CatalogItem {
    id: number;
    nombre: string;
}

// ── Componente ───────────────────────────────────────────────────────
export default function Inventory() {
    const { token } = useContext(AuthContext);
    const { refreshKey } = useRefresh();
    const [activeTab, setActiveTab] = useState<'categorias' | 'marcas'>('categorias');

    // Stock Crítico state
    const [criticalStock, setCriticalStock] = useState<StockCriticoItem[]>([]);
    const [meta, setMeta] = useState<PaginationMeta | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [searchStock, setSearchStock] = useState('');

    // Catálogo state
    const [categorias, setCategorias] = useState<CatalogItem[]>([]);
    const [marcas, setMarcas] = useState<CatalogItem[]>([]);
    const [isLoadingCatalog, setIsLoadingCatalog] = useState(true);

    // Modal state
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalInput, setModalInput] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [modalError, setModalError] = useState('');
    const [searchCatalog, setSearchCatalog] = useState('');

    // Edit Stock Modal state
    const [isEditStockOpen, setIsEditStockOpen] = useState(false);
    const [selectedStockItem, setSelectedStockItem] = useState<StockCriticoItem | null>(null);
    const [editStockValue, setEditStockValue] = useState('');
    const [isUpdatingStock, setIsUpdatingStock] = useState(false);
    const [updateStockError, setUpdateStockError] = useState('');

    // ── Fetch Stock Crítico ──────────────────────────────────────────
    const fetchStockCritico = async (page: number, search: string = '') => {
        if (!token) return;
        try {
            setIsLoading(true);
            const params = new URLSearchParams({ page: String(page) });
            if (search.trim()) params.append('search', search.trim());
            const res = await api.get(`inventario/stock-critico/?${params.toString()}`, {
                headers: { Authorization: `Token ${token}` },
            });
            if (res.data.success) {
                setCriticalStock(res.data.data);
                setMeta(res.data.meta);
            }
        } catch (error) {
            console.error('Error fetching stock crítico:', error);
        } finally {
            setIsLoading(false);
        }
    };

    // ── Fetch Categorías y Marcas ─────────────────────────────────────
    const fetchCategorias = async () => {
        if (!token) return;
        try {
            const res = await api.get('categorias/', {
                headers: { Authorization: `Token ${token}` },
            });
            setCategorias(res.data);
        } catch (error) {
            console.error('Error fetching categorías:', error);
        }
    };

    const fetchMarcas = async () => {
        if (!token) return;
        try {
            const res = await api.get('marcas/', {
                headers: { Authorization: `Token ${token}` },
            });
            setMarcas(res.data);
        } catch (error) {
            console.error('Error fetching marcas:', error);
        }
    };

    useEffect(() => {
        fetchStockCritico(currentPage, searchStock);
    }, [currentPage, token, refreshKey]);

    // Debounce search para stock crítico
    useEffect(() => {
        const timer = setTimeout(() => {
            setCurrentPage(1);
            fetchStockCritico(1, searchStock);
        }, 400);
        return () => clearTimeout(timer);
    }, [searchStock]);

    useEffect(() => {
        const loadCatalog = async () => {
            setIsLoadingCatalog(true);
            await Promise.all([fetchCategorias(), fetchMarcas()]);
            setIsLoadingCatalog(false);
        };
        loadCatalog();
    }, [token, refreshKey]);

    // ── Handlers paginación ──────────────────────────────────────────
    const handlePrevPage = () => {
        if (meta?.previous) setCurrentPage((p) => Math.max(1, p - 1));
    };
    const handleNextPage = () => {
        if (meta?.next) setCurrentPage((p) => p + 1);
    };

    // ── Handler crear categoría/marca ────────────────────────────────
    const handleCreate = async () => {
        if (!modalInput.trim()) {
            setModalError('El nombre es obligatorio.');
            return;
        }
        if (!token) return;

        setIsSubmitting(true);
        setModalError('');

        const endpoint = activeTab === 'categorias' ? 'categorias/' : 'marcas/';

        try {
            await api.post(endpoint, { nombre: modalInput.trim() }, {
                headers: { Authorization: `Token ${token}` },
            });
            // Refrescar la lista correspondiente
            if (activeTab === 'categorias') {
                await fetchCategorias();
            } else {
                await fetchMarcas();
            }
            setModalInput('');
            setIsModalOpen(false);
        } catch (error: any) {
            const detail = error?.response?.data?.nombre?.[0] || error?.response?.data?.detail || 'Error al crear. Inténtalo de nuevo.';
            setModalError(detail);
        } finally {
            setIsSubmitting(false);
        }
    };

    const openModal = () => {
        setModalInput('');
        setModalError('');
        setIsModalOpen(true);
    };

    // ── Edit Stock handler ───────────────────────────────────────────
    const openEditStock = (item: StockCriticoItem) => {
        setSelectedStockItem(item);
        setEditStockValue(String(item.stock_actual));
        setUpdateStockError('');
        setIsEditStockOpen(true);
    };

    const handleUpdateStock = async () => {
        if (!selectedStockItem || !token) return;
        const value = parseInt(editStockValue, 10);
        if (isNaN(value) || value < 0) {
            setUpdateStockError('El stock debe ser un número ≥ 0.');
            return;
        }
        setIsUpdatingStock(true);
        setUpdateStockError('');
        try {
            await api.patch(`inventario/${selectedStockItem.id}/stock/`, {
                stock_actual: value,
            }, {
                headers: { Authorization: `Token ${token}` },
            });
            setIsEditStockOpen(false);
            setSelectedStockItem(null);
            fetchStockCritico(currentPage, searchStock);
        } catch (err: any) {
            setUpdateStockError(
                err.response?.data?.stock_actual?.[0] ||
                err.response?.data?.detail ||
                'Error al actualizar el stock.'
            );
        } finally {
            setIsUpdatingStock(false);
        }
    };

    return (
        <div className="flex h-screen w-full overflow-hidden bg-[#1E293B] font-['Space_Grotesk']">
            <Sidebar />

            {/* Contenedor principal (paneles + footer) */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Paneles lado a lado */}
                <div className="flex-1 flex overflow-hidden">

                    {/* Left Panel (50%) - STOCK CRÍTICO */}
                    <main className="flex-1 w-1/2 h-full bg-[#0f1523] border-r border-slate-800 flex flex-col overflow-hidden">
                        <div className="p-8 pb-0 shrink-0">
                            <div className="flex items-center justify-between mb-4">
                                <div>
                                    <h2 className="text-3xl font-black text-white tracking-tight">Stock Crítico</h2>
                                    <p className="text-slate-400 text-sm mt-1">Sistemas con niveles bajos de existencias.</p>
                                </div>
                            </div>

                            {/* Buscador Stock */}
                            <div className="relative mb-4">
                                <span className="absolute left-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500">search</span>
                                <input
                                    className="w-full bg-slate-900 border border-slate-700 text-slate-100 py-3 pl-12 pr-12 focus:border-primary focus:outline-none focus:ring-0 text-sm tracking-wider uppercase rounded-sm transition-all placeholder:text-slate-500"
                                    placeholder="BUSCAR POR PRODUCTO O CÓDIGO..."
                                    type="text"
                                    value={searchStock}
                                    onChange={(e) => setSearchStock(e.target.value)}
                                />
                                {searchStock && (
                                    <button
                                        onClick={() => setSearchStock('')}
                                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                                    >
                                        <span className="material-symbols-outlined text-lg">close</span>
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="flex-1 flex flex-col min-h-0 px-8 pb-4">
                            <div className="bg-slate-900 border border-slate-700 rounded-sm overflow-hidden flex-1 relative flex flex-col min-h-0 shadow-lg">
                                <div className="flex-1 overflow-auto w-full pb-14">
                                    <table className="w-full text-left text-xs text-slate-300 border-collapse">
                                        <thead className="bg-[#0b1121] border-y border-slate-700 text-[9px] uppercase text-slate-500 font-bold tracking-widest sticky top-0 z-10 shadow-sm">
                                            <tr>
                                                <th scope="col" className="px-3 py-3 w-[25%] leading-tight">Código Interno</th>
                                                <th scope="col" className="px-3 py-3 w-[35%]">Producto</th>
                                                <th scope="col" className="px-3 py-3 text-right w-[20%]">Stock</th>
                                                <th scope="col" className="px-3 py-3 text-center w-[20%]">Acción</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {isLoading ? (
                                                <tr>
                                                    <td colSpan={4} className="px-3 py-12 text-center text-slate-500">
                                                        <div className="flex flex-col items-center gap-2">
                                                            <span className="material-symbols-outlined animate-spin text-primary text-3xl">progress_activity</span>
                                                            <p className="text-[10px] uppercase font-bold tracking-widest">CARGANDO INVENTARIO...</p>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ) : criticalStock.length === 0 ? (
                                                <tr>
                                                    <td colSpan={4} className="px-3 py-8 text-center text-slate-500 font-medium">
                                                        <div className="flex flex-col items-center justify-center gap-2">
                                                            <span className="material-symbols-outlined text-4xl" style={{ color: searchStock ? undefined : 'rgba(34,197,94,0.5)' }}>{searchStock ? 'search_off' : 'check_circle'}</span>
                                                            <p className="text-[10px] uppercase font-bold tracking-widest mt-2">
                                                                {searchStock ? `NO SE ENCONTRARON RESULTADOS PARA "${searchStock}".` : 'SISTEMAS NOMINALES. NO HAY STOCK CRÍTICO.'}
                                                            </p>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ) : (
                                                criticalStock.map((item) => (
                                                    <tr key={item.id} className="bg-slate-900 border-b border-slate-800/80 hover:bg-slate-800/50 transition-colors group">
                                                        <td className="px-3 py-3 font-mono text-primary font-medium text-[11px] truncate">{item.codigo_interno}</td>
                                                        <td className="px-3 py-3 text-slate-100 font-medium text-xs truncate max-w-[150px]" title={item.producto_nombre}>{item.producto_nombre}</td>
                                                        <td className="px-3 py-3 text-right">
                                                            <span className={`font-mono flex items-center justify-end gap-1 font-bold text-xs ${item.stock_actual <= 0 ? 'text-red-500' : 'text-red-400/90'}`}>
                                                                <span>{item.stock_actual}</span>
                                                                <span className={`text-[9px] uppercase ${item.stock_actual <= 0 ? 'text-red-600/70' : 'text-red-600/50'}`}>UND</span>
                                                            </span>
                                                        </td>
                                                        <td className="px-3 py-3 text-center">
                                                            <button
                                                                onClick={() => openEditStock(item)}
                                                                className="w-full flex items-center justify-center gap-1.5 bg-primary/10 text-primary border border-primary/30 hover:bg-primary hover:text-white hover:border-primary transition-all rounded-sm px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider disabled:opacity-50 disabled:cursor-not-allowed"
                                                            >
                                                                <span className="material-symbols-outlined text-[14px]">edit</span>
                                                                <span>Editar</span>
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                </div>

                                {/* Paginación (sticky bottom) */}
                                {meta && !isLoading && criticalStock.length > 0 && (
                                    <div className="h-14 border-t border-slate-800 flex items-center justify-between px-4 bg-slate-900 absolute bottom-0 w-full">
                                        <span className="text-[10px] text-slate-500 font-medium tracking-wider uppercase">
                                            Página {meta.current_page} de {meta.total_pages} • {meta.count} totales
                                        </span>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={handlePrevPage}
                                                disabled={!meta.previous}
                                                className="w-8 h-8 flex items-center justify-center rounded-sm border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                                            >
                                                <span className="material-symbols-outlined text-[16px]">chevron_left</span>
                                            </button>
                                            <span className="text-xs font-mono text-slate-300 w-6 text-center">{meta.current_page}</span>
                                            <button
                                                onClick={handleNextPage}
                                                disabled={!meta.next}
                                                className="w-8 h-8 flex items-center justify-center rounded-sm border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                                            >
                                                <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </main>

                    {/* Right Panel (50%) - GESTIÓN DE CATÁLOGO */}
                    <section className="flex-1 w-1/2 h-full bg-[#0b111c] flex flex-col overflow-hidden">
                        <div className="p-8 pb-0 shrink-0">
                            <div className="flex items-center justify-between mb-4 gap-4">
                                <div className="flex-1 min-w-[200px]">
                                    <h2 className="text-3xl font-black text-white tracking-tight truncate">Gestión de Catálogo</h2>
                                    <p className="text-slate-400 text-sm mt-1 truncate">Administración de categorías y marcas.</p>
                                </div>
                                <button
                                    onClick={openModal}
                                    className="bg-primary hover:bg-orange-600 text-white font-bold py-2.5 px-5 flex items-center justify-center gap-2 transition-colors rounded-sm shadow-lg shadow-primary/20 text-xs uppercase tracking-widest min-w-[160px] shrink-0"
                                >
                                    <span className="material-symbols-outlined text-[18px]">add</span>
                                    {activeTab === 'categorias' ? 'Nueva Categoría' : 'Nueva Marca'}
                                </button>
                            </div>

                            {/* Buscador Catálogo */}
                            <div className="relative mb-4">
                                <span className="absolute left-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500">search</span>
                                <input
                                    className="w-full bg-slate-900 border border-slate-700 text-slate-100 py-3 pl-12 pr-12 focus:border-primary focus:outline-none focus:ring-0 text-sm tracking-wider uppercase rounded-sm transition-all placeholder:text-slate-500"
                                    placeholder={activeTab === 'categorias' ? 'BUSCAR CATEGORÍA...' : 'BUSCAR MARCA...'}
                                    type="text"
                                    value={searchCatalog}
                                    onChange={(e) => setSearchCatalog(e.target.value)}
                                />
                                {searchCatalog && (
                                    <button
                                        onClick={() => setSearchCatalog('')}
                                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                                    >
                                        <span className="material-symbols-outlined text-lg">close</span>
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="flex-1 flex flex-col min-h-0 px-8 pb-4">
                            <div className="border-b border-slate-800 mb-6 flex gap-8 shrink-0">
                                <button
                                    onClick={() => { setActiveTab('categorias'); setSearchCatalog(''); }}
                                    className={`pb-3 border-b-2 text-xs font-bold uppercase tracking-widest transition-colors ${activeTab === 'categorias' ? 'border-primary text-slate-100' : 'border-transparent text-slate-500 hover:text-slate-300'}`}
                                >
                                    Categorías ({categorias.length})
                                </button>
                                <button
                                    onClick={() => { setActiveTab('marcas'); setSearchCatalog(''); }}
                                    className={`pb-3 border-b-2 text-xs font-bold uppercase tracking-widest transition-colors ${activeTab === 'marcas' ? 'border-primary text-slate-100' : 'border-transparent text-slate-500 hover:text-slate-300'}`}
                                >
                                    Marcas ({marcas.length})
                                </button>
                            </div>

                            {/* Lista del catálogo (scrollable) */}
                            <div className="flex-1 overflow-y-auto min-h-0">
                                {isLoadingCatalog ? (
                                    <div className="flex flex-col items-center justify-center py-12 gap-2">
                                        <span className="material-symbols-outlined animate-spin text-primary text-3xl">progress_activity</span>
                                        <p className="text-[10px] uppercase font-bold tracking-widest text-slate-500">CARGANDO CATÁLOGO...</p>
                                    </div>
                                ) : (() => {
                                    const items = (activeTab === 'categorias' ? categorias : marcas)
                                        .filter(item => item.nombre.toLowerCase().includes(searchCatalog.toLowerCase()));
                                    return (
                                        <div className="flex flex-col gap-3">
                                            {items.length === 0 ? (
                                                <div className="flex flex-col items-center justify-center py-12 gap-2">
                                                    <span className="material-symbols-outlined text-slate-600 text-4xl">{searchCatalog ? 'search_off' : 'inventory_2'}</span>
                                                    <p className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mt-2">
                                                        {searchCatalog
                                                            ? `No se encontraron ${activeTab === 'categorias' ? 'categorías' : 'marcas'} con "${searchCatalog}".`
                                                            : `No hay ${activeTab === 'categorias' ? 'categorías' : 'marcas'} registradas.`
                                                        }
                                                    </p>
                                                </div>
                                            ) : (
                                                items.map((item) => (
                                                    <div key={item.id} className="flex items-center justify-between p-4 bg-slate-800/20 border border-slate-700/50 hover:border-slate-600 transition-all rounded-lg group">
                                                        <div className="flex items-center gap-4">
                                                            <div className="w-10 h-10 rounded-lg bg-[#0f1523] border border-[#1E293B] flex items-center justify-center text-slate-500 group-hover:text-primary transition-colors">
                                                                <span className="material-symbols-outlined">
                                                                    {activeTab === 'categorias' ? 'category' : 'sell'}
                                                                </span>
                                                            </div>
                                                            <div>
                                                                <p className="text-sm font-bold uppercase tracking-tight text-slate-100">{item.nombre}</p>
                                                                <p className="text-[10px] text-slate-500 font-mono">ID: {item.id}</p>
                                                            </div>
                                                        </div>
                                                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                            <button className="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-white hover:bg-slate-700 rounded transition-all">
                                                                <span className="material-symbols-outlined text-lg">edit</span>
                                                            </button>
                                                            <button className="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-all">
                                                                <span className="material-symbols-outlined text-lg">delete</span>
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    );
                                })()}
                            </div>
                        </div>
                    </section>

                </div>

                {/* Footer (ancho completo) */}
                <footer className="h-8 bg-slate-950 border-t border-slate-800 px-4 flex items-center justify-between shrink-0">
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
                            {new Date().toLocaleDateString('es-ES')} | {new Date().toLocaleTimeString('es-ES')}
                        </div>
                    </div>
                </footer>
            </div>

            {/* ── Modal Crear Categoría / Marca ────────────────────────── */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={() => !isSubmitting && setIsModalOpen(false)}
                    />
                    <div className="relative bg-[#0f1523] border border-slate-700 rounded-lg shadow-2xl w-full max-w-md p-6 mx-4">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-lg font-black text-white tracking-tight">
                                {activeTab === 'categorias' ? 'Nueva Categoría' : 'Nueva Marca'}
                            </h3>
                            <button
                                onClick={() => !isSubmitting && setIsModalOpen(false)}
                                className="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-white hover:bg-slate-700 rounded transition-all"
                            >
                                <span className="material-symbols-outlined text-lg">close</span>
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-[10px] uppercase font-bold tracking-widest text-slate-500 mb-2">
                                    Nombre de la {activeTab === 'categorias' ? 'categoría' : 'marca'}
                                </label>
                                <input
                                    type="text"
                                    value={modalInput}
                                    onChange={(e) => { setModalInput(e.target.value); setModalError(''); }}
                                    onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                                    placeholder={activeTab === 'categorias' ? 'Ej: Herramientas Eléctricas' : 'Ej: DeWalt'}
                                    autoFocus
                                    disabled={isSubmitting}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-sm px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all disabled:opacity-50"
                                />
                            </div>
                            {modalError && (
                                <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-sm px-3 py-2">
                                    <span className="material-symbols-outlined text-[16px]">error</span>
                                    {modalError}
                                </div>
                            )}
                            <div className="flex items-center justify-end gap-3 pt-2">
                                <button
                                    onClick={() => setIsModalOpen(false)}
                                    disabled={isSubmitting}
                                    className="px-4 py-2.5 text-xs font-bold uppercase tracking-widest text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 rounded-sm transition-all disabled:opacity-50"
                                >
                                    Cancelar
                                </button>
                                <button
                                    onClick={handleCreate}
                                    disabled={isSubmitting || !modalInput.trim()}
                                    className="px-5 py-2.5 text-xs font-bold uppercase tracking-widest bg-primary hover:bg-orange-600 text-white rounded-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-primary/20"
                                >
                                    {isSubmitting ? (
                                        <>
                                            <span className="material-symbols-outlined animate-spin text-[14px]">progress_activity</span>
                                            Guardando...
                                        </>
                                    ) : (
                                        <>
                                            <span className="material-symbols-outlined text-[14px]">add</span>
                                            Crear
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Modal Editar Stock ──────────────────────────────────── */}
            {isEditStockOpen && selectedStockItem && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={() => !isUpdatingStock && setIsEditStockOpen(false)}
                    />
                    <div className="relative bg-[#0f1523] border border-slate-700 rounded-lg shadow-2xl w-full max-w-md p-6 mx-4">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-lg font-black text-white tracking-tight">Actualizar Stock</h3>
                            <button
                                onClick={() => !isUpdatingStock && setIsEditStockOpen(false)}
                                className="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-white hover:bg-slate-700 rounded transition-all"
                            >
                                <span className="material-symbols-outlined text-lg">close</span>
                            </button>
                        </div>

                        {/* Info del producto */}
                        <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4 mb-6">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
                                    <span className="material-symbols-outlined text-primary">inventory_2</span>
                                </div>
                                <div>
                                    <p className="text-sm font-bold text-white">{selectedStockItem.producto_nombre}</p>
                                    <p className="text-[10px] font-mono text-primary">{selectedStockItem.codigo_interno}</p>
                                </div>
                            </div>
                            <div className="flex gap-4 mt-3 pt-3 border-t border-slate-700/50">
                                <div>
                                    <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Stock Actual</p>
                                    <p className={`text-lg font-black font-mono ${selectedStockItem.stock_actual <= 0 ? 'text-red-500' : 'text-red-400'}`}>
                                        {selectedStockItem.stock_actual}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Stock Mínimo</p>
                                    <p className="text-lg font-black font-mono text-slate-300">{selectedStockItem.stock_minimo}</p>
                                </div>
                            </div>
                        </div>

                        {/* Input stock */}
                        <div className="space-y-4">
                            <div>
                                <label className="block text-[10px] uppercase font-bold tracking-widest text-slate-500 mb-2">
                                    Nuevo Stock
                                </label>
                                <input
                                    type="number"
                                    min="0"
                                    value={editStockValue}
                                    onChange={(e) => { setEditStockValue(e.target.value); setUpdateStockError(''); }}
                                    onKeyDown={(e) => e.key === 'Enter' && handleUpdateStock()}
                                    placeholder="0"
                                    autoFocus
                                    disabled={isUpdatingStock}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-sm px-4 py-3 text-lg text-center text-slate-100 font-mono font-bold placeholder-slate-600 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all disabled:opacity-50"
                                />
                            </div>

                            {updateStockError && (
                                <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-sm px-3 py-2">
                                    <span className="material-symbols-outlined text-[16px]">error</span>
                                    {updateStockError}
                                </div>
                            )}

                            <div className="flex items-center justify-end gap-3 pt-2">
                                <button
                                    onClick={() => setIsEditStockOpen(false)}
                                    disabled={isUpdatingStock}
                                    className="px-4 py-2.5 text-xs font-bold uppercase tracking-widest text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 rounded-sm transition-all disabled:opacity-50"
                                >
                                    Cancelar
                                </button>
                                <button
                                    onClick={handleUpdateStock}
                                    disabled={isUpdatingStock || editStockValue === ''}
                                    className="px-5 py-2.5 text-xs font-bold uppercase tracking-widest bg-primary hover:bg-orange-600 text-white rounded-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-primary/20"
                                >
                                    {isUpdatingStock ? (
                                        <>
                                            <span className="material-symbols-outlined animate-spin text-[14px]">progress_activity</span>
                                            Guardando...
                                        </>
                                    ) : (
                                        <>
                                            <span className="material-symbols-outlined text-[14px]">save</span>
                                            Guardar
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

