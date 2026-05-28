import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { AdminAuthModal } from './AdminAuthModal';
import api from '../api/axios';
import { useDebounce } from '../hooks/useDebounce';

// Misma interfaz que Customers.tsx (los campos numéricos llegan como string del serializer)
export interface ClienteCredito {
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

type MetodoPagoInicial = 'EFECTIVO' | 'TARJETA' | 'TRANSFERENCIA';

interface ClientSelectorDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    totalVenta: number;
    onConfirmCreditSale: (
        cliente: ClienteCredito,
        adminAuthorizedId: number | null,
        pagoInicial?: { monto: number; metodo: string; conComision: boolean },
    ) => void;
    userRol: string | null;
    userId: number | null;
}

export const ClientSelectorDrawer: React.FC<ClientSelectorDrawerProps> = ({
    isOpen,
    onClose,
    totalVenta,
    onConfirmCreditSale,
    userRol,
    userId,
}) => {
    const { token } = useContext(AuthContext);
    const [searchTerm, setSearchTerm] = useState('');
    const debouncedSearch = useDebounce(searchTerm, 500);
    const [clientes, setClientes] = useState<ClienteCredito[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedClientId, setSelectedClientId] = useState<number | null>(null);

    // Pago inicial opcional
    const [pagoInicialActivo, setPagoInicialActivo] = useState(false);
    const [montoPagoInicial, setMontoPagoInicial] = useState('');
    const [metodoPagoInicial, setMetodoPagoInicial] = useState<MetodoPagoInicial>('EFECTIVO');
    const [comisionTarjeta, setComisionTarjeta] = useState(false);

    // Modales de autorización
    const [showAdminAuth, setShowAdminAuth] = useState(false);
    const [showConfirmLimitModal, setShowConfirmLimitModal] = useState(false);
    const [adminAuthorizedId, setAdminAuthorizedId] = useState<number | null>(null);

    // Fetch clientes — misma lógica que Customers.tsx
    const fetchClientes = async (search: string = '') => {
        if (!token) return;
        setIsLoading(true);
        try {
            const queryParams = new URLSearchParams();
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
            }
        } catch (error) {
            console.error('Error fetching clientes:', error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            fetchClientes(debouncedSearch);
        }
    }, [isOpen, debouncedSearch]);

    // Reset state al cerrar
    useEffect(() => {
        if (!isOpen) {
            setSearchTerm('');
            setSelectedClientId(null);
            setPagoInicialActivo(false);
            setMontoPagoInicial('');
            setMetodoPagoInicial('EFECTIVO');
            setComisionTarjeta(false);
            setShowAdminAuth(false);
            setShowConfirmLimitModal(false);
            setAdminAuthorizedId(null);
        }
    }, [isOpen]);

    const selectedClient = clientes.find(c => c.id === selectedClientId);

    // Parsear valores numéricos desde strings del serializer
    const saldoActual = selectedClient ? parseFloat(selectedClient.saldo_actual || '0') : 0;
    const limiteCredito = selectedClient ? parseFloat(selectedClient.limite_credito || '0') : 0;

    // Cálculos de pago inicial
    const pagoInicialNum = pagoInicialActivo ? Math.min(parseFloat(montoPagoInicial) || 0, totalVenta) : 0;
    const comisionPagoInicial = (metodoPagoInicial === 'TARJETA' && comisionTarjeta && pagoInicialNum > 0)
        ? pagoInicialNum * 0.045
        : 0;
    const montoACredito = totalVenta - pagoInicialNum;

    // Validación de crédito: nuevo saldo = saldo_actual + lo que va a crédito
    const nuevoSaldo = saldoActual + montoACredito;
    const isExceedingLimit = selectedClient ? nuevoSaldo > limiteCredito : false;

    // Si el admin ya autorizó el override, permitir proceder
    const creditOverrideAuthorized = adminAuthorizedId !== null;

    const handleConfirmClick = () => {
        if (!selectedClient) return;

        if (isExceedingLimit && !creditOverrideAuthorized) {
            // Flujo de autorización
            if (userRol === 'ADMIN') {
                // El admin actual puede autorizar directamente
                setShowConfirmLimitModal(true);
            } else {
                // Vendedor: pedir credenciales de un admin
                setShowAdminAuth(true);
            }
            return;
        }

        // Proceder con la venta
        const pagoInicialData = pagoInicialActivo && pagoInicialNum > 0
            ? { monto: pagoInicialNum, metodo: metodoPagoInicial, conComision: comisionTarjeta && metodoPagoInicial === 'TARJETA' }
            : undefined;
        onConfirmCreditSale(selectedClient, adminAuthorizedId, pagoInicialData);
    };

    const handleAdminAuthorized = (adminId: number) => {
        setShowAdminAuth(false);
        setAdminAuthorizedId(adminId);
        // Mostrar confirmación de aumento de límite
        setShowConfirmLimitModal(true);
    };

    const handleConfirmLimitIncrease = () => {
        if (!selectedClient) return;
        setShowConfirmLimitModal(false);

        // El admin (ya sea el logueado o el que autorizó) confirma
        const authId = adminAuthorizedId || userId;
        if (authId) {
            setAdminAuthorizedId(authId);
        }

        // Proceder con la venta (el CartDrawer o el componente padre se encargará de enviar force_credit_override)
        const pagoInicialData = pagoInicialActivo && pagoInicialNum > 0
            ? { monto: pagoInicialNum, metodo: metodoPagoInicial, conComision: comisionTarjeta && metodoPagoInicial === 'TARJETA' }
            : undefined;
        onConfirmCreditSale(selectedClient, authId, pagoInicialData);
    };

    const handleRejectLimitIncrease = () => {
        // El admin dice que NO: venta bloqueada
        setShowConfirmLimitModal(false);
        setAdminAuthorizedId(null);
    };

    return (
        <>
            {/* Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[60] transition-opacity"
                    onClick={onClose}
                />
            )}

            {/* Sliding Drawer */}
            <div
                className={`fixed top-0 right-0 h-full w-[450px] bg-background-dark border-l border-slate-800 shadow-2xl z-[70] transform transition-transform duration-300 ease-in-out flex flex-col ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
            >
                {/* Header */}
                <header className="flex items-center justify-between px-4 py-4 bg-slate-950 border-b border-slate-800 shrink-0">
                    <button onClick={onClose} className="flex items-center justify-center text-slate-100 hover:text-primary transition-colors">
                        <span className="material-symbols-outlined">arrow_back</span>
                    </button>
                    <h1 className="text-white text-sm font-bold tracking-widest uppercase">Selección de Cliente</h1>
                    <button onClick={onClose} className="flex items-center justify-center text-slate-100 hover:text-primary transition-colors">
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </header>

                <main className="flex-1 flex flex-col overflow-hidden bg-[#0f1523]">
                    {/* Search Bar */}
                    <div className="px-4 py-4 bg-slate-950/20">
                        <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <span className="material-symbols-outlined text-slate-400 group-focus-within:text-primary transition-colors">search</span>
                            </div>
                            <input
                                className="block w-full pl-10 pr-3 py-3 bg-slate-950 border border-slate-800 rounded text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary text-sm"
                                placeholder="Buscar por nombre, teléfono o email..."
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                    </div>

                    {/* Client List */}
                    <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3 custom-scrollbar">
                        {isLoading ? (
                            <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-3">
                                <span className="material-symbols-outlined animate-spin text-primary text-3xl">progress_activity</span>
                                <p className="text-[10px] font-bold uppercase tracking-[0.2em]">Cargando clientes...</p>
                            </div>
                        ) : clientes.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-3">
                                <span className="material-symbols-outlined text-5xl text-slate-600">group_off</span>
                                <p className="text-[10px] font-bold uppercase tracking-[0.2em]">No se encontraron clientes</p>
                            </div>
                        ) : (
                            clientes.map(client => {
                                const isSelected = selectedClientId === client.id;
                                const saldo = parseFloat(client.saldo_actual || '0');
                                const limite = parseFloat(client.limite_credito || '0');
                                const overLimit = limite > 0 && saldo >= limite;

                                return (
                                    <div
                                        key={client.id}
                                        onClick={() => setSelectedClientId(client.id)}
                                        className={`p-4 rounded-lg cursor-pointer transition-all border ${isSelected
                                                ? 'bg-slate-800/50 border-primary shadow-[0_0_15px_rgba(249,116,21,0.15)]'
                                                : 'bg-slate-900 border-slate-800 hover:border-slate-600 opacity-90 hover:opacity-100'
                                            }`}
                                    >
                                        <div className="flex justify-between items-start">
                                            <div className="space-y-1">
                                                <h3 className="text-white font-bold text-lg flex items-center gap-2">
                                                    {client.nombre}
                                                    <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">ID: {client.id}</span>
                                                </h3>
                                                <p className="text-slate-400 text-sm flex items-center gap-1">
                                                    <span className="material-symbols-outlined text-xs">call</span>
                                                    {client.telefono || 'S/N'}
                                                </p>
                                                <div className="pt-2">
                                                    <p className={`text-xs font-medium uppercase tracking-wider ${overLimit ? 'text-red-500' : (saldo > 0 ? 'text-slate-300' : 'text-slate-500')}`}>
                                                        Saldo: ${saldo.toLocaleString('en-US', { minimumFractionDigits: 2 })} | Límite: ${limite.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className={isSelected ? 'text-primary' : 'text-slate-700'}>
                                                <span className="material-symbols-outlined text-3xl">
                                                    {isSelected ? 'check_circle' : 'radio_button_unchecked'}
                                                </span>
                                            </div>
                                        </div>

                                        {/* Status Badges */}
                                        <div className="mt-3 flex gap-2">
                                            {client.tipo_cliente === 'mayorista' && (
                                                <span className="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-bold rounded border border-primary/20 uppercase">
                                                    Mayorista
                                                </span>
                                            )}
                                            {overLimit ? (
                                                <span className="px-2 py-0.5 bg-red-500/10 text-red-500 text-[10px] font-bold rounded border border-red-500/20 uppercase">
                                                    Excede Límite
                                                </span>
                                            ) : saldo === 0 ? (
                                                <span className="px-2 py-0.5 bg-slate-500/10 text-slate-400 text-[10px] font-bold rounded border border-slate-500/20 uppercase">
                                                    Sin Deuda
                                                </span>
                                            ) : (
                                                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-[10px] font-bold rounded border border-emerald-500/20 uppercase">
                                                    Al Corriente
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>

                    {/* Pago Inicial (Opcional) — visible solo cuando hay un cliente seleccionado */}
                    {selectedClient && (
                        <div className="px-4 py-3 border-t border-slate-800 bg-slate-950/40">
                            {/* Toggle */}
                            <button
                                onClick={() => {
                                    setPagoInicialActivo(!pagoInicialActivo);
                                    if (pagoInicialActivo) {
                                        setMontoPagoInicial('');
                                        setComisionTarjeta(false);
                                    }
                                }}
                                className="w-full flex items-center justify-between py-2 text-slate-300 hover:text-primary transition-colors"
                            >
                                <span className="text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                                    <span className="material-symbols-outlined text-sm">
                                        {pagoInicialActivo ? 'expand_less' : 'expand_more'}
                                    </span>
                                    Pago Inicial (Opcional)
                                </span>
                                <span className={`w-9 h-5 rounded-full transition-colors relative ${pagoInicialActivo ? 'bg-primary' : 'bg-slate-700'}`}>
                                    <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${pagoInicialActivo ? 'translate-x-4' : ''}`}></span>
                                </span>
                            </button>

                            {/* Contenido expandible */}
                            {pagoInicialActivo && (
                                <div className="mt-3 space-y-3 animate-in">
                                    {/* Monto */}
                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Monto</label>
                                        <div className="relative">
                                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-bold text-sm">$</span>
                                            <input
                                                type="number"
                                                step="0.01"
                                                min="0"
                                                max={totalVenta}
                                                value={montoPagoInicial}
                                                onChange={(e) => setMontoPagoInicial(e.target.value)}
                                                className={`w-full bg-slate-900 border text-slate-100 py-2.5 pl-7 pr-3 focus:outline-none focus:ring-0 text-sm font-mono rounded-sm transition-all placeholder:text-slate-600 ${
                                                    (parseFloat(montoPagoInicial) || 0) > totalVenta
                                                        ? 'border-amber-500 focus:border-amber-500'
                                                        : 'border-slate-700 focus:border-primary'
                                                }`}
                                                placeholder="0.00"
                                            />
                                        </div>
                                        {(parseFloat(montoPagoInicial) || 0) > totalVenta && (
                                            <div className="flex items-center gap-1.5 text-amber-400">
                                                <span className="material-symbols-outlined text-[12px]">info</span>
                                                <span className="text-[10px] font-bold uppercase tracking-widest">
                                                    Máximo: ${totalVenta.toFixed(2)} — se ajustará automáticamente
                                                </span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Método de Pago */}
                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Método de Pago</label>
                                        <div className="grid grid-cols-3 gap-2">
                                            {(['EFECTIVO', 'TARJETA', 'TRANSFERENCIA'] as const).map(metodo => (
                                                <button
                                                    key={metodo}
                                                    onClick={() => {
                                                        setMetodoPagoInicial(metodo);
                                                        if (metodo !== 'TARJETA') setComisionTarjeta(false);
                                                    }}
                                                    className={`py-2 px-1 rounded-sm text-[10px] font-bold uppercase tracking-wider transition-all border ${metodoPagoInicial === metodo
                                                            ? 'bg-primary/10 border-primary text-primary'
                                                            : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-500'
                                                        }`}
                                                >
                                                    {metodo}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Comisión Tarjeta */}
                                    {metodoPagoInicial === 'TARJETA' && (
                                        <div className="flex items-center justify-between py-1">
                                            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Comisión +4.5%</span>
                                            <button
                                                onClick={() => setComisionTarjeta(!comisionTarjeta)}
                                                className={`w-9 h-5 rounded-full transition-colors relative ${comisionTarjeta ? 'bg-primary' : 'bg-slate-700'}`}
                                            >
                                                <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${comisionTarjeta ? 'translate-x-4' : ''}`}></span>
                                            </button>
                                        </div>
                                    )}

                                    {/* Resumen del pago inicial */}
                                    {pagoInicialNum > 0 && (
                                        <div className="bg-slate-900/50 border border-slate-800 rounded px-3 py-2 space-y-1">
                                            <div className="flex justify-between text-[10px] uppercase tracking-widest">
                                                <span className="text-slate-500 font-bold">
                                                    {comisionPagoInicial > 0 ? 'Pago con comisión' : `Anticipo (${metodoPagoInicial})`}
                                                </span>
                                                <span className="text-slate-300 font-mono">
                                                    ${(pagoInicialNum + comisionPagoInicial).toFixed(2)}
                                                </span>
                                            </div>
                                            <div className="border-t border-slate-800 pt-1 flex justify-between text-[10px] uppercase tracking-widest">
                                                <span className="text-primary font-bold">Cargo a Crédito</span>
                                                <span className="text-primary font-mono font-bold">${montoACredito.toFixed(2)}</span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </main>

                {/* Footer */}
                <footer className="bg-slate-950 border-t border-slate-800 px-6 py-6 space-y-4 shrink-0 shadow-[0_-10px_40px_rgba(0,0,0,0.5)]">
                    <div className="flex justify-between items-end">
                        <div className="flex flex-col">
                            <span className="text-slate-400 text-xs uppercase tracking-widest font-bold">
                                {pagoInicialNum > 0 ? 'Cargo a Crédito' : 'Total de Venta'}
                            </span>
                            <span className="text-primary text-3xl font-bold">${montoACredito.toFixed(2)}</span>
                            {pagoInicialNum > 0 && (
                                <span className="text-slate-500 text-[10px] font-mono line-through">Total: ${totalVenta.toFixed(2)}</span>
                            )}
                        </div>
                        {selectedClient && (
                            <div className="text-right flex flex-col items-end">
                                <span className={`text-[10px] font-bold uppercase tracking-widest ${isExceedingLimit && !creditOverrideAuthorized ? 'text-red-500' : 'text-emerald-500'}`}>
                                    SALDO RESULTANTE ({selectedClient.nombre.split(' ')[0].toUpperCase()})
                                </span>
                                <span className={`text-lg font-mono font-bold ${isExceedingLimit && !creditOverrideAuthorized ? 'text-red-400' : 'text-white'}`}>
                                    ${nuevoSaldo.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                                </span>
                                <span className="text-[9px] text-slate-500 font-mono">
                                    Límite: ${limiteCredito.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Indicador de autorización */}
                    {creditOverrideAuthorized && isExceedingLimit && (
                        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-sm px-3 py-2 flex items-center gap-2">
                            <span className="material-symbols-outlined text-emerald-500 text-sm">verified</span>
                            <span className="text-emerald-400 text-[10px] font-bold uppercase tracking-widest">
                                Excedente autorizado — Límite será actualizado
                            </span>
                        </div>
                    )}

                    <button
                        disabled={!selectedClient}
                        onClick={handleConfirmClick}
                        className={`w-full font-bold py-4 rounded uppercase tracking-wider text-sm transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${isExceedingLimit && !creditOverrideAuthorized
                                ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-600/20'
                                : 'bg-primary hover:bg-[#ff8a33] text-white shadow-primary/20 disabled:hover:bg-primary'
                            }`}
                    >
                        {isExceedingLimit && !creditOverrideAuthorized ? (
                            <>
                                <span className="material-symbols-outlined">lock</span>
                                <span>Solicitar Autorización</span>
                            </>
                        ) : (
                            <>
                                <span>Confirmar Venta a Crédito</span>
                                <span className="material-symbols-outlined">payments</span>
                            </>
                        )}
                    </button>
                </footer>
            </div>

            {/* Admin Auth Modal */}
            <AdminAuthModal
                isOpen={showAdminAuth}
                onClose={() => setShowAdminAuth(false)}
                onAuthorized={handleAdminAuthorized}
                title="Autorización de Crédito"
                description="El cliente excede su límite. Ingrese las credenciales de un administrador."
            />

            {/* Confirm Limit Increase Modal */}
            {showConfirmLimitModal && selectedClient && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center">
                    <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={handleRejectLimitIncrease} />
                    <div className="relative bg-slate-950 border border-slate-800 rounded-lg shadow-2xl w-[420px] overflow-hidden">
                        <div className="px-6 py-5 border-b border-slate-800">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                                    <span className="material-symbols-outlined text-amber-500">trending_up</span>
                                </div>
                                <div>
                                    <h2 className="text-white font-bold text-sm uppercase tracking-widest">Aumentar Límite de Crédito</h2>
                                    <p className="text-slate-400 text-xs mt-0.5">El límite actual será insuficiente para esta venta.</p>
                                </div>
                            </div>
                        </div>
                        <div className="px-6 py-5 space-y-4">
                            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
                                <div className="flex justify-between text-xs uppercase tracking-widest">
                                    <span className="text-slate-500 font-bold">Cliente</span>
                                    <span className="text-white font-bold">{selectedClient.nombre}</span>
                                </div>
                                <div className="flex justify-between text-xs uppercase tracking-widest">
                                    <span className="text-slate-500 font-bold">Límite Actual</span>
                                    <span className="text-slate-300 font-mono">${limiteCredito.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-xs uppercase tracking-widest">
                                    <span className="text-slate-500 font-bold">Nuevo Límite</span>
                                    <span className="text-primary font-mono font-bold">${nuevoSaldo.toFixed(2)}</span>
                                </div>
                                <div className="border-t border-slate-800 pt-2 flex justify-between text-xs uppercase tracking-widest">
                                    <span className="text-slate-500 font-bold">Diferencia</span>
                                    <span className="text-amber-400 font-mono">+${(nuevoSaldo - limiteCredito).toFixed(2)}</span>
                                </div>
                            </div>
                            <p className="text-slate-400 text-xs text-center">
                                ¿Desea actualizar el límite de crédito para continuar con la venta?
                            </p>
                            <div className="flex gap-3">
                                <button
                                    onClick={handleRejectLimitIncrease}
                                    className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-3 rounded-sm text-xs uppercase tracking-widest transition-colors border border-slate-700"
                                >
                                    No, Cancelar
                                </button>
                                <button
                                    onClick={handleConfirmLimitIncrease}
                                    className="flex-1 bg-primary hover:bg-orange-600 text-white font-bold py-3 rounded-sm text-xs uppercase tracking-widest transition-colors shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                                >
                                    <span className="material-symbols-outlined text-sm">check</span>
                                    Sí, Aumentar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};
