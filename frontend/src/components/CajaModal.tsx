import { useState } from "react";
import { useCaja } from "../context/CajaContext";

type Step = "ASK" | "AMOUNT";

export const CajaModal = () => {
    const { showCajaModal, abrirCaja, dismissModal } = useCaja();
    const [step, setStep] = useState<Step>("ASK");
    const [montoInicial, setMontoInicial] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    if (!showCajaModal) return null;

    const handleAbrirCaja = async () => {
        const monto = parseFloat(montoInicial);
        if (isNaN(monto) || monto < 0) {
            alert("Ingrese un monto válido (mayor o igual a 0).");
            return;
        }
        setIsSubmitting(true);
        await abrirCaja(monto);
        setIsSubmitting(false);
        // Reset for next time
        setStep("ASK");
        setMontoInicial("");
    };

    const handleDismiss = () => {
        dismissModal();
        setStep("ASK");
        setMontoInicial("");
    };

    return (
        <>
            {/* Backdrop */}
            <div className="fixed inset-0 z-[60] bg-background-dark/80 backdrop-blur-sm" />

            {/* Modal */}
            <div className="fixed inset-0 z-[61] flex items-center justify-center p-4">
                <div className="bg-slate-900 border border-slate-700 shadow-2xl rounded-sm w-full max-w-md overflow-hidden">
                    {/* Header */}
                    <div className="px-6 py-5 bg-slate-950 border-b border-slate-800 flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary text-2xl">point_of_sale</span>
                        <div>
                            <h3 className="text-lg font-bold text-slate-100 uppercase tracking-wider">
                                {step === "ASK" ? "Apertura de Caja" : "Monto Inicial"}
                            </h3>
                            <p className="text-[10px] text-slate-500 font-mono mt-0.5 uppercase tracking-widest">
                                {step === "ASK" ? "INICIO DE TURNO" : "CONFIGURE EL FONDO DE CAJA"}
                            </p>
                        </div>
                    </div>

                    {/* Body */}
                    <div className="p-6">
                        {step === "ASK" ? (
                            <div className="text-center space-y-6">
                                <div className="w-16 h-16 mx-auto bg-primary/10 border border-primary/30 rounded-full flex items-center justify-center">
                                    <span className="material-symbols-outlined text-primary text-3xl">storefront</span>
                                </div>
                                <div>
                                    <p className="text-slate-200 text-sm font-medium">
                                        No tiene una caja abierta en este momento.
                                    </p>
                                    <p className="text-slate-500 text-xs mt-2">
                                        Para registrar ventas es necesario abrir la caja primero.
                                    </p>
                                </div>
                                <div className="flex gap-3">
                                    <button
                                        onClick={handleDismiss}
                                        className="flex-1 py-3 border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500 font-bold text-xs uppercase tracking-widest transition-colors rounded-sm"
                                    >
                                        Ahora no
                                    </button>
                                    <button
                                        onClick={() => setStep("AMOUNT")}
                                        className="flex-1 py-3 bg-primary hover:bg-[#ff8a33] text-white font-bold text-xs uppercase tracking-widest transition-colors rounded-sm shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                                    >
                                        <span className="material-symbols-outlined text-[16px]">lock_open</span>
                                        Sí, abrir caja
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-6">
                                <div className="text-center">
                                    <p className="text-slate-300 text-sm">
                                        ¿Con cuánto efectivo inicia el turno?
                                    </p>
                                    <p className="text-slate-500 text-[10px] mt-1 uppercase tracking-widest">
                                        Puede ser $0.00 si no hay fondo
                                    </p>
                                </div>

                                {/* Money Input */}
                                <div className="relative">
                                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-xl font-bold">$</span>
                                    <input
                                        autoFocus
                                        type="number"
                                        min="0"
                                        step="0.01"
                                        placeholder="0.00"
                                        value={montoInicial}
                                        onChange={(e) => setMontoInicial(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter") handleAbrirCaja();
                                        }}
                                        className="w-full bg-slate-800 border border-slate-700 text-slate-100 py-4 pl-10 pr-4 text-2xl font-mono text-center focus:border-primary focus:outline-none focus:ring-0 rounded-sm transition-all tracking-wider"
                                    />
                                </div>

                                <div className="flex gap-3">
                                    <button
                                        onClick={() => setStep("ASK")}
                                        className="flex-1 py-3 border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500 font-bold text-xs uppercase tracking-widest transition-colors rounded-sm"
                                    >
                                        Regresar
                                    </button>
                                    <button
                                        onClick={handleAbrirCaja}
                                        disabled={isSubmitting}
                                        className="flex-1 py-3 bg-primary hover:bg-[#ff8a33] text-white font-bold text-xs uppercase tracking-widest transition-colors rounded-sm shadow-lg shadow-primary/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {isSubmitting ? (
                                            <>
                                                <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
                                                Abriendo...
                                            </>
                                        ) : (
                                            <>
                                                <span className="material-symbols-outlined text-[16px]">point_of_sale</span>
                                                Abrir Caja
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
};
