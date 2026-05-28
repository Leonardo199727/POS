import { useContext, useState, useEffect, useRef } from "react";
import { Sidebar } from "../components/Sidebar";
import { AuthContext } from "../context/AuthContext";
import api from "../api/axios";

const BUSINESS_NAME_KEY = "pos_business_name";
const DEFAULT_BUSINESS_NAME = "LMSolutions";

/**
 * Obtiene el nombre del negocio desde el cache local.
 * El cache se actualiza cada vez que se abre la app o se guarda en Settings.
 */
export const getBusinessName = (): string => {
    return localStorage.getItem(BUSINESS_NAME_KEY) || DEFAULT_BUSINESS_NAME;
};

export const Settings = () => {
    const { token } = useContext(AuthContext);

    // ── Business Name State ──
    const [businessName, setBusinessName] = useState("");
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // ── Backup State ──
    const [isExporting, setIsExporting] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [isCleaning, setIsCleaning] = useState(false);
    const [showCleanConfirm, setShowCleanConfirm] = useState(false);
    const [cleanConfirmText, setCleanConfirmText] = useState('');
    const [backupMsg, setBackupMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // ── Fetch config on mount ──
    useEffect(() => {
        const fetchConfig = async () => {
            if (!token) return;
            try {
                const res = await api.get('configuracion/negocio/', {
                    headers: { Authorization: `Token ${token}` },
                });
                if (res.data.success) {
                    const nombre = res.data.data.nombre_negocio;
                    setBusinessName(nombre);
                    localStorage.setItem(BUSINESS_NAME_KEY, nombre);
                }
            } catch (err) {
                console.error("Error fetching config:", err);
                setBusinessName(getBusinessName());
            } finally {
                setIsLoading(false);
            }
        };
        fetchConfig();
    }, [token]);

    // ── Save Business Name ──
    const handleSave = async () => {
        const trimmed = businessName.trim();
        if (!trimmed || !token) return;
        setIsSaving(true);
        setError(null);
        try {
            const res = await api.put('configuracion/negocio/', 
                { nombre_negocio: trimmed },
                { headers: { Authorization: `Token ${token}` } },
            );
            if (res.data.success) {
                const nombre = res.data.data.nombre_negocio;
                setBusinessName(nombre);
                localStorage.setItem(BUSINESS_NAME_KEY, nombre);
                setSaved(true);
                setTimeout(() => setSaved(false), 2500);
            }
        } catch (err: any) {
            const msg = err.response?.data?.detail || 'Error al guardar la configuración.';
            setError(msg);
        } finally {
            setIsSaving(false);
        }
    };

    // ── Export Database ──
    const handleExport = async () => {
        if (!token) return;
        setIsExporting(true);
        setBackupMsg(null);
        try {
            const res = await api.get('configuracion/backup/exportar/', {
                headers: { Authorization: `Token ${token}` },
                responseType: 'blob',
            });
            const blob = new Blob([res.data], { type: 'application/x-sqlite3' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            const now = new Date();
            const ts = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}_${String(now.getHours()).padStart(2,'0')}-${String(now.getMinutes()).padStart(2,'0')}`;
            a.href = url;
            a.download = `respaldo_pos_${ts}.sqlite3`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            setBackupMsg({ type: 'success', text: 'Base de datos exportada correctamente.' });
        } catch (err: any) {
            setBackupMsg({ type: 'error', text: err.response?.data?.detail || 'Error al exportar la base de datos.' });
        } finally {
            setIsExporting(false);
        }
    };

    // ── Import Database ──
    const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !token) return;

        setIsImporting(true);
        setBackupMsg(null);
        try {
            const formData = new FormData();
            formData.append('archivo', file);
            const res = await api.post('configuracion/backup/importar/', formData, {
                headers: {
                    Authorization: `Token ${token}`,
                    'Content-Type': 'multipart/form-data',
                },
            });
            setBackupMsg({ type: 'success', text: res.data.message || 'Base de datos importada. Reinicie la aplicación.' });
        } catch (err: any) {
            setBackupMsg({ type: 'error', text: err.response?.data?.detail || 'Error al importar la base de datos.' });
        } finally {
            setIsImporting(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    // ── Clean Database ──
    const handleClean = async () => {
        if (!token || cleanConfirmText !== 'LIMPIAR') return;
        setIsCleaning(true);
        setBackupMsg(null);
        try {
            const res = await api.post('configuracion/backup/limpiar/', 
                { confirmar: true },
                { headers: { Authorization: `Token ${token}` } },
            );
            setBackupMsg({ 
                type: 'success', 
                text: `${res.data.message} (${res.data.data.tablas_limpiadas} tablas limpiadas)` 
            });
            setShowCleanConfirm(false);
            setCleanConfirmText('');
        } catch (err: any) {
            setBackupMsg({ type: 'error', text: err.response?.data?.detail || 'Error al limpiar la base de datos.' });
        } finally {
            setIsCleaning(false);
        }
    };

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background-dark text-slate-100 font-display">
            <Sidebar />

            <main className="flex-1 flex flex-col overflow-hidden bg-[#0f1523]">
                {/* Header */}
                <header className="flex items-center justify-between border-b border-slate-800 bg-[#0b1121]/50 px-8 py-3 shrink-0">
                    <div className="flex items-center gap-4">
                        <span className="material-symbols-outlined text-primary text-2xl">settings</span>
                        <h1 className="text-2xl font-black uppercase tracking-tighter text-primary">Configuración</h1>
                    </div>
                </header>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-8">
                    <div className="max-w-2xl mx-auto space-y-8">

                        {isLoading ? (
                            <div className="flex flex-col items-center justify-center py-20 text-slate-500">
                                <span className="material-symbols-outlined animate-spin text-4xl mb-3">progress_activity</span>
                                <p className="text-xs uppercase tracking-widest">Cargando configuración...</p>
                            </div>
                        ) : (
                            <>
                                {/* ═══════════════ SECTION 1: Business Name ═══════════════ */}
                                <section className="bg-slate-900 border border-slate-800 rounded-sm shadow-2xl overflow-hidden">
                                    <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex items-center gap-3">
                                        <span className="material-symbols-outlined text-primary">storefront</span>
                                        <div>
                                            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-100">Datos del Negocio</h2>
                                            <p className="text-[10px] text-slate-500 mt-0.5 uppercase tracking-widest">Información que aparece en los tickets impresos</p>
                                        </div>
                                    </div>
                                    <div className="p-6 space-y-6">
                                        <div>
                                            <label className="block text-[10px] font-bold uppercase text-slate-500 tracking-widest mb-3">
                                                Nombre del Negocio
                                            </label>
                                            <input
                                                type="text"
                                                value={businessName}
                                                onChange={(e) => { setBusinessName(e.target.value); setSaved(false); setError(null); }}
                                                onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); }}
                                                placeholder="Nombre de tu negocio..."
                                                className="w-full bg-[#0b1121] border-2 border-slate-800 focus:border-primary transition-colors text-xl font-bold text-white px-5 py-4 rounded-sm outline-none focus:ring-0"
                                            />
                                            <p className="text-[10px] text-slate-500 mt-2 italic">
                                                * Este nombre aparecerá en el encabezado de todos los tickets de venta, abonos y cargos.
                                            </p>
                                        </div>

                                        {/* Preview */}
                                        <div>
                                            <label className="block text-[10px] font-bold uppercase text-slate-500 tracking-widest mb-3">
                                                Vista Previa del Ticket
                                            </label>
                                            <div className="bg-white text-black rounded-sm p-4 font-mono text-center max-w-[220px] mx-auto shadow-lg border border-slate-300">
                                                <p className="text-sm font-black tracking-tight">{businessName.trim() || DEFAULT_BUSINESS_NAME}</p>
                                                <p className="text-[8px] text-gray-500 mt-0.5">Punto de Venta</p>
                                                <div className="border-t border-dashed border-gray-400 my-2"></div>
                                                <p className="text-[8px] text-gray-400">Folio: V-00001</p>
                                                <p className="text-[8px] text-gray-400">Fecha: {new Date().toLocaleDateString('es-MX')}</p>
                                                <div className="border-t border-dashed border-gray-400 my-2"></div>
                                                <p className="text-[9px] font-bold mt-1">¡Gracias por su compra!</p>
                                            </div>
                                        </div>

                                        {error && (
                                            <div className="bg-red-950/30 border border-red-500/30 rounded-sm px-4 py-3 text-red-400 text-sm flex items-center gap-2">
                                                <span className="material-symbols-outlined text-[18px]">error</span>
                                                {error}
                                            </div>
                                        )}

                                        <button
                                            onClick={handleSave}
                                            disabled={!businessName.trim() || isSaving}
                                            className={`w-full py-4 rounded-sm font-bold text-sm uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${
                                                saved
                                                    ? 'bg-green-600 text-white shadow-lg shadow-green-600/20'
                                                    : 'bg-primary hover:bg-[#ff8a33] text-white shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed'
                                            }`}
                                        >
                                            <span className="material-symbols-outlined text-[18px]">
                                                {isSaving ? 'progress_activity' : saved ? 'check_circle' : 'save'}
                                            </span>
                                            {isSaving ? 'Guardando...' : saved ? '¡Guardado Exitosamente!' : 'Guardar Cambios'}
                                        </button>
                                    </div>
                                </section>

                                {/* ═══════════════ SECTION 2: Database Backup ═══════════════ */}
                                <section className="bg-slate-900 border border-slate-800 rounded-sm shadow-2xl overflow-hidden">
                                    <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex items-center gap-3">
                                        <span className="material-symbols-outlined text-primary">database</span>
                                        <div>
                                            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-100">Respaldo de Datos</h2>
                                            <p className="text-[10px] text-slate-500 mt-0.5 uppercase tracking-widest">Exportar, importar o limpiar la base de datos</p>
                                        </div>
                                    </div>

                                    <div className="p-6 space-y-5">
                                        {/* Feedback message */}
                                        {backupMsg && (
                                            <div className={`rounded-sm px-4 py-3 text-sm flex items-center gap-2 ${
                                                backupMsg.type === 'success'
                                                    ? 'bg-green-950/30 border border-green-500/30 text-green-400'
                                                    : 'bg-red-950/30 border border-red-500/30 text-red-400'
                                            }`}>
                                                <span className="material-symbols-outlined text-[18px]">
                                                    {backupMsg.type === 'success' ? 'check_circle' : 'error'}
                                                </span>
                                                {backupMsg.text}
                                            </div>
                                        )}

                                        {/* Export */}
                                        <div className="bg-slate-800/50 border border-slate-700 rounded-sm p-5">
                                            <div className="flex items-start gap-4">
                                                <span className="material-symbols-outlined text-emerald-400 text-3xl mt-0.5">download</span>
                                                <div className="flex-1">
                                                    <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">Exportar Base de Datos</h3>
                                                    <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
                                                        Descarga una copia completa de tu base de datos. Úsala para crear respaldos
                                                        o para migrar tus datos a una nueva versión de la aplicación.
                                                    </p>
                                                    <button
                                                        onClick={handleExport}
                                                        disabled={isExporting}
                                                        className="mt-4 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs uppercase tracking-widest rounded-sm transition-colors shadow-lg shadow-emerald-600/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                                    >
                                                        <span className="material-symbols-outlined text-[16px]">
                                                            {isExporting ? 'progress_activity' : 'download'}
                                                        </span>
                                                        {isExporting ? 'Exportando...' : 'Descargar Respaldo'}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Import */}
                                        <div className="bg-slate-800/50 border border-slate-700 rounded-sm p-5">
                                            <div className="flex items-start gap-4">
                                                <span className="material-symbols-outlined text-blue-400 text-3xl mt-0.5">upload</span>
                                                <div className="flex-1">
                                                    <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">Importar Base de Datos</h3>
                                                    <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
                                                        Restaura una base de datos desde un archivo de respaldo previo.
                                                        Se creará un respaldo automático de la base actual antes de reemplazarla.
                                                    </p>
                                                    <p className="text-[9px] text-amber-500/80 mt-1 flex items-center gap-1">
                                                        <span className="material-symbols-outlined text-[12px]">warning</span>
                                                        Deberás reiniciar la aplicación después de importar.
                                                    </p>
                                                    <input
                                                        ref={fileInputRef}
                                                        type="file"
                                                        accept=".sqlite3,.db"
                                                        onChange={handleImport}
                                                        className="hidden"
                                                    />
                                                    <button
                                                        onClick={() => fileInputRef.current?.click()}
                                                        disabled={isImporting}
                                                        className="mt-4 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs uppercase tracking-widest rounded-sm transition-colors shadow-lg shadow-blue-600/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                                    >
                                                        <span className="material-symbols-outlined text-[16px]">
                                                            {isImporting ? 'progress_activity' : 'upload_file'}
                                                        </span>
                                                        {isImporting ? 'Importando...' : 'Seleccionar Archivo'}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Clean */}
                                        <div className="bg-red-950/10 border border-red-500/20 rounded-sm p-5">
                                            <div className="flex items-start gap-4">
                                                <span className="material-symbols-outlined text-red-400 text-3xl mt-0.5">delete_forever</span>
                                                <div className="flex-1">
                                                    <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">Limpiar Base de Datos</h3>
                                                    <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
                                                        Elimina todos los datos del sistema (ventas, productos, clientes, inventario, etc.)
                                                        pero conserva los usuarios, roles y la configuración del negocio.
                                                    </p>
                                                    <p className="text-[9px] text-red-400/80 mt-1 flex items-center gap-1 font-bold">
                                                        <span className="material-symbols-outlined text-[12px]">dangerous</span>
                                                        Esta acción es irreversible. Se recomienda exportar un respaldo antes.
                                                    </p>

                                                    {!showCleanConfirm ? (
                                                        <button
                                                            onClick={() => setShowCleanConfirm(true)}
                                                            className="mt-4 px-6 py-3 bg-red-600/80 hover:bg-red-600 text-white font-bold text-xs uppercase tracking-widest rounded-sm transition-colors shadow-lg shadow-red-600/20 flex items-center gap-2"
                                                        >
                                                            <span className="material-symbols-outlined text-[16px]">delete_forever</span>
                                                            Limpiar Todo
                                                        </button>
                                                    ) : (
                                                        <div className="mt-4 bg-red-950/30 border border-red-500/30 rounded-sm p-4 space-y-3">
                                                            <p className="text-xs text-red-300 font-bold">
                                                                Escriba <code className="bg-red-950 px-2 py-0.5 rounded text-red-400 font-mono">LIMPIAR</code> para confirmar:
                                                            </p>
                                                            <input
                                                                type="text"
                                                                autoFocus
                                                                value={cleanConfirmText}
                                                                onChange={(e) => setCleanConfirmText(e.target.value.toUpperCase())}
                                                                onKeyDown={(e) => { if (e.key === 'Enter' && cleanConfirmText === 'LIMPIAR') handleClean(); }}
                                                                placeholder="Escriba LIMPIAR..."
                                                                className="w-full bg-[#0b1121] border-2 border-red-500/30 focus:border-red-500 text-white text-sm px-4 py-3 rounded-sm outline-none font-mono uppercase tracking-widest"
                                                            />
                                                            <div className="flex gap-3">
                                                                <button
                                                                    onClick={() => { setShowCleanConfirm(false); setCleanConfirmText(''); }}
                                                                    className="flex-1 py-2 border border-slate-700 text-slate-400 hover:text-slate-200 font-bold text-xs uppercase tracking-widest rounded-sm transition-colors"
                                                                >
                                                                    Cancelar
                                                                </button>
                                                                <button
                                                                    onClick={handleClean}
                                                                    disabled={cleanConfirmText !== 'LIMPIAR' || isCleaning}
                                                                    className="flex-1 py-2 bg-red-600 hover:bg-red-500 text-white font-bold text-xs uppercase tracking-widest rounded-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                                                >
                                                                    <span className="material-symbols-outlined text-[14px]">
                                                                        {isCleaning ? 'progress_activity' : 'delete_forever'}
                                                                    </span>
                                                                    {isCleaning ? 'Limpiando...' : 'Confirmar'}
                                                                </button>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </section>
                            </>
                        )}

                    </div>
                </div>

                {/* Footer */}
                <footer className="h-8 bg-slate-950 border-t border-slate-800 px-4 flex items-center justify-between shrink-0 mt-auto">
                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2">
                            <div className="size-2 bg-green-500"></div>
                            <span className="text-[10px] font-bold text-slate-400 tracking-wider">SISTEMA ONLINE</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-300 tracking-widest">
                        {new Date().toLocaleDateString('es-ES')} | {new Date().toLocaleTimeString('es-ES')}
                    </div>
                </footer>
            </main>
        </div>
    );
};

export default Settings;
