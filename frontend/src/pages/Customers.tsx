import { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { Sidebar } from '../components/Sidebar';
import { CustomerDrawer } from '../components/CustomerDrawer';
import { useRefresh } from '../context/RefreshContext';
import api from '../api/axios';
import { useDebounce } from '../hooks/useDebounce';

interface Cliente {
    id: number;
    nombre: string;
    telefono: string;
    email: string;
    direccion: string;
    tipo_cliente: string;
    limite_credito: string;
    saldo_actual: string;
    activo: boolean;
    notas: string;
    created_at: string;
    updated_at: string;
}

interface ClienteMeta {
    count: number;
    total_pages: number;
    current_page: number;
    next: string | null;
    previous: string | null;
}

export const Customers = () => {
    const { user, token } = useContext(AuthContext);
    const { refreshKey } = useRefresh();
    const [clientes, setClientes] = useState<Cliente[]>([]);
    const [meta, setMeta] = useState<ClienteMeta | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const debouncedSearch = useDebounce(searchTerm, 500);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [selectedCustomerToEdit, setSelectedCustomerToEdit] = useState<any>(null);
    const [isSaving, setIsSaving] = useState(false);

    const handleSaveCustomer = async (customerData: any) => {
        if (!token) return;
        setIsSaving(true);
        try {
            if (customerData.isEdit) {
                const { isEdit, clienteId, ...payload } = customerData;
                await api.patch(`clientes/${clienteId}/`, payload, {
                    headers: { Authorization: `Token ${token}` }
                });
            } else {
                await api.post('clientes/crear/', customerData, {
                    headers: { Authorization: `Token ${token}` }
                });
            }
            setIsDrawerOpen(false);
            setSelectedCustomerToEdit(null);
            fetchClientes(currentPage, debouncedSearch);
        } catch (error) {
            console.error('Error saving customer:', error);
        } finally {
            setIsSaving(false);
        }
    };

    useEffect(() => {
        setCurrentPage(1);
        fetchClientes(1, debouncedSearch);
    }, [token, debouncedSearch, refreshKey]);

    useEffect(() => {
        fetchClientes(currentPage, debouncedSearch);
    }, [currentPage]);

    const fetchClientes = async (page: number, search: string = '') => {
        if (!token) return;
        setIsLoading(true);
        try {
            const queryParams = new URLSearchParams({ page: page.toString() });
            // Búsqueda numérica (ID): enviar inmediatamente. Texto: requiere 3+ caracteres.
            const trimmed = search.trim();
            const isNumeric = /^\d+$/.test(trimmed);
            if (trimmed.length > 0 && (isNumeric || trimmed.length >= 3)) {
                queryParams.append('search', trimmed);
            }
            const res = await api.get(`clientes/?${queryParams.toString()}`, {
                headers: { Authorization: `Token ${token}` }
            });
            if (res.data.success) {
                setClientes(res.data.data);
                setMeta(res.data.meta);
            }
        } catch (error) {
            console.error("Error fetching clientes:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const formatCurrency = (amount: string | number) => {
        const val = typeof amount === 'string' ? parseFloat(amount) : amount;
        if (isNaN(val)) return '$0.00';
        return `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background-dark text-slate-100 font-display">
            {/* Sidebar Real */}
            <Sidebar />

            {/* Contenedor Principal (Derecho) */}
            <div className="flex-1 flex flex-col bg-slate-900 overflow-hidden">
                {/* Header idéntico a Products.tsx */}
                <header className="p-4 bg-slate-950 border-b border-slate-800">
                    <div className="flex items-center gap-4">
                        <div className="flex-1 relative">
                            <span className="absolute left-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500">search</span>
                            <input
                                autoFocus
                                className="w-full bg-slate-900 border border-slate-700 text-slate-100 py-4 pl-12 pr-12 focus:border-primary focus:outline-none focus:ring-0 text-sm tracking-wider uppercase rounded-sm transition-all placeholder:text-slate-500"
                                placeholder="BUSCAR CLIENTE POR NOMBRE O ID..."
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>

                        <div className="flex items-center gap-2 px-4 py-3 bg-slate-800 border border-slate-700 rounded-sm">
                            <span className="material-symbols-outlined text-slate-400">person</span>
                            <span className="text-xs font-bold uppercase text-slate-300 tracking-widest">
                                Operador: {user?.username || "ADMIN"}
                            </span>
                        </div>
                    </div>
                </header>

                <main className="flex-1 p-8 flex flex-col min-h-0 bg-[#0f1523]">
                    {/* Título Superior */}
                    <div className="flex items-center justify-between mb-8 shrink-0">
                        <div>
                            <h2 className="text-3xl font-black text-white tracking-tight flex items-center gap-3">
                                Gestión de Clientes
                                <span className="bg-slate-800 text-slate-400 text-xs px-2 py-1 rounded-sm border border-slate-700 font-bold uppercase tracking-widest">
                                    {meta?.count ?? 0} TOTAL
                                </span>
                            </h2>
                            <p className="text-slate-400 text-sm mt-1">Directorio principal de clientes, mayoristas y límites de crédito.</p>
                        </div>
                        <button
                            onClick={() => { setSelectedCustomerToEdit(null); setIsDrawerOpen(true); }}
                            className="bg-primary hover:bg-orange-600 text-white font-bold py-3 px-6 flex items-center gap-2 transition-colors rounded-sm shadow-lg shadow-primary/20"
                        >
                            <span className="material-symbols-outlined">person_add</span>
                            NUEVO CLIENTE
                        </button>
                    </div>

                    {/* Contenedor de Tabla */}
                    <div className="bg-slate-900 border border-slate-700 rounded-sm overflow-hidden flex-1 relative flex flex-col min-h-0 shadow-lg">
                        <div className="flex-1 overflow-auto w-full pb-14 custom-scrollbar">
                            <table className="w-full text-left text-sm text-slate-300 border-collapse">
                                <thead className="bg-[#0b1121] border-y border-slate-700 text-[10px] uppercase text-slate-500 font-bold tracking-[0.2em] sticky top-0 z-10 shadow-sm">
                                    <tr>
                                        <th scope="col" className="px-6 py-4 w-[10%]">ID</th>
                                        <th scope="col" className="px-6 py-4 w-[25%]">Nombre</th>
                                        <th scope="col" className="px-6 py-4 w-[20%]">Telefono</th>
                                        <th scope="col" className="px-6 py-4 w-[15%]">Dirección</th>
                                        <th scope="col" className="px-6 py-4 text-right w-[10%]">Límite</th>
                                        <th scope="col" className="px-6 py-4 text-right w-[10%]">Saldo Actual</th>
                                        <th scope="col" className="px-6 py-4 text-center w-[10%]">Acción</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {isLoading ? (
                                        <tr>
                                            <td colSpan={7} className="px-6 py-12 text-center text-slate-500 font-medium tracking-widest text-[11px]">
                                                <div className="flex items-center justify-center gap-3">
                                                    <span className="material-symbols-outlined animate-spin text-primary">progress_activity</span>
                                                    CARGANDO CLIENTES...
                                                </div>
                                            </td>
                                        </tr>
                                    ) : clientes.length === 0 ? (
                                        <tr>
                                            <td colSpan={7} className="px-6 py-8 text-center text-slate-500 font-medium">
                                                <div className="flex flex-col items-center justify-center gap-2">
                                                    <span className="material-symbols-outlined text-red-500/50 text-5xl">group_off</span>
                                                    <p className="text-[10px] uppercase font-bold tracking-[0.2em] mt-2">NO SE ENCONTRARON CLIENTES</p>
                                                </div>
                                            </td>
                                        </tr>
                                    ) : (
                                        clientes.map((cliente) => {
                                            const saldo = parseFloat(cliente.saldo_actual || "0");
                                            const limite = parseFloat(cliente.limite_credito || "0");
                                            const isOverLimit = saldo < 0 && Math.abs(saldo) > limite;

                                            // No badge needed, using direccion field instead

                                            return (
                                                <tr key={cliente.id} className="bg-slate-900 border-b border-slate-800/80 hover:bg-slate-800/50 transition-colors group">
                                                    <td className="px-6 py-4 font-mono text-primary font-bold">
                                                        {cliente.id}
                                                    </td>
                                                    <td className="px-6 py-4 text-slate-100 font-medium">
                                                        {cliente.nombre}
                                                    </td>
                                                    <td className="px-6 py-4 text-[10px] uppercase tracking-[0.1em]">
                                                        <div className="text-slate-300">{cliente.telefono || 'S/N'}</div>
                                                        <div className="text-slate-500 mt-1 truncate">{cliente.email || 'S/E'}</div>
                                                    </td>
                                                    <td className="px-6 py-4 text-slate-400 text-xs truncate max-w-[200px]">
                                                        {cliente.direccion || <span className="text-slate-600 italic">Sin dirección</span>}
                                                    </td>
                                                    <td className="px-6 py-4 text-right font-mono text-slate-300 text-sm">
                                                        {formatCurrency(limite)}
                                                    </td>
                                                    <td className={`px-6 py-4 text-right font-mono text-sm font-bold ${isOverLimit ? 'text-red-400' : (saldo < 0 ? 'text-orange-400' : 'text-slate-300')}`}>
                                                        {formatCurrency(saldo)}
                                                    </td>
                                                    <td className="px-6 py-4 text-center">
                                                        <button
                                                            onClick={() => { setSelectedCustomerToEdit(cliente); setIsDrawerOpen(true); }}
                                                            className="w-full flex items-center justify-center gap-2 bg-primary/10 text-primary border border-primary/30 hover:bg-primary hover:text-white hover:border-primary transition-all rounded-sm px-4 py-2 text-xs font-bold uppercase tracking-widest"
                                                        >
                                                            <span className="material-symbols-outlined text-[16px]">edit</span>
                                                            <span>Editar</span>
                                                        </button>
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    )}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination Footer - misma estructura que Products.tsx */}
                        {meta && (
                            <div className="absolute bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-700 px-6 py-3 flex items-center justify-between text-[10px] uppercase text-slate-500 font-bold tracking-[0.2em]">
                                <span>
                                    Mostrando página {meta.current_page} de {meta.total_pages} • {meta.count} totales
                                </span>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setCurrentPage(prev => prev - 1)}
                                        disabled={!meta.previous}
                                        className="p-1.5 border border-slate-700 rounded-sm text-slate-400 hover:text-white hover:border-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                    >
                                        <span className="material-symbols-outlined text-[16px]">chevron_left</span>
                                    </button>
                                    <button
                                        onClick={() => setCurrentPage(prev => prev + 1)}
                                        disabled={!meta.next}
                                        className="p-1.5 border border-slate-700 rounded-sm text-slate-400 hover:text-white hover:border-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                    >
                                        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </main>
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

            {/* Inyección del Drawer Dinámico (Crear / Editar) */}
            <CustomerDrawer
                isOpen={isDrawerOpen}
                onClose={() => {
                    setIsDrawerOpen(false);
                    setSelectedCustomerToEdit(null);
                }}
                onSave={handleSaveCustomer}
                initialData={selectedCustomerToEdit}
                isLoading={isSaving}
            />
        </div>
    );
};
