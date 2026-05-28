import React, { useState } from 'react';
import api from '../api/axios';

interface AdminAuthModalProps {
    isOpen: boolean;
    onClose: () => void;
    onAuthorized: (adminUserId: number) => void;
    title?: string;
    description?: string;
}

export const AdminAuthModal: React.FC<AdminAuthModalProps> = ({
    isOpen,
    onClose,
    onAuthorized,
    title = 'Autorización Requerida',
    description = 'Ingrese las credenciales de un administrador para continuar.',
}) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            const res = await api.post('login/', { username, password });

            if (res.data.success) {
                const adminUser = res.data.data.user;

                // Verificar que el usuario sea ADMIN
                if (adminUser.rol !== 'ADMIN') {
                    setError('El usuario no tiene permisos de administrador.');
                    setIsLoading(false);
                    return;
                }

                // Limpiar y retornar el ID del admin
                setUsername('');
                setPassword('');
                onAuthorized(adminUser.id);
            }
        } catch (err: any) {
            const msg = err.response?.data?.detail || 'Credenciales inválidas.';
            setError(msg);
        } finally {
            setIsLoading(false);
        }
    };

    const handleClose = () => {
        setUsername('');
        setPassword('');
        setError('');
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onClick={handleClose}
            />

            {/* Modal */}
            <div className="relative bg-slate-950 border border-slate-800 rounded-lg shadow-2xl w-[400px] overflow-hidden">
                {/* Header */}
                <div className="px-6 py-5 border-b border-slate-800">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                            <span className="material-symbols-outlined text-primary">admin_panel_settings</span>
                        </div>
                        <div>
                            <h2 className="text-white font-bold text-sm uppercase tracking-widest">{title}</h2>
                            <p className="text-slate-400 text-xs mt-0.5">{description}</p>
                        </div>
                    </div>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
                    {error && (
                        <div className="bg-red-500/10 border border-red-500/30 rounded px-3 py-2 flex items-center gap-2">
                            <span className="material-symbols-outlined text-red-500 text-sm">error</span>
                            <span className="text-red-400 text-xs font-medium">{error}</span>
                        </div>
                    )}

                    <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Usuario</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 text-slate-100 py-3 px-4 focus:border-primary focus:outline-none focus:ring-0 text-sm tracking-wider rounded-sm transition-all placeholder:text-slate-600"
                            placeholder="admin"
                            autoFocus
                            required
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Contraseña</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 text-slate-100 py-3 px-4 focus:border-primary focus:outline-none focus:ring-0 text-sm tracking-wider rounded-sm transition-all placeholder:text-slate-600"
                            placeholder="••••••••"
                            required
                        />
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-2">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-3 rounded-sm text-xs uppercase tracking-widest transition-colors border border-slate-700"
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading || !username || !password}
                            className="flex-1 bg-primary hover:bg-orange-600 text-white font-bold py-3 rounded-sm text-xs uppercase tracking-widest transition-colors shadow-lg shadow-primary/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <span className="material-symbols-outlined animate-spin text-sm">progress_activity</span>
                            ) : (
                                <>
                                    <span className="material-symbols-outlined text-sm">verified</span>
                                    Autorizar
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
