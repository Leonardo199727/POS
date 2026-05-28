import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';

// Props para controlar el Drawer desde Customers.tsx
interface CustomerDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (customerData: any) => void;
    isLoading?: boolean;
    initialData?: any;
}

export const CustomerDrawer: React.FC<CustomerDrawerProps> = ({
    isOpen,
    onClose,
    onSave,
    isLoading = false,
    initialData = null
}) => {
    const { user } = useContext(AuthContext);
    const isAdmin = user?.rol === 'ADMIN';

    // Estado inicial del formulario (Basado en el Schema del Backend → Cliente model)
    const emptyForm = {
        nombre: '',
        direccion: '',
        telefono: '',
        email: '',
        limite_credito: ''
    };

    const [formData, setFormData] = useState(emptyForm);

    useEffect(() => {
        if (isOpen) {
            if (initialData) {
                // Modo Edición: Pre-poblar el formulario con los datos del cliente
                setFormData({
                    nombre: initialData.nombre || '',
                    direccion: initialData.direccion || '',
                    telefono: initialData.telefono || '',
                    email: initialData.email || '',
                    limite_credito: initialData.limite_credito?.toString() || ''
                });
            } else {
                // Modo Creación: Limpiar el formulario
                setFormData(emptyForm);
            }
        } else {
            setFormData(emptyForm);
        }
    }, [isOpen, initialData]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        const cleanData: any = { ...formData };

        // Limpiar campos vacíos
        Object.keys(cleanData).forEach(key => {
            if (cleanData[key] === '') {
                delete cleanData[key];
            }
        });

        if (initialData) {
            onSave({
                ...cleanData,
                isEdit: true,
                clienteId: initialData.id
            });
        } else {
            onSave(cleanData);
        }
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop / Overlay oscuro y blur */}
            <div
                className="fixed inset-0 bg-[#0b1121]/80 backdrop-blur-sm z-40 flex items-center justify-center transition-opacity"
                onClick={onClose}
            ></div>

            {/* Customer Drawer Container */}
            <div
                className="fixed inset-y-0 right-0 w-full max-w-[450px] bg-[#0f1523] border-l border-slate-700 shadow-2xl z-50 flex flex-col transform transition-transform duration-300 translate-x-0"
            >
                <form onSubmit={handleSubmit} className="flex flex-col h-full">

                    {/* Header */}
                    <header className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between shrink-0">
                        <div className="flex items-center gap-3">
                            <span className="material-symbols-outlined text-primary text-2xl">
                                {initialData ? 'edit_square' : 'person_add'}
                            </span>
                            <div>
                                <h2 className="text-slate-100 text-lg font-bold tracking-tight uppercase">
                                    {initialData ? 'Editar Cliente' : 'Nuevo Cliente'}
                                </h2>
                                <p className="text-[10px] uppercase font-mono tracking-[0.2em] text-slate-500">
                                    {initialData
                                        ? `ID: ${initialData.id}`
                                        : 'REGISTRO NUEVO'}
                                </p>
                            </div>
                        </div>
                        <button
                            type="button"
                            onClick={onClose}
                            className="text-slate-400 hover:text-white transition-colors"
                        >
                            <span className="material-symbols-outlined">close</span>
                        </button>
                    </header>

                    {/* Body Content (Scrollable) */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">

                        {/* Card 1: Información General */}
                        <section className="bg-slate-900 border border-slate-800/80 p-5 rounded-sm space-y-4 shadow-sm">
                            <div className="flex items-center gap-2 mb-2">
                                <span className="material-symbols-outlined text-primary text-sm">person</span>
                                <h3 className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500">Información General</h3>
                            </div>

                            <div className="space-y-4">
                                {/* Nombre Completo */}
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Nombre Completo *</label>
                                    <input
                                        name="nombre"
                                        value={formData.nombre}
                                        onChange={handleChange}
                                        required
                                        className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono"
                                        placeholder="Ej. Juan Pérez"
                                        type="text"
                                    />
                                </div>

                                {/* Dirección */}
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Dirección</label>
                                    <input
                                        name="direccion"
                                        value={formData.direccion}
                                        onChange={handleChange}
                                        className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono"
                                        placeholder="Calle, número, colonia"
                                        type="text"
                                    />
                                </div>

                                {/* Teléfono */}
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Teléfono</label>
                                    <input
                                        name="telefono"
                                        value={formData.telefono}
                                        onChange={handleChange}
                                        className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono"
                                        placeholder="ej. 4423123456"
                                        type="tel"
                                    />
                                </div>

                                {/* Email */}
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Email</label>
                                    <input
                                        name="email"
                                        value={formData.email}
                                        onChange={handleChange}
                                        className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono"
                                        placeholder="cliente@empresa.com"
                                        type="email"
                                    />
                                </div>
                            </div>
                        </section>

                        {/* Card 2: Configuración de Crédito */}
                        <section className="bg-slate-900 border border-slate-800/80 p-5 rounded-sm space-y-4 shadow-sm">
                            <div className="flex items-center gap-2 mb-2">
                                <span className="material-symbols-outlined text-primary text-sm">payments</span>
                                <h3 className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500">Configuración de Crédito</h3>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                {/* Límite de Crédito */}
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 text-center">
                                        Límite de Crédito
                                        {!isAdmin && <span className="text-red-400 ml-1">🔒</span>}
                                    </label>
                                    <div className="relative">
                                        <span className={`absolute left-3 top-1/2 -translate-y-1/2 font-mono text-sm ${isAdmin ? 'text-primary' : 'text-slate-500'}`}>$</span>
                                        <input
                                            name="limite_credito"
                                            value={formData.limite_credito}
                                            onChange={handleChange}
                                            readOnly={!isAdmin}
                                            className={`w-full border border-slate-800/80 rounded-sm font-mono text-right focus:outline-none transition-all text-sm py-2 pl-6 pr-3 ${isAdmin
                                                    ? 'bg-slate-900 text-slate-200 placeholder-slate-600 focus:border-primary'
                                                    : 'bg-slate-950 text-slate-500 cursor-not-allowed'
                                                }`}
                                            placeholder="0.00"
                                            step="0.01"
                                            type="number"
                                        />
                                    </div>
                                </div>

                                {/* Saldo Actual (Solo lectura en edición) */}
                                {initialData && (
                                    <div className="flex flex-col gap-1.5">
                                        <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 text-center">Saldo Actual</label>
                                        <div className="relative">
                                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 font-mono text-sm">$</span>
                                            <input
                                                value={initialData.saldo_actual || '0.00'}
                                                readOnly
                                                className="w-full bg-slate-950 border border-slate-800/80 rounded-sm text-slate-500 font-mono text-right text-sm py-2 pl-6 pr-3 cursor-not-allowed"
                                                type="text"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </section>

                    </div>

                    {/* Footer */}
                    <footer className="p-6 bg-slate-950 border-t border-slate-800 shrink-0 flex items-center justify-end gap-3 shadow-inner">
                        <button
                            type="button"
                            onClick={onClose}
                            className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-400 hover:text-white transition-colors px-4 py-2"
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="flex items-center justify-center gap-2 px-6 py-2 rounded-sm border border-primary/30 bg-primary/10 text-primary hover:bg-primary hover:text-white transition-all duration-200 group disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
                            ) : (
                                <span className="material-symbols-outlined text-[16px]">save</span>
                            )}
                            <span className="text-[10px] uppercase font-bold tracking-[0.2em]">
                                {initialData ? 'Guardar Cambios' : 'Guardar Cliente'}
                            </span>
                        </button>
                    </footer>
                </form>
            </div>
        </>
    );
};
