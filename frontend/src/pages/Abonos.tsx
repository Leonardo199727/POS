import { useContext, useState, useEffect } from "react";
import { Sidebar } from "../components/Sidebar";
import { AuthContext } from "../context/AuthContext";
import { useRefresh } from "../context/RefreshContext";
import { useDebounce } from "../hooks/useDebounce";
import api from "../api/axios";
import { printAbonoTicket } from "../utils/printTicket";

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
}

interface Movimiento {
    id: string;
    fecha: string;
    concepto: string;
    monto: string;
    tipo: 'ABONO' | 'CARGO' | 'AJUSTE';
}


export const Abonos = () => {
    const { token, user } = useContext(AuthContext);
    const { refreshKey } = useRefresh();
    
    // UI State
    const [activeTab, setActiveTab] = useState<'ABONOS' | 'CARGOS'>('ABONOS');

    // Customer Data State
    const [clientes, setClientes] = useState<Cliente[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const debouncedSearchTerm = useDebounce(searchTerm, 500);
    const [selectedCliente, setSelectedCliente] = useState<Cliente | null>(null);

    // Movements State
    const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
    const [isLoadingMovs, setIsLoadingMovs] = useState(false);

    // Form State
    const [monto, setMonto] = useState<string>('');
    const [metodoPago, setMetodoPago] = useState<string>('Efectivo');
    const [aplicaComision, setAplicaComision] = useState<boolean>(false);
    const [concepto, setConcepto] = useState<string>('Ajuste de saldo (Corrección)');
    const [conceptoManual, setConceptoManual] = useState<string>('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { triggerRefresh } = useRefresh();

    // Success Modal State
    const [showSuccessModal, setShowSuccessModal] = useState(false);
    const [successData, setSuccessData] = useState<any>(null);
    const [ticketPrinted, setTicketPrinted] = useState(false);

    // Fetch Clientes Logic
    const fetchClientes = async (search: string = '') => {
        if (!token) return;
        setIsLoading(true);
        try {
            const queryParams = new URLSearchParams({ page: '1' });
            const trimmed = search.trim();
            const isNumeric = /^\d+$/.test(trimmed);
            if (trimmed.length > 0 && (isNumeric || trimmed.length >= 3)) {
                queryParams.append('search', trimmed);
            }
            // For Abonos/Cargos, we typically want *all* active customers or searching them directly
            const res = await api.get(`clientes/?${queryParams.toString()}`, {
                headers: { Authorization: `Token ${token}` }
            });
            if (res.data.success) {
                setClientes(res.data.data);
            }
        } catch (error) {
            console.error("Error fetching clientes:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleActionSubmit = async () => {
        if (!selectedCliente || !monto || parseFloat(monto) <= 0 || !token) return;
        setIsSubmitting(true);
        try {
            if (activeTab === 'ABONOS') {
                const isTarjeta = metodoPago === 'Tarjeta';
                const reqData = { 
                    metodos_pago: [{ 
                        metodo: metodoPago.toLowerCase(), 
                        monto: parseFloat(monto),
                        con_intereses: isTarjeta ? aplicaComision : false,
                        porcentaje_interes: (isTarjeta && aplicaComision) ? 4.5 : 0
                    }] 
                };
                const res = await api.post(`clientes/${selectedCliente.id}/abono/`, reqData, {
                    headers: { Authorization: `Token ${token}` }
                });
                const resData = res.data.data;
                setSuccessData({
                    tipo: 'ABONO' as const,
                    clienteNombre: selectedCliente.nombre,
                    cajero: user?.username || 'N/A',
                    folio: resData.folio,
                    metodoPago: metodoPago,
                    montoCliente: resData.monto_cliente,
                    cargoTarjeta: resData.cargo_tarjeta,
                    totalCobrado: resData.total_cobrado,
                    saldoAnterior: resData.saldo_anterior,
                    saldoNuevo: resData.saldo_nuevo,
                });
            } else {
                const finalConcepto = concepto === 'Otro motivo...' ? conceptoManual.trim() : concepto;
                const reqData = { monto: parseFloat(monto), concepto: finalConcepto };
                const res = await api.post(`clientes/${selectedCliente.id}/cargo/`, reqData, {
                    headers: { Authorization: `Token ${token}` }
                });
                const resData = res.data.data;
                setSuccessData({
                    tipo: 'CARGO' as const,
                    clienteNombre: selectedCliente.nombre,
                    cajero: user?.username || 'N/A',
                    concepto: resData.concepto,
                    montoCargo: resData.monto,
                    saldoAnterior: resData.saldo_anterior,
                    saldoNuevo: resData.saldo_nuevo,
                });
            }
            
            setShowSuccessModal(true);
            setTicketPrinted(false);
            setMonto('');
            triggerRefresh();
            fetchClientes(debouncedSearchTerm);
            setSelectedCliente(null);
            setConceptoManual('');
            
        } catch (error: any) {
            console.error('Error action:', error);
            const msg = error.response?.data?.detail || error.response?.data?.message || 'Error al procesar la operación.';
            alert(msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    useEffect(() => {
        fetchClientes(debouncedSearchTerm);
    }, [token, debouncedSearchTerm, refreshKey]);

    useEffect(() => {
        if (!selectedCliente || !token) {
            setMovimientos([]);
            return;
        }
        const fetchMovimientos = async () => {
            setIsLoadingMovs(true);
            try {
                const res = await api.get(`clientes/${selectedCliente.id}/movimientos/`, {
                    headers: { Authorization: `Token ${token}` }
                });
                if (res.data.success) {
                    setMovimientos(res.data.data);
                }
            } catch (error) {
                console.error("Error fetching movimientos:", error);
            } finally {
                setIsLoadingMovs(false);
            }
        };
        fetchMovimientos();
    }, [selectedCliente, token, refreshKey]);

    const formatCurrency = (amount: string | number) => {
        const val = typeof amount === 'string' ? parseFloat(amount) : amount;
        if (isNaN(val)) return '$0.00';
        return `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background-dark text-slate-100 font-display">
            <Sidebar />
            
            <main className="flex-1 flex flex-col overflow-hidden bg-[#0f1523]">
                {/* Top Header with Segmented Control */}
                <header className="flex items-center justify-between border-b border-slate-800 bg-[#0b1121]/50 px-8 py-3 shrink-0">
                    <div className="flex items-center gap-8">
                        <h1 className="text-2xl font-black uppercase tracking-tighter text-primary">Cargos y Abonos</h1>
                        
                        {/* Segmented Control */}
                        <div className="flex h-10 w-64 items-center rounded bg-slate-800 p-1 border border-slate-700">
                            <button 
                                onClick={() => setActiveTab('ABONOS')}
                                className={`flex-1 h-full rounded text-xs font-bold uppercase tracking-widest transition-all ${
                                    activeTab === 'ABONOS' 
                                    ? 'bg-primary text-white' 
                                    : 'text-slate-400 hover:text-slate-200'
                                }`}
                            >
                                Abonos
                            </button>
                            <button 
                                onClick={() => setActiveTab('CARGOS')}
                                className={`flex-1 h-full rounded text-xs font-bold uppercase tracking-widest transition-all ${
                                    activeTab === 'CARGOS' 
                                    ? 'bg-primary text-white' 
                                    : 'text-slate-400 hover:text-slate-200'
                                }`}
                            >
                                Cargos
                            </button>
                        </div>
                    </div>
                </header>

                <div className="flex flex-1 min-h-0 overflow-hidden">
                    {/* Left Panel: Customer List */}
                    <aside className="w-[350px] border-r border-slate-800 flex flex-col bg-slate-900/20 shrink-0">
                        <div className="p-6 border-b border-slate-800">
                            <div className="relative">
                                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-lg">person_search</span>
                                <input 
                                    className="w-full bg-slate-800/80 border border-slate-700 rounded py-3 pl-10 pr-4 text-sm focus:ring-1 focus:ring-blue-500 text-slate-100 placeholder:text-slate-500 transition-colors" 
                                    placeholder="Nombre o ID del cliente..." 
                                    type="text"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>
                        </div>
                        
                        <div className="flex-1 overflow-y-auto custom-scrollbar">
                            {isLoading && (
                                <div className="p-8 text-center text-slate-500">
                                    <span className="material-symbols-outlined animate-spin text-3xl mb-2">progress_activity</span>
                                    <p className="text-xs uppercase tracking-widest">Buscando...</p>
                                </div>
                            )}
                            
                            {!isLoading && clientes.length === 0 && (
                                <div className="p-8 text-center text-slate-500">
                                    <span className="material-symbols-outlined text-4xl mb-2 opacity-50">person_off</span>
                                    <p className="text-xs uppercase tracking-widest mt-2">{searchTerm ? 'No se encontraron clientes.' : 'Escriba para buscar clientes.'}</p>
                                </div>
                            )}

                            {!isLoading && clientes.map(cliente => {
                                const isSelected = selectedCliente?.id === cliente.id;
                                const pendingBalance = parseFloat(cliente.saldo_actual) || 0;

                                return (
                                    <div 
                                        key={cliente.id}
                                        onClick={() => setSelectedCliente(cliente)}
                                        className={`p-4 border-b border-slate-800 cursor-pointer group transition-all ${
                                            isSelected 
                                            ? 'bg-blue-900/10 border-l-4 border-l-blue-500 hover:bg-blue-900/20' 
                                            : 'hover:bg-slate-800/30'
                                        }`}
                                    >
                                        <div className="flex items-start gap-4">
                                            <div className={`size-10 rounded-full flex items-center justify-center shrink-0 transition-colors ${
                                                isSelected 
                                                ? 'bg-slate-800 border border-blue-500/30' 
                                                : 'bg-slate-800/50 border border-slate-700 group-hover:border-slate-500'
                                            }`}>
                                                <span className={`material-symbols-outlined text-xl ${
                                                    isSelected ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-400'
                                                }`}>
                                                    person
                                                </span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <h4 className={`font-bold text-sm uppercase truncate transition-colors ${
                                                    isSelected ? 'text-slate-100' : 'text-slate-400 group-hover:text-slate-200'
                                                }`}>
                                                    {cliente.nombre}
                                                </h4>
                                                <p className="text-slate-500 text-xs font-mono uppercase tracking-tight mt-0.5">
                                                    Límite: {formatCurrency(cliente.limite_credito)}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="mt-4 flex justify-between items-end">
                                            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Saldo Pendiente</span>
                                            <span className={`text-[11px] font-bold px-2 py-1 border font-mono tracking-wider transition-colors ${
                                                pendingBalance > 0
                                                ? (isSelected ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' : 'bg-slate-800 text-orange-500 border-slate-700 group-hover:bg-slate-700')
                                                : (isSelected ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' : 'bg-slate-800 text-slate-400 border-slate-700 group-hover:bg-slate-700')
                                            }`}>
                                                {formatCurrency(cliente.saldo_actual)}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </aside>

                    {/* Right Panel: Account Details & Action Form */}
                    <section className="flex-1 flex flex-col bg-[#0f1523]/60 overflow-hidden">
                        {!selectedCliente ? (
                            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-8">
                                <span className="material-symbols-outlined text-6xl mb-4 opacity-30">account_balance_wallet</span>
                                <h3 className="text-xl font-bold uppercase tracking-widest text-slate-400 mb-2">Ningún cliente seleccionado</h3>
                                <p className="text-sm text-center max-w-md">Seleccione un cliente de la lista de la izquierda para ver su estado de cuenta, historial de transacciones, y registrar cargos o abonos.</p>
                            </div>
                        ) : (
                            <>
                                {/* Selected Customer Header */}
                                <div className="p-6 border-b border-slate-800 flex justify-between items-end bg-slate-900/30 shrink-0">
                                    <div>
                                        <div className="flex items-center gap-2 text-blue-400 mb-2">
                                            <span className="material-symbols-outlined text-sm">account_balance_wallet</span>
                                            <span className="text-[10px] font-bold uppercase tracking-widest">Estado de Cuenta</span>
                                        </div>
                                        <h2 className={`font-black uppercase tracking-tighter text-white max-w-[600px] leading-none ${
                                            selectedCliente.nombre.length > 40 ? 'text-2xl line-clamp-2' 
                                            : selectedCliente.nombre.length > 25 ? 'text-3xl line-clamp-2' 
                                            : 'text-4xl truncate'
                                        }`}>
                                            {selectedCliente.nombre}
                                        </h2>
                                        <div className="flex gap-8 mt-4">
                                            <div>
                                                <p className="text-[10px] uppercase text-slate-500 font-bold tracking-widest mb-1">Límite de Crédito</p>
                                                <p className="text-xl font-mono text-slate-300">{formatCurrency(selectedCliente.limite_credito)}</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] uppercase text-slate-500 font-bold tracking-widest mb-1">Crédito Disponible</p>
                                                <p className="text-xl font-mono text-blue-400">
                                                    {formatCurrency(Math.max(0, parseFloat(selectedCliente.limite_credito) - parseFloat(selectedCliente.saldo_actual)))}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="text-right shrink-0">
                                        <p className="text-[10px] uppercase text-slate-500 font-bold tracking-widest mb-2">Saldo Actual Deudor</p>
                                        <p className={`text-5xl font-black font-mono tracking-tighter leading-none ${parseFloat(selectedCliente.saldo_actual) > 0 ? 'text-orange-500' : 'text-white'}`}>
                                            {formatCurrency(selectedCliente.saldo_actual)}
                                        </p>
                                    </div>
                                </div>

                        <div className="p-6 flex flex-col flex-1 min-h-0 gap-6">
                            {/* Action Card: Registar Abono OR Registar Cargo */}
                            <div className="bg-slate-900 border border-slate-800 p-6 shadow-2xl rounded-sm shrink-0">
                                <h3 className="text-sm font-black uppercase tracking-[0.2em] mb-6 flex items-center gap-3 text-slate-200">
                                    <span className="material-symbols-outlined text-primary">
                                        {activeTab === 'ABONOS' ? 'payments' : 'add_card'}
                                    </span>
                                    {activeTab === 'ABONOS' ? 'REGISTRAR ABONO' : 'REGISTRAR CARGO MANUAL'}
                                </h3>
                                
                                <div className="grid grid-cols-12 gap-6">
                                    {/* Amount Input */}
                                    <div className="col-span-12 lg:col-span-5 relative">
                                        <label className="block text-[10px] font-bold uppercase text-slate-500 tracking-widest mb-3">
                                            Monto {activeTab === 'ABONOS' ? 'del Abono' : 'del Cargo'} ($)
                                        </label>
                                        <div className="relative">
                                            <span className="absolute left-6 top-1/2 -translate-y-1/2 text-4xl font-black text-slate-600">$</span>
                                            <input 
                                                className={`w-full bg-[#0b1121] border-2 border-slate-800 focus:border-primary transition-colors text-5xl font-black text-white font-mono pl-14 pr-6 py-6 ring-0 focus:ring-0 rounded-sm outline-none ${isSubmitting ? 'opacity-50' : ''}`}
                                                type="number" 
                                                placeholder="0.00"
                                                step="0.01"
                                                value={monto}
                                                onChange={(e) => setMonto(e.target.value)}
                                                disabled={isSubmitting}
                                            />
                                        </div>
                                        {activeTab === 'CARGOS' && (
                                            <p className="text-[10px] text-slate-500 italic mt-3">* El cargo aumentará la deuda del cliente.</p>
                                        )}
                                    </div>

                                    {/* Concept / Methods */}
                                    <div className="col-span-12 lg:col-span-7 flex flex-col justify-between space-y-4 lg:space-y-0">
                                        
                                        {activeTab === 'ABONOS' ? (
                                            <div>
                                                <label className="block text-[10px] font-bold uppercase text-slate-500 tracking-widest mb-3">Método de Pago</label>
                                                <div className="flex gap-2">
                                                    {['Efectivo', 'Tarjeta', 'Transferencia'].map(method => (
                                                        <label key={method} className="flex-1 cursor-pointer group">
                                                            <input 
                                                                type="radio" 
                                                                name="payment-method" 
                                                                className="sr-only peer" 
                                                                checked={metodoPago === method} 
                                                                onChange={() => {
                                                                    setMetodoPago(method);
                                                                    if (method !== 'Tarjeta') setAplicaComision(false);
                                                                }}
                                                                disabled={isSubmitting}
                                                            />
                                                            <div className="h-16 flex items-center justify-center border-2 border-slate-800 bg-[#0b1121] peer-checked:border-primary peer-checked:bg-primary/20 peer-checked:text-primary text-slate-500 font-bold uppercase text-xs tracking-widest transition-all rounded-sm">
                                                                {method}
                                                            </div>
                                                        </label>
                                                    ))}
                                                </div>
                                                
                                                {metodoPago === 'Tarjeta' && (
                                                    <div className="mt-4 p-4 border border-blue-500/30 bg-blue-950/20 rounded-sm">
                                                        <div className="flex items-center justify-between">
                                                            <div>
                                                                <p className="text-xs font-bold text-primary uppercase tracking-widest">Cobrar Comisión (4.5%)</p>
                                                                <p className="text-[10px] text-slate-500 mt-1 max-w-[200px]">Transfiere el costo de terminal al cliente.</p>
                                                            </div>
                                                            <label className="relative inline-flex items-center cursor-pointer">
                                                                <input 
                                                                    type="checkbox" 
                                                                    className="sr-only peer"
                                                                    checked={aplicaComision}
                                                                    onChange={(e) => setAplicaComision(e.target.checked)}
                                                                    disabled={isSubmitting || !monto || parseFloat(monto) <= 0}
                                                                />
                                                                <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                                                            </label>
                                                        </div>
                                                        
                                                        {aplicaComision && monto && parseFloat(monto) > 0 && (
                                                            <div className="mt-4 pt-4 border-t border-primary/20 flex justify-between items-center">
                                                                <span className="text-[10px] uppercase tracking-widest text-slate-400">Total a cobrar en terminal:</span>
                                                                <span className="text-xl font-black font-mono text-primary">
                                                                    {formatCurrency(parseFloat(monto) * 1.045)}
                                                                </span>
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div>
                                                <label className="block text-[10px] font-bold uppercase text-slate-500 tracking-widest mb-3">Concepto / Motivo</label>
                                                <select 
                                                    className="w-full h-16 bg-[#0b1121] border-2 border-slate-800 rounded-sm px-4 text-slate-200 font-bold uppercase text-xs tracking-widest focus:border-primary outline-none appearance-none cursor-pointer"
                                                    value={concepto}
                                                    onChange={(e) => setConcepto(e.target.value)}
                                                    disabled={isSubmitting}
                                                >
                                                    <option value="Ajuste de saldo (Corrección)">Ajuste de saldo (Corrección)</option>
                                                    <option value="Penalización por pago tardío">Penalización por pago tardío</option>
                                                    <option value="Cheque Devuelto">Cheque Devuelto</option>
                                                    <option value="Otro motivo...">Otro motivo...</option>
                                                </select>
                                                
                                                {concepto === 'Otro motivo...' && (
                                                    <div className="mt-4">
                                                        <label className="block text-[10px] font-bold uppercase text-primary tracking-widest mb-2">Especificar Motivo *</label>
                                                        <input 
                                                            type="text" 
                                                            value={conceptoManual}
                                                            onChange={(e) => setConceptoManual(e.target.value)}
                                                            placeholder="Escriba la razón del cargo..."
                                                            className="w-full bg-[#0f1523] border border-blue-500/30 rounded px-4 py-3 text-sm focus:ring-1 focus:ring-primary focus:border-primary outline-none text-slate-200 placeholder:text-slate-600 transition-colors"
                                                            disabled={isSubmitting}
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        <button 
                                            onClick={handleActionSubmit}
                                            disabled={
                                                isSubmitting || 
                                                !monto || 
                                                parseFloat(monto) <= 0 || 
                                                (activeTab === 'CARGOS' && concepto === 'Otro motivo...' && !conceptoManual.trim())
                                            }
                                            className={`w-full h-16 text-white font-black uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 text-sm rounded-sm bg-primary hover:bg-orange-600 shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed`}
                                        >
                                            <span className="material-symbols-outlined">
                                                {isSubmitting ? 'progress_activity' : (activeTab === 'ABONOS' ? 'task_alt' : 'note_add')}
                                            </span>
                                            {isSubmitting ? 'PROCESANDO...' : (activeTab === 'ABONOS' ? 'Procesar Abono' : 'Aplicar Cargo')}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Movement History Table */}
                            <div className="flex flex-col flex-1 min-h-0 min-h-[200px]">
                                <div className="flex items-center justify-between mb-4 shrink-0">
                                    <h4 className="text-white font-bold uppercase tracking-widest text-xs flex items-center gap-2">
                                        <span className="material-symbols-outlined text-sm text-slate-500">history</span>
                                        Historial de Movimientos Recientes
                                    </h4>
                                </div>
                                
                                <div className="border border-slate-800 bg-slate-900/40 rounded-sm overflow-x-hidden overflow-y-auto custom-scrollbar flex-1">
                                    <table className="w-full text-left font-mono text-sm">
                                        <thead className="sticky top-0 z-10">
                                            <tr className="border-b border-slate-800 bg-[#0b1121]">
                                                <th className="px-6 py-4 font-bold uppercase text-[10px] text-slate-500 tracking-widest">Fecha</th>
                                                <th className="px-6 py-4 font-bold uppercase text-[10px] text-slate-500 tracking-widest">Concepto</th>
                                                <th className="px-6 py-4 font-bold uppercase text-[10px] text-slate-500 tracking-widest text-right">Monto</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-800/50">
                                            {isLoadingMovs ? (
                                                <tr>
                                                    <td colSpan={3} className="px-6 py-8 text-center text-slate-500">
                                                        <span className="material-symbols-outlined animate-spin text-2xl mb-2">progress_activity</span>
                                                        <p className="text-xs uppercase tracking-widest">Cargando movimientos...</p>
                                                    </td>
                                                </tr>
                                            ) : movimientos.length === 0 ? (
                                                <tr>
                                                    <td colSpan={3} className="px-6 py-8 text-center text-slate-500">
                                                        <p className="text-xs uppercase tracking-widest">No hay movimientos registrados.</p>
                                                    </td>
                                                </tr>
                                            ) : (
                                                movimientos.map((mov) => {
                                                    const dateObj = new Date(mov.fecha);
                                                    const formattedDate = dateObj.toLocaleDateString('es-MX', {
                                                        day: '2-digit', month: '2-digit', year: 'numeric'
                                                    }) + ' ' + dateObj.toLocaleTimeString('es-MX', {
                                                        hour: '2-digit', minute: '2-digit'
                                                    });

                                                    const isAbono = mov.tipo === 'ABONO';
                                                    
                                                    return (
                                                        <tr key={mov.id} className="hover:bg-slate-800/20 transition-colors">
                                                            <td className="px-6 py-4 text-slate-400">{formattedDate}</td>
                                                            <td className="px-6 py-4 text-slate-300 flex items-center gap-2">
                                                                {mov.concepto}
                                                                <span className={`text-[9px] px-2 py-0.5 rounded font-sans tracking-widest border ${
                                                                    isAbono 
                                                                        ? 'bg-orange-500/20 text-primary border-primary/30' 
                                                                        : mov.tipo === 'AJUSTE'
                                                                            ? 'bg-purple-900/30 text-purple-400 border-purple-500/20'
                                                                            : 'bg-slate-800 text-slate-400 border-slate-700'
                                                                }`}>
                                                                    {mov.tipo}
                                                                </span>
                                                            </td>
                                                            <td className={`px-6 py-4 text-right font-bold ${isAbono ? 'text-primary' : 'text-slate-200'}`}>
                                                                {formatCurrency(mov.monto)}
                                                            </td>
                                                        </tr>
                                                    );
                                                })
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </>
                    )}
                    </section>
                </div>

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
                            {new Date().toLocaleDateString('es-ES')} | {new Date().toLocaleTimeString('es-ES')}
                        </div>
                    </div>
                </footer>
            </main>

            {/* Success Modal Overlay */}
            {showSuccessModal && successData && (
                <div className="fixed inset-0 z-[110] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-slate-900 border border-slate-700 rounded-sm shadow-2xl w-full max-w-md overflow-hidden">
                        {/* Header */}
                        <div className="bg-green-900/30 border-b border-green-500/20 px-6 py-5 text-center">
                            <span className="material-symbols-outlined text-green-400 text-5xl">check_circle</span>
                            <h3 className="text-white text-lg font-bold uppercase tracking-widest mt-2">
                                {successData.tipo === 'ABONO' ? '¡Abono Registrado!' : '¡Cargo Aplicado!'}
                            </h3>
                            <p className="text-slate-400 text-xs mt-1">{successData.clienteNombre}</p>
                        </div>

                        {/* Summary */}
                        <div className="px-6 py-5 space-y-3">
                            {successData.tipo === 'ABONO' ? (
                                <>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-400">Folio</span>
                                        <span className="text-primary font-mono font-bold">{successData.folio}</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-400">Método</span>
                                        <span className="text-slate-200 font-bold">{successData.metodoPago}</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-400">Abono</span>
                                        <span className="text-slate-200 font-mono">{formatCurrency(successData.montoCliente)}</span>
                                    </div>
                                    {successData.cargoTarjeta > 0 && (
                                        <div className="flex justify-between text-sm">
                                            <span className="text-slate-400">Comisión T.C.</span>
                                            <span className="text-slate-200 font-mono">{formatCurrency(successData.cargoTarjeta)}</span>
                                        </div>
                                    )}
                                    <div className="flex justify-between text-sm border-t border-slate-800 pt-2">
                                        <span className="text-slate-300 font-bold">Total Cobrado</span>
                                        <span className="text-white font-mono font-bold">{formatCurrency(successData.totalCobrado)}</span>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-400">Concepto</span>
                                        <span className="text-slate-200 text-right max-w-[200px] truncate">{successData.concepto}</span>
                                    </div>
                                    <div className="flex justify-between text-sm border-t border-slate-800 pt-2">
                                        <span className="text-slate-300 font-bold">Monto del Cargo</span>
                                        <span className="text-white font-mono font-bold">{formatCurrency(successData.montoCargo)}</span>
                                    </div>
                                </>
                            )}
                            <div className="bg-slate-800/50 border border-slate-700 rounded-sm p-3 mt-3">
                                <div className="flex justify-between text-xs">
                                    <span className="text-slate-500 uppercase tracking-widest">Saldo Anterior</span>
                                    <span className="text-slate-400 font-mono">{formatCurrency(successData.saldoAnterior)}</span>
                                </div>
                                <div className="flex justify-between text-sm mt-2">
                                    <span className="text-slate-300 font-bold uppercase tracking-widest text-xs">Saldo Nuevo</span>
                                    <span className={`font-mono font-bold ${successData.saldoNuevo > 0 ? 'text-orange-400' : 'text-green-400'}`}>
                                        {formatCurrency(successData.saldoNuevo)}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="px-6 pb-6 space-y-3">
                            <button
                                onClick={() => {
                                    printAbonoTicket(successData);
                                    setTicketPrinted(true);
                                }}
                                className={`w-full border py-3 rounded-sm font-bold text-sm uppercase tracking-widest transition-colors flex items-center justify-center gap-2 ${
                                    ticketPrinted 
                                        ? 'bg-slate-800 border-slate-700 hover:bg-slate-700 text-slate-300 hover:text-white' 
                                        : 'bg-primary border-primary hover:bg-[#ff8a33] text-white shadow-lg shadow-primary/20'
                                }`}
                            >
                                <span className="material-symbols-outlined text-[18px]">local_printshop</span>
                                {ticketPrinted ? 'Reimprimir Ticket' : 'Imprimir Ticket'}
                            </button>
                            <button
                                onClick={() => {
                                    setShowSuccessModal(false);
                                    setSuccessData(null);
                                    setTicketPrinted(false);
                                }}
                                className="w-full bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 hover:text-white py-3 rounded-sm font-bold text-sm uppercase tracking-widest transition-colors"
                            >
                                Cerrar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Abonos;
