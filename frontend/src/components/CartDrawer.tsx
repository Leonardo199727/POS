import React, { useState, useContext } from 'react';
import { ClientSelectorDrawer, type ClienteCredito } from './ClientSelectorDrawer';
import { useCaja } from '../context/CajaContext';
import { AuthContext } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useRefresh } from '../context/RefreshContext';
import api from '../api/axios';
import { printTicket } from '../utils/printTicket';

interface CartDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    cartItems: any[];
    onUpdateQuantity: (variantId: number, delta: number) => void;
    onRemoveItem: (variantId: number) => void;
}

type CheckoutStep = 1 | 2 | 3;
type TipoVenta = 'CONTADO' | 'CREDITO' | null;
type MetodoPago = 'EFECTIVO' | 'TARJETA' | 'TRANSFERENCIA';

export const CartDrawer: React.FC<CartDrawerProps> = ({ isOpen, onClose, cartItems, onUpdateQuantity, onRemoveItem }) => {
    const { cajaAbierta, triggerCajaModal } = useCaja();
    const { user, token } = useContext(AuthContext);
    const { clearCart } = useCart();
    const { triggerRefresh } = useRefresh();
    const [step, setStep] = useState<CheckoutStep>(1);
    const [tipoVenta, setTipoVenta] = useState<TipoVenta>(null);
    const [metodoPago, setMetodoPago] = useState<MetodoPago>('EFECTIVO');
    const [aplicarComision, setAplicarComision] = useState(false);
    const [isClientSelectorOpen, setIsClientSelectorOpen] = useState(false);

    // API states
    const [isProcessing, setIsProcessing] = useState(false);
    const [processingStatus, setProcessingStatus] = useState('');
    const [saleError, setSaleError] = useState<string | null>(null);
    const [successFolio, setSuccessFolio] = useState<string | null>(null);
    const [successVentaId, setSuccessVentaId] = useState<number | null>(null);
    const [ticketPrinted, setTicketPrinted] = useState<boolean>(false);

    // Cálculos de totales — usar precio_credito cuando tipoVenta es CREDITO
    const getItemPrice = (item: any) => {
        if (tipoVenta === 'CREDITO') {
            return Number(item.variante.precio_credito || item.variante.precio_contado || 0);
        }
        return Number(item.variante.precio_contado || 0);
    };
    const subtotal = cartItems.reduce((acc, item) => acc + (getItemPrice(item) * item.cantidad), 0);
    const comision = (metodoPago === 'TARJETA' && aplicarComision) ? subtotal * 0.045 : 0;
    const totalFinal = subtotal + comision;

    const handleClose = () => {
        setStep(1);
        setTipoVenta(null);
        setMetodoPago('EFECTIVO');
        setAplicarComision(false);
        setSaleError(null);
        setSuccessFolio(null);
        setSuccessVentaId(null);
        setTicketPrinted(false);
        onClose();
    };

    const headers = { Authorization: `Token ${token}` };

    /**
     * Helper: crea la venta, agrega productos y finaliza.
     * Retorna la venta finalizada.
     */
    const crearYFinalizarVenta = async (
        tipo: 'contado' | 'credito',
        clienteId?: number,
        forceOverride?: boolean,
        authorizedBy?: number | null,
    ) => {
        // 1. Crear venta
        setProcessingStatus('Creando venta...');
        const crearRes = await api.post('ventas/', {
            tipo_venta: tipo,
            ...(clienteId ? { cliente_id: clienteId } : {}),
        }, { headers });
        const ventaId = crearRes.data.data.id;

        // 2. Agregar productos
        for (let i = 0; i < cartItems.length; i++) {
            const item = cartItems[i];
            setProcessingStatus(`Agregando producto ${i + 1}/${cartItems.length}...`);
            await api.post(`ventas/${ventaId}/agregar-producto/`, {
                variante_id: item.variante.id,
                cantidad: item.cantidad,
            }, { headers });
        }

        // 3. Finalizar
        setProcessingStatus('Finalizando venta...');
        const finalizarBody: any = {};
        if (forceOverride) {
            finalizarBody.force_credit_override = true;
            finalizarBody.authorized_by = authorizedBy;
        }
        const finRes = await api.post(`ventas/${ventaId}/finalizar/`, finalizarBody, { headers });
        return { ventaId, folio: finRes.data.data.folio };
    };

    /**
     * Venta de CONTADO completa.
     */
    const handleCheckout = async () => {
        if (isProcessing) return;
        setIsProcessing(true);
        setSaleError(null);

        try {
            const { ventaId, folio } = await crearYFinalizarVenta('contado');

            // 4. Registrar pago
            setProcessingStatus('Registrando pago...');
            const metodosPago = [{
                metodo: metodoPago,
                monto: subtotal.toFixed(2),
                con_intereses: metodoPago === 'TARJETA' && aplicarComision,
                porcentaje_interes: (metodoPago === 'TARJETA' && aplicarComision) ? '4.50' : null,
            }];
            await api.post('pagos/contado/', { venta_id: ventaId, metodos_pago: metodosPago }, { headers });

            // Éxito
            setSuccessFolio(folio);
            setSuccessVentaId(ventaId);
            clearCart();
            triggerRefresh();
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.response?.data?.error || err.message || 'Error al procesar la venta.';
            setSaleError(msg);
        } finally {
            setIsProcessing(false);
            setProcessingStatus('');
        }
    };

    /**
     * Venta a CRÉDITO completa (llamado desde ClientSelectorDrawer callback).
     */
    const handleCreditSale = async (
        cliente: ClienteCredito,
        adminAuthorizedId: number | null,
        pagoInicial?: { monto: number; metodo: string; conComision: boolean },
    ) => {
        if (isProcessing) return;
        setIsProcessing(true);
        setSaleError(null);
        setIsClientSelectorOpen(false);

        try {
            const forceOverride = adminAuthorizedId !== null;
            const { ventaId, folio } = await crearYFinalizarVenta(
                'credito',
                cliente.id,
                forceOverride,
                adminAuthorizedId,
            );

            // 4. Pago inicial (opcional)
            if (pagoInicial && pagoInicial.monto > 0) {
                setProcessingStatus('Registrando pago inicial...');
                const metodosPago = [{
                    metodo: pagoInicial.metodo,
                    monto: pagoInicial.monto.toFixed(2),
                    con_intereses: pagoInicial.conComision,
                    porcentaje_interes: pagoInicial.conComision ? '4.50' : null,
                }];
                await api.post('pagos/inicial/', { venta_id: ventaId, metodos_pago: metodosPago }, { headers });
            }

            // Éxito
            setSuccessFolio(folio);
            setSuccessVentaId(ventaId);
            clearCart();
            triggerRefresh();
        } catch (err: any) {
            const data = err.response?.data;
            let msg = 'Error al procesar la venta a crédito.';
            if (data) {
                if (typeof data.detail === 'string') msg = data.detail;
                else if (typeof data.error === 'string') msg = data.error;
                else if (typeof data === 'object') msg = Object.values(data).flat().join('. ');
            } else if (err.message) {
                msg = err.message;
            }
            setSaleError(msg);
        } finally {
            setIsProcessing(false);
            setProcessingStatus('');
        }
    };

    return (
        <>
            {/* Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity"
                    onClick={handleClose}
                />
            )}

            {/* Sliding Drawer */}
            <div
                className={`fixed top-0 right-0 h-full w-[450px] bg-slate-900 border-l border-slate-800 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
            >
                {/* Dynamic Header */}
                <header className="bg-slate-950 p-6 border-b border-slate-800 shrink-0 relative flex items-center justify-center">
                    {step > 1 && (
                        <button
                            onClick={() => setStep(prev => (prev - 1) as CheckoutStep)}
                            className="absolute left-6 text-slate-400 hover:text-white transition-colors flex items-center gap-1"
                            title="Regresar"
                        >
                            <span className="material-symbols-outlined text-xl">arrow_back</span>
                        </button>
                    )}

                    <div className="flex items-center gap-3">
                        {step === 1 && <span className="material-symbols-outlined text-primary">shopping_cart</span>}
                        <h2 className="text-white font-bold text-lg uppercase tracking-wider">
                            {step === 1 && "Carrito de Órdenes"}
                            {step === 2 && "Tipo de Venta"}
                            {step === 3 && "Método de Pago"}
                        </h2>
                    </div>

                    <button
                        onClick={handleClose}
                        className="absolute right-6 text-slate-500 hover:text-white transition-colors p-1"
                        title="Cerrar"
                    >
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </header>

                {/* Content Area */}
                <div className="flex-1 bg-[#0f1523] relative overflow-hidden">

                    {/* --- STEP 1: CART ITEMS --- */}
                    <div
                        className={`absolute inset-0 p-4 space-y-4 overflow-y-auto w-full transition-all duration-300 ease-in-out
                        ${step === 1 ? 'opacity-100 translate-x-0 z-10' : 'opacity-0 -translate-x-10 pointer-events-none z-0'}`}
                    >
                        {cartItems.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full text-slate-500 opacity-50 space-y-4">
                                <span className="material-symbols-outlined text-6xl">remove_shopping_cart</span>
                                <p className="text-sm font-bold uppercase tracking-widest">El carrito está vacío</p>
                            </div>
                        ) : (
                            cartItems.map((item) => {
                                const unitPrice = getItemPrice(item);
                                const lineTotal = unitPrice * item.cantidad;
                                const variantName = item.variante.nombre && item.variante.nombre !== 'Default' ? item.variante.nombre : null;
                                const displayName = variantName ? `${item.producto.nombre} - ${variantName}` : item.producto.nombre;

                                return (
                                    <div key={item.variante.id} className="bg-slate-900/50 p-4 border border-slate-800 rounded-sm flex flex-col gap-3 group relative overflow-hidden">
                                        {/* decorative line */}
                                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-slate-800 group-hover:bg-primary/50 transition-colors" />

                                        <div className="flex justify-between items-start pl-2">
                                            <div className="flex-1 pr-2">
                                                <h3 className="text-slate-200 font-bold leading-tight">{displayName}</h3>
                                                <p className="text-slate-500 text-xs font-mono mt-1">
                                                    SKU: {item.variante.sku || item.producto.codigo_interno}
                                                </p>
                                            </div>
                                            <button
                                                onClick={() => onRemoveItem(item.variante.id)}
                                                className="text-slate-600 hover:text-red-500 transition-colors p-1"
                                                title="Eliminar del carrito"
                                            >
                                                <span className="material-symbols-outlined text-[18px]">delete</span>
                                            </button>
                                        </div>
                                        <div className="flex items-center justify-between pl-2 mt-1">
                                            <div className="flex items-center bg-slate-950 border border-slate-800 rounded-sm">
                                                <button
                                                    onClick={() => onUpdateQuantity(item.variante.id, -1)}
                                                    disabled={item.cantidad <= 1}
                                                    className="px-3 py-1 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
                                                >
                                                    -
                                                </button>
                                                <span className="px-4 py-1 text-sm font-bold text-white font-mono min-w-[3rem] text-center">
                                                    {item.cantidad}
                                                </span>
                                                <button
                                                    onClick={() => onUpdateQuantity(item.variante.id, 1)}
                                                    disabled={item.cantidad >= item.variante.stock_actual}
                                                    className="px-3 py-1 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
                                                >
                                                    +
                                                </button>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-0.5">
                                                    ${unitPrice.toFixed(2)} c/u
                                                </p>
                                                <p className="text-lg font-mono font-bold text-white">${lineTotal.toFixed(2)}</p>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>

                    {/* --- STEP 2: TIPO DE VENTA --- */}
                    <div
                        className={`absolute inset-0 p-4 space-y-4 overflow-y-auto w-full flex flex-col justify-center pb-10 transition-all duration-300 ease-in-out
                        ${step === 2 ? 'opacity-100 translate-x-0 z-10' : step < 2 ? 'opacity-0 translate-x-10 pointer-events-none z-0' : 'opacity-0 -translate-x-10 pointer-events-none z-0'}`}
                    >
                        <div className="flex flex-col gap-4">
                            <button
                                onClick={() => {
                                    setTipoVenta('CONTADO');
                                    setStep(3);
                                }}
                                className="group bg-slate-900 border border-slate-800 hover:border-primary p-6 rounded-md flex flex-col items-center gap-4 transition-all duration-300 hover:bg-slate-800/50 hover:shadow-[0_0_20px_rgba(249,115,22,0.15)] relative overflow-hidden"
                            >
                                <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                <div className="w-16 h-16 rounded-full border border-slate-700 bg-slate-950 flex items-center justify-center group-hover:border-primary/50 group-hover:text-primary text-slate-400 transition-colors">
                                    <span className="material-symbols-outlined text-3xl">payments</span>
                                </div>
                                <div className="text-center relative z-10">
                                    <h3 className="text-white font-bold tracking-widest text-lg bg-slate-950 px-3 py-1 rounded border border-slate-800">CONTADO</h3>
                                    <p className="text-slate-500 text-sm mt-3">Cobro inmediato en caja.</p>
                                </div>
                            </button>

                            <button
                                onClick={() => {
                                    setTipoVenta('CREDITO');
                                    setIsClientSelectorOpen(true);
                                }}
                                className="group bg-slate-900 border border-slate-800 hover:border-blue-500 p-6 rounded-md flex flex-col items-center gap-4 transition-all duration-300 hover:bg-slate-800/50 hover:shadow-[0_0_20px_rgba(59,130,246,0.15)] relative overflow-hidden"
                            >
                                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                <div className="w-16 h-16 rounded-full border border-slate-700 bg-slate-950 flex items-center justify-center group-hover:border-blue-500/50 group-hover:text-blue-400 text-slate-400 transition-colors">
                                    <span className="material-symbols-outlined text-3xl">account_box</span>
                                </div>
                                <div className="text-center relative z-10">
                                    <h3 className="text-white font-bold tracking-widest text-lg bg-slate-950 px-3 py-1 rounded border border-slate-800">CRÉDITO</h3>
                                    <p className="text-slate-500 text-sm mt-3">Asignar a deuda de cliente.</p>
                                </div>
                            </button>
                        </div>
                    </div>

                    {/* --- STEP 3: MÉTODO DE PAGO --- */}
                    <div
                        className={`absolute inset-0 p-4 space-y-4 overflow-y-auto w-full py-6 transition-all duration-300 ease-in-out
                        ${step === 3 ? 'opacity-100 translate-x-0 z-10' : 'opacity-0 translate-x-10 pointer-events-none z-0'}`}
                    >
                        <div className="flex flex-col gap-3">
                            {(['EFECTIVO', 'TARJETA', 'TRANSFERENCIA'] as MetodoPago[]).map((method) => {
                                const isSelected = metodoPago === method;
                                const icons: Record<MetodoPago, string> = {
                                    EFECTIVO: 'local_atm',
                                    TARJETA: 'credit_card',
                                    TRANSFERENCIA: 'account_balance'
                                };
                                return (
                                    <button
                                        key={method}
                                        onClick={() => setMetodoPago(method)}
                                        className={`p-4 border rounded-md flex items-center gap-4 transition-all
                                            ${isSelected
                                                ? 'bg-slate-900 border-primary shadow-[inset_4px_0_0_#f97316]'
                                                : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-600'
                                            }
                                        `}
                                    >
                                        <span className={`material-symbols-outlined ${isSelected ? 'text-primary' : 'text-slate-500'}`}>
                                            {icons[method]}
                                        </span>
                                        <span className={`font-bold tracking-widest ${isSelected ? 'text-white' : 'text-slate-400'}`}>
                                            {method}
                                        </span>
                                        {isSelected && (
                                            <span className="material-symbols-outlined text-primary ml-auto text-sm">check_circle</span>
                                        )}
                                    </button>
                                );
                            })}

                            <div className={`mt-4 transform transition-all duration-300 overflow-hidden ${metodoPago === 'TARJETA' ? 'max-h-24 opacity-100' : 'max-h-0 opacity-0'}`}>
                                <label className="bg-slate-900 border border-slate-800 px-4 py-3 rounded-md flex items-center justify-between cursor-pointer group hover:bg-slate-800/50">
                                    <div className="flex flex-col">
                                        <span className="text-slate-200 font-bold text-sm tracking-wide">Aplicar +4.5% de comisión</span>
                                        <span className="text-slate-500 text-xs mt-1">Cargo extra por terminal</span>
                                    </div>
                                    <div className="relative inline-flex items-center cursor-pointer">
                                        <input
                                            type="checkbox"
                                            className="sr-only peer"
                                            checked={aplicarComision}
                                            onChange={(e) => setAplicarComision(e.target.checked)}
                                        />
                                        <div className="w-11 h-6 bg-slate-950 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-300 peer-checked:after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border border-slate-700"></div>
                                    </div>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Fixed Footer */}
                <footer className="bg-slate-950 border-t border-slate-800 p-6 shrink-0 flex flex-col gap-4 relative z-10 shadow-[0_-10px_40px_rgba(0,0,0,0.5)]">
                    {/* Desglose cuando hay comisión */}
                    <div className={`flex flex-col gap-2 transition-all duration-300 overflow-hidden ${comision > 0 ? 'max-h-20 opacity-100 mb-2' : 'max-h-0 opacity-0'}`}>
                        <div className="flex justify-between items-center">
                            <span className="text-slate-500 text-sm">Subtotal</span>
                            <span className="text-slate-400 font-mono text-sm">${subtotal.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-primary text-sm font-bold">Comisión (4.5%)</span>
                            <span className="text-primary font-mono text-sm font-bold">${comision.toFixed(2)}</span>
                        </div>
                        <div className="border-t border-slate-800"></div>
                    </div>

                    <div className="flex justify-between items-end">
                        <span className="text-slate-400 font-bold text-sm uppercase tracking-wider">Total a Pagar</span>
                        <span className="text-primary font-bold text-3xl font-mono">${totalFinal.toFixed(2)}</span>
                    </div>

                    {step === 1 && (
                        <>
                            {!cajaAbierta && (
                                <button
                                    onClick={triggerCajaModal}
                                    className="w-full bg-red-500/10 border border-red-500/30 rounded-sm px-3 py-2 flex items-center gap-2 mb-2 hover:bg-red-500/20 transition-colors cursor-pointer"
                                >
                                    <span className="material-symbols-outlined text-red-500 text-sm">warning</span>
                                    <span className="text-red-400 text-[10px] font-bold uppercase tracking-widest">Abra la caja para realizar ventas</span>
                                    <span className="material-symbols-outlined text-red-400 text-sm ml-auto">lock_open</span>
                                </button>
                            )}
                            <button
                                disabled={cartItems.length === 0 || !cajaAbierta}
                                onClick={() => setStep(2)}
                                className="w-full bg-primary hover:bg-[#ff8a33] text-white py-4 rounded-sm font-bold text-lg uppercase tracking-widest flex items-center justify-center gap-2 transition-colors shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary"
                            >
                                <span className="material-symbols-outlined">arrow_forward</span>
                                Continuar
                            </button>
                        </>
                    )}

                    {step === 2 && (
                        <div className="h-4 text-center text-xs text-slate-600 uppercase tracking-widest font-bold">
                            Seleccione el tipo de venta
                        </div>
                    )}

                    {step === 3 && (
                        <button
                            onClick={handleCheckout}
                            disabled={isProcessing}
                            className="w-full bg-primary hover:bg-[#ff8a33] text-white p-4 rounded-sm font-bold text-lg uppercase tracking-widest flex items-center justify-center gap-3 transition-colors shadow-[0_0_20px_rgba(249,115,22,0.3)] shadow-primary/20 hover:shadow-primary/40 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isProcessing ? (
                                <>
                                    <span className="material-symbols-outlined animate-spin">progress_activity</span>
                                    {processingStatus || 'Procesando...'}
                                </>
                            ) : (
                                <>
                                    <span className="material-symbols-outlined">payments</span>
                                    Concretar Venta
                                </>
                            )}
                        </button>
                    )}

                    {/* Error */}
                    {saleError && (
                        <div className="bg-red-500/10 border border-red-500/30 rounded-sm px-3 py-2 flex items-start gap-2">
                            <span className="material-symbols-outlined text-red-500 text-sm mt-0.5">error</span>
                            <div>
                                <span className="text-red-400 text-xs font-bold uppercase tracking-widest">Error</span>
                                <p className="text-red-300 text-xs mt-0.5">{saleError}</p>
                            </div>
                            <button onClick={() => setSaleError(null)} className="ml-auto text-red-500 hover:text-red-300">
                                <span className="material-symbols-outlined text-sm">close</span>
                            </button>
                        </div>
                    )}
                </footer>
            </div>

            {/* Client Selector Drawer (Step 4 for Credit) */}
            <ClientSelectorDrawer
                isOpen={isClientSelectorOpen}
                onClose={() => setIsClientSelectorOpen(false)}
                totalVenta={totalFinal}
                onConfirmCreditSale={(cliente, adminAuthorizedId, pagoInicial) => {
                    handleCreditSale(cliente, adminAuthorizedId, pagoInicial);
                }}
                userRol={user?.rol || null}
                userId={user?.id || null}
            />

            {/* Success Modal */}
            {successFolio && (
                <>
                    <div className="fixed inset-0 z-[110] bg-black/70 backdrop-blur-sm" />
                    <div className="fixed inset-0 z-[111] flex items-center justify-center">
                        <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl w-[400px] overflow-hidden">
                            <div className="p-8 text-center space-y-4">
                                <div className="w-20 h-20 mx-auto bg-emerald-500/10 border border-emerald-500/30 rounded-full flex items-center justify-center">
                                    <span className="material-symbols-outlined text-emerald-500 text-4xl">check_circle</span>
                                </div>
                                <div>
                                    <h3 className="text-white text-lg font-bold uppercase tracking-widest">¡Venta Exitosa!</h3>
                                    <p className="text-slate-400 text-sm mt-1">Folio: <span className="text-primary font-mono font-bold">{successFolio}</span></p>
                                </div>
                                <button
                                    onClick={() => {
                                        setSuccessFolio(null);
                                        setSuccessVentaId(null);
                                        handleClose();
                                    }}
                                    className="w-full bg-primary hover:bg-[#ff8a33] text-white py-3 rounded-sm font-bold text-sm uppercase tracking-widest transition-colors shadow-lg shadow-primary/20"
                                >
                                    Aceptar y Cerrar
                                </button>
                                {successVentaId && (
                                    <button
                                        onClick={() => {
                                            if (token) printTicket(successVentaId, token);
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
                                )}
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* Processing Overlay */}
            {isProcessing && (
                <div className="fixed inset-0 z-[105] bg-black/60 backdrop-blur-sm flex items-center justify-center">
                    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 flex flex-col items-center gap-4 shadow-2xl">
                        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
                        <p className="text-white text-sm font-bold uppercase tracking-widest">{processingStatus || 'Procesando...'}</p>
                    </div>
                </div>
            )}
        </>
    );
};
