import { useContext, useState, useEffect } from "react";
import { Sidebar } from "../components/Sidebar";
import { AuthContext } from "../context/AuthContext";
import { useRefresh } from "../context/RefreshContext";
import { useDebounce } from "../hooks/useDebounce";
import api from "../api/axios";
import { useNavigate } from "react-router-dom";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx-js-style";

interface Cliente {
    id: number;
    nombre: string;
    telefono: string;
    email: string;
    direccion: string;
    saldo_actual: string;
    limite_credito: string;
}

interface MovimientoReporte {
    fecha: string;
    movimiento: string;
    detalle: string;
    metodo: string;
    monto: string;
    saldo: string | null;
    referencia: string;
}

interface EstadoCuenta {
    cliente_id: number;
    nombre_cliente: string;
    telefono: string;
    direccion: string;
    saldo_actual: string;
    fecha_generacion: string;
    movimientos: MovimientoReporte[];
}

export const CreditoCobranza = () => {
    const { token } = useContext(AuthContext);
    const { refreshKey } = useRefresh();
    const navigate = useNavigate();

    // Export Modal States
    const [isExportModalOpen, setIsExportModalOpen] = useState(false);
    const [exportType, setExportType] = useState<'pdf' | 'excel' | null>(null);
    const [startClientId, setStartClientId] = useState<string>('');
    const [endClientId, setEndClientId] = useState<string>('');

    // Search State
    const [clientes, setClientes] = useState<Cliente[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const debouncedSearchTerm = useDebounce(searchTerm, 500);
    
    // Selected Report State
    const [selectedCliente, setSelectedCliente] = useState<Cliente | null>(null);
    const [estadoCuenta, setEstadoCuenta] = useState<EstadoCuenta | null>(null);
    const [isLoadingReport, setIsLoadingReport] = useState(false);

    // Fetch Clientes Logic
    const fetchClientes = async (search: string = '') => {
        if (!token) return;
        setIsLoading(true);
        try {
            const queryParams = new URLSearchParams({ page: '1', page_size: '10000' });
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
            console.error("Error fetching clientes:", error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (!selectedCliente) {
            fetchClientes(debouncedSearchTerm);
        }
    }, [token, debouncedSearchTerm, refreshKey, selectedCliente]);

    // Fetch Report Logic
    useEffect(() => {
        if (!selectedCliente || !token) return;
        
        const fetchReport = async () => {
            setIsLoadingReport(true);
            try {
                const res = await api.get(`reportes/estado-cuenta/${selectedCliente.id}/`, {
                    headers: { Authorization: `Token ${token}` }
                });
                if (res.data.success) {
                    setEstadoCuenta(res.data.data);
                }
            } catch (error) {
                console.error("Error fetching report:", error);
            } finally {
                setIsLoadingReport(false);
            }
        };
        fetchReport();
    }, [selectedCliente, token, refreshKey]);

    const formatCurrency = (amount: string | number | null) => {
        if (amount === null) return '--';
        const val = typeof amount === 'string' ? parseFloat(amount) : amount;
        if (isNaN(val)) return '$0.00';
        return `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    const handleExportPDF = () => {
        if (!estadoCuenta) return;
        
        const doc = new jsPDF();
        
        // Header Text
        doc.setFontSize(18);
        doc.text("LMSolutions POS - Estado de Cuenta", 14, 20);
        
        doc.setFontSize(11);
        doc.text(`Cliente: ${estadoCuenta.nombre_cliente} (ID: ${estadoCuenta.cliente_id})`, 14, 30);
        doc.text(`Fecha de Corte: ${estadoCuenta.fecha_generacion}`, 14, 36);
        doc.text(`Saldo Total Deudor: ${formatCurrency(estadoCuenta.saldo_actual)}`, 14, 42);

        // Table Content
        const tableColumn = ["Fecha", "Concepto", "Detalle / Referencia", "Método", "Monto", "Saldo Restante"];
        const tableRows = [...estadoCuenta.movimientos].reverse().map(mov => [
            mov.fecha,
            mov.movimiento.toUpperCase(),
            `${mov.detalle}\nRef: ${mov.referencia}`,
            mov.metodo || '--',
            `${mov.movimiento.includes("Abono") || mov.movimiento.includes("Contado") ? '+' : '-'}${formatCurrency(mov.monto)}`,
            formatCurrency(mov.saldo)
        ]);

        autoTable(doc, {
            head: [tableColumn],
            body: tableRows,
            startY: 50,
            styles: { fontSize: 8 },
            headStyles: { fillColor: [15, 21, 35] }
        });
        
        doc.save(`Estado_de_Cuenta_${estadoCuenta.nombre_cliente.replace(/\s+/g, '_')}_${estadoCuenta.fecha_generacion.split(' ')[0]}.pdf`);
    };

    const handleExportExcel = () => {
        if (!estadoCuenta) return;
        
        const data = [...estadoCuenta.movimientos].reverse().map(mov => ({
            "Fecha": mov.fecha,
            "Concepto": mov.movimiento.toUpperCase(),
            "Detalle": mov.detalle,
            "Referencia": mov.referencia,
            "Método de Pago": mov.metodo || '--',
            "Operación": (mov.movimiento.includes("Abono") || mov.movimiento.includes("Contado") ? '+' : '-'),
            "Monto": parseFloat(mov.monto),
            "Saldo Restante": mov.saldo ? parseFloat(mov.saldo) : 0
        }));

        const worksheet = XLSX.utils.json_to_sheet(data);
        const workbook = XLSX.utils.book_new();
        
        // Custom Column Widths
        worksheet["!cols"] = [
            { wch: 15 }, // Fecha
            { wch: 20 }, // Concepto
            { wch: 45 }, // Detalle
            { wch: 15 }, // Referencia
            { wch: 15 }, // Método de Pago
            { wch: 12 }, // Operación
            { wch: 15 }, // Monto
            { wch: 18 }  // Saldo Restante
        ];
        
        // Style Headers (First Row)
        const headerStyle = {
            font: { bold: true, color: { rgb: "FFFFFF" } },
            fill: { fgColor: { rgb: "0F1523" } }, // Dark LMSolutions Theme
            alignment: { horizontal: "center", vertical: "center" },
            border: {
                top: { style: "thin", color: { rgb: "000000" } },
                bottom: { style: "thin", color: { rgb: "000000" } },
                left: { style: "thin", color: { rgb: "000000" } },
                right: { style: "thin", color: { rgb: "000000" } }
            }
        };

        // Extract the range from '!ref' to know how many columns we have
        const range = XLSX.utils.decode_range(worksheet['!ref'] as string);
        for (let C = range.s.c; C <= range.e.c; ++C) {
            const cellAddress = XLSX.utils.encode_cell({ r: 0, c: C }); // Row 0 is the header
            if (!worksheet[cellAddress]) continue;
            worksheet[cellAddress].s = headerStyle;
        }

        // Add AutoFilter
        if (worksheet["!ref"]) {
            worksheet["!autofilter"] = { ref: worksheet["!ref"] };
        }

        XLSX.utils.book_append_sheet(workbook, worksheet, "Estado de Cuenta");
        
        XLSX.writeFile(workbook, `Estado_de_Cuenta_${estadoCuenta.nombre_cliente.replace(/\s+/g, '_')}_${estadoCuenta.fecha_generacion.split(' ')[0]}.xlsx`);
    };

    // --- LIST EXPORT FUNCTIONS ---
    const openExportModal = (type: 'pdf' | 'excel') => {
        setExportType(type);
        setIsExportModalOpen(true);
    };

    const closeExportModal = () => {
        setIsExportModalOpen(false);
        setExportType(null);
    };

    const generateListPDF = (data: Cliente[]) => {
        const doc = new jsPDF();
        doc.setFontSize(18);
        doc.text("LMSolutions POS - Directorio de Clientes", 14, 20);
        
        const now = new Date();
        doc.setFontSize(11);
        doc.text(`Fecha de exportación: ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`, 14, 30);
        doc.text(`Total de registros: ${data.length}`, 14, 36);

        const tableColumn = ["ID", "Nombre", "Teléfono", "Saldo Actual", "Límite"];
        const tableRows = data.map(c => [
            `#${c.id}`,
            c.nombre,
            c.telefono || 'Sin teléfono',
            formatCurrency(c.saldo_actual),
            formatCurrency(c.limite_credito)
        ]);

        autoTable(doc, {
            head: [tableColumn],
            body: tableRows,
            startY: 45,
            styles: { fontSize: 8 },
            headStyles: { fillColor: [15, 21, 35] }
        });
        
        doc.save(`Directorio_Clientes_${now.getTime()}.pdf`);
    };

    const generateListExcel = (data: Cliente[]) => {
        const sheetData = data.map(c => ({
            "ID": c.id,
            "Nombre": c.nombre,
            "Teléfono": c.telefono || 'Sin teléfono',
            "Email": c.email || 'Sin email',
            "Dirección": c.direccion || '--',
            "Saldo Actual": parseFloat(c.saldo_actual),
            "Límite de Crédito": parseFloat(c.limite_credito)
        }));

        const worksheet = XLSX.utils.json_to_sheet(sheetData);
        const workbook = XLSX.utils.book_new();
        
        worksheet["!cols"] = [
            { wch: 8 },  // ID
            { wch: 40 }, // Nombre
            { wch: 15 }, // Teléfono
            { wch: 25 }, // Email
            { wch: 40 }, // Direccion
            { wch: 15 }, // Saldo Actual
            { wch: 15 }  // Límite de Crédito
        ];
        
        const headerStyle = {
            font: { bold: true, color: { rgb: "FFFFFF" } },
            fill: { fgColor: { rgb: "0F1523" } },
            alignment: { horizontal: "center", vertical: "center" },
            border: {
                top: { style: "thin", color: { rgb: "000000" } },
                bottom: { style: "thin", color: { rgb: "000000" } },
                left: { style: "thin", color: { rgb: "000000" } },
                right: { style: "thin", color: { rgb: "000000" } }
            }
        };

        const range = XLSX.utils.decode_range(worksheet['!ref'] || "A1:G1");
        for (let C = range.s.c; C <= range.e.c; ++C) {
            const cellAddress = XLSX.utils.encode_cell({ r: 0, c: C });
            if (!worksheet[cellAddress]) continue;
            worksheet[cellAddress].s = headerStyle;
        }

        if (worksheet["!ref"]) {
            worksheet["!autofilter"] = { ref: worksheet["!ref"] };
        }

        XLSX.utils.book_append_sheet(workbook, worksheet, "Clientes");
        XLSX.writeFile(workbook, `Directorio_Clientes_${new Date().getTime()}.xlsx`);
    };

    const handleExportList = async (option: 'all' | 'range') => {
        let exportData: Cliente[] = [];
        setIsLoading(true); // Optional: if you want to show loading
        
        try {
            // Fetch all to ensure we have the complete list
            const res = await api.get('clientes/', {
                params: { search: '', page_size: 10000 },
                headers: { Authorization: `Token ${token}` }
            });
            
            // Backend returns data in res.data.data based on pagination setup
            exportData = res.data.data ? res.data.data : res.data;
            
            if (option === 'range') {
                const start = parseInt(startClientId, 10);
                const end = parseInt(endClientId, 10);
                if (!isNaN(start) && !isNaN(end)) {
                    // Assuming IDs are sequential numbers for filtering
                    exportData = exportData.filter(c => c.id >= start && c.id <= end);
                }
            }
            
            if (exportType === 'pdf') {
                generateListPDF(exportData);
            } else if (exportType === 'excel') {
                generateListExcel(exportData);
            }
        } catch (error) {
            console.error("Error exporting list", error);
        } finally {
            closeExportModal();
            setIsLoading(false);
        }
    };

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background-dark text-slate-100 font-display">
            <Sidebar />
            
            <main className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#0f1523]">
                {/* Header */}
                <header className="flex flex-col items-start border-b border-slate-800 bg-[#0b1121]/50 px-8 py-6 shrink-0 h-24 justify-center relative">
                    {/* Back Button */}
                    <button 
                        onClick={() => navigate('/reportes')}
                        className="absolute left-8 top-8 text-slate-500 hover:text-white flex items-center gap-2 transition-colors lg:hidden"
                    >
                        <span className="material-symbols-outlined text-sm">arrow_back</span>
                    </button>

                    <div className="flex items-center gap-4 w-full justify-between">
                        <div className="flex items-center gap-4">
                            <button 
                                onClick={() => navigate('/reportes')}
                                className="hidden lg:flex w-10 h-10 rounded-sm bg-slate-900 border border-slate-800 items-center justify-center text-slate-400 hover:text-primary hover:border-primary/50 transition-all active:scale-95"
                                title="Volver al Dashboard"
                            >
                                <span className="material-symbols-outlined">arrow_back</span>
                            </button>
                            <div className="flex flex-col">
                                <h1 className="text-2xl font-black uppercase tracking-tighter text-white">Crédito y Cobranza</h1>
                                <p className="text-xs text-slate-400 tracking-widest uppercase mt-1">Historial Completo de Cliente</p>
                            </div>
                        </div>

                        {selectedCliente && (
                            <button 
                                onClick={() => setSelectedCliente(null)}
                                className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-sm text-xs font-bold uppercase tracking-widest transition-colors flex items-center gap-2"
                            >
                                <span className="material-symbols-outlined text-sm">search</span>
                                Buscar Otro
                            </button>
                        )}
                    </div>
                </header>

                <div className="flex-1 flex flex-col p-8 relative min-h-0 bg-[#0f1523]">
                    
                    {/* VIEW 1: SEARCH CENTERED */}
                    {!selectedCliente && (
                        <div className="max-w-4xl mx-auto w-full flex flex-col h-full min-h-0">
                            <h2 className="text-xl font-bold text-slate-300 mb-6 tracking-tight text-center shrink-0 mt-4">Busca un cliente para generar su reporte</h2>
                            
                            <div className="flex flex-col sm:flex-row gap-4 mb-6 shrink-0 relative">
                                <div className="relative flex-1">
                                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-primary text-2xl">person_search</span>
                                    <input 
                                        className="w-full bg-slate-900 border-2 border-slate-800 rounded py-5 pl-14 pr-4 focus:ring-2 focus:ring-primary focus:border-primary text-slate-100 placeholder:text-slate-500 transition-all text-lg shadow-xl shadow-black/20" 
                                        placeholder="Ingresa un Nombre, ID o Teléfono para comenzar..." 
                                        type="text"
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        autoFocus
                                    />
                                </div>
                                <div className="flex items-center justify-center gap-3">
                                    <button 
                                        onClick={() => openExportModal('pdf')}
                                        className="h-full px-6 bg-slate-800 hover:bg-rose-600/20 text-slate-300 hover:text-rose-400 border border-slate-700 hover:border-rose-500/50 transition-colors rounded-sm text-sm font-bold uppercase tracking-widest flex items-center justify-center gap-2"
                                    >
                                        <span className="material-symbols-outlined text-[20px]">picture_as_pdf</span>
                                        PDF
                                    </button>
                                    <button 
                                        onClick={() => openExportModal('excel')}
                                        className="h-full px-6 bg-slate-800 hover:bg-emerald-600/20 text-slate-300 hover:text-emerald-400 border border-slate-700 hover:border-emerald-500/50 transition-colors rounded-sm text-sm font-bold uppercase tracking-widest flex items-center justify-center gap-2"
                                    >
                                        <span className="material-symbols-outlined text-[20px]">table_view</span>
                                        EXCEL
                                    </button>
                                </div>
                            </div>

                            {/* Contenedor Resultados */}
                            <div className="bg-slate-900/50 border border-slate-800 rounded-sm overflow-hidden flex flex-col flex-1 min-h-0">
                                {isLoading && (
                                    <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-slate-500">
                                        <span className="material-symbols-outlined animate-spin text-4xl mb-4 text-primary">progress_activity</span>
                                        <p className="text-sm uppercase tracking-widest font-mono">Consultando base de datos...</p>
                                    </div>
                                )}

                                {!isLoading && clientes.length === 0 && (
                                    <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-slate-500">
                                        <span className="material-symbols-outlined text-5xl mb-4 opacity-50">quick_reference_all</span>
                                        <p className="text-sm uppercase tracking-widest">{searchTerm ? 'Sin coincidencias.' : 'Los resultados aparecerán aquí.'}</p>
                                    </div>
                                )}

                                {!isLoading && clientes.length > 0 && (
                                    <div className="flex-1 overflow-y-auto custom-scrollbar relative">
                                        <table className="w-full text-left text-sm text-slate-300 border-collapse">
                                            <thead className="text-[10px] uppercase text-slate-500 font-bold tracking-[0.2em]">
                                                <tr>
                                                    <th scope="col" className="px-6 py-4 w-[15%] sticky top-0 z-10 bg-[#0b1121] border-y border-slate-700 shadow-sm">ID</th>
                                                    <th scope="col" className="px-6 py-4 w-[40%] sticky top-0 z-10 bg-[#0b1121] border-y border-slate-700 shadow-sm">Nombre</th>
                                                    <th scope="col" className="px-6 py-4 w-[25%] sticky top-0 z-10 bg-[#0b1121] border-y border-slate-700 shadow-sm">Teléfono</th>
                                                    <th scope="col" className="px-6 py-4 text-right w-[20%] sticky top-0 z-10 bg-[#0b1121] border-y border-slate-700 shadow-sm">Saldo Actual</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {clientes.map(cliente => (
                                                    <tr 
                                                        key={cliente.id}
                                                        onClick={() => setSelectedCliente(cliente)}
                                                        className="bg-slate-900 border-b border-slate-800/80 hover:bg-slate-800 cursor-pointer transition-colors group"
                                                    >
                                                        <td className="px-6 py-4 font-mono text-slate-500 group-hover:text-primary transition-colors">
                                                            #{cliente.id}
                                                        </td>
                                                        <td className="px-6 py-4 font-bold text-white group-hover:text-primary transition-colors">
                                                            {cliente.nombre}
                                                        </td>
                                                        <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                                                            {cliente.telefono || 'Sin teléfono'}
                                                        </td>
                                                        <td className={`px-6 py-4 text-right font-mono font-bold ${parseFloat(cliente.saldo_actual) > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                                                            {formatCurrency(cliente.saldo_actual)}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* VIEW 2: FULL WIDTH REPORT */}
                    {selectedCliente && (
                        <div className="max-w-7xl mx-auto flex flex-col h-full animate-in fade-in slide-in-from-bottom-4 duration-500">
                            
                            {isLoadingReport ? (
                                <div className="flex flex-col items-center justify-center h-[400px] text-primary">
                                    <span className="material-symbols-outlined animate-spin text-5xl mb-4">autorenew</span>
                                    <p className="text-sm uppercase tracking-widest font-mono text-slate-400">Generando Reporte Histórico...</p>
                                </div>
                            ) : estadoCuenta ? (
                                <>
                                    {/* Report Header Cards */}
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 mt-2">
                                        <div className="bg-slate-900 p-6 rounded-sm border-l-4 border-slate-600 flex flex-col justify-center">
                                            <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">Cliente</p>
                                            <p className="text-xl font-bold text-white truncate" title={estadoCuenta.nombre_cliente}>
                                                {estadoCuenta.nombre_cliente}
                                            </p>
                                            <div className="flex items-center gap-4 mt-2">
                                                <p className="text-xs text-slate-400 font-mono">ID: {estadoCuenta.cliente_id}</p>
                                                {estadoCuenta.telefono && (
                                                    <p className="text-xs text-slate-400 font-mono flex items-center gap-1" title="Teléfono">
                                                        <span className="material-symbols-outlined text-[14px]">call</span>
                                                        {estadoCuenta.telefono}
                                                    </p>
                                                )}
                                            </div>
                                            {estadoCuenta.direccion && (
                                                <p className="text-[11px] text-slate-500 flex items-start gap-1 mt-2 leading-tight line-clamp-2" title="Dirección">
                                                    <span className="material-symbols-outlined text-[13px] mt-0.5">location_on</span>
                                                    {estadoCuenta.direccion}
                                                </p>
                                            )}
                                        </div>

                                        <div className="bg-slate-900 p-6 rounded-sm border-l-4 border-sky-500 flex flex-col justify-center">
                                            <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">Total Movimientos</p>
                                            <p className="text-2xl font-mono font-bold text-white tracking-tighter">
                                                {estadoCuenta.movimientos.length}
                                            </p>
                                            <p className="text-xs text-slate-400 font-mono mt-2 flex items-center gap-1">
                                                <span className="material-symbols-outlined text-[14px]">history</span>
                                                Historial completo
                                            </p>
                                        </div>

                                        <div className={`bg-slate-900 p-6 rounded-sm border-l-4 flex flex-col justify-center ${parseFloat(estadoCuenta.saldo_actual) > 0 ? 'border-rose-500' : 'border-emerald-500'}`}>
                                            <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">Saldo Deudor Actual</p>
                                            <p className={`text-3xl font-mono font-bold tracking-tighter ${parseFloat(estadoCuenta.saldo_actual) > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                                                {formatCurrency(estadoCuenta.saldo_actual)}
                                            </p>
                                            <p className="text-[10px] text-slate-400 mt-2 font-mono uppercase tracking-widest">
                                                Corte: {estadoCuenta.fecha_generacion}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Report Table */}
                                    <div className="bg-slate-900 rounded-sm border border-slate-800 shadow-xl overflow-hidden flex flex-col min-h-0">
                                        <div className="px-6 py-4 border-b border-slate-800 bg-slate-900 flex justify-between items-center">
                                            <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                                                <span className="material-symbols-outlined text-primary">list_alt</span>
                                                Historial de Transacciones
                                            </h3>
                                            <div className="flex items-center gap-3">
                                                <button 
                                                    onClick={handleExportPDF}
                                                    className="bg-slate-800 hover:bg-rose-600/20 text-slate-300 hover:text-rose-400 border border-slate-700 hover:border-rose-500/50 transition-colors px-3 py-1.5 rounded-sm text-xs font-bold uppercase tracking-widest flex items-center gap-2"
                                                >
                                                    <span className="material-symbols-outlined text-[16px]">picture_as_pdf</span>
                                                    PDF
                                                </button>
                                                <button 
                                                    onClick={handleExportExcel}
                                                    className="bg-slate-800 hover:bg-emerald-600/20 text-slate-300 hover:text-emerald-400 border border-slate-700 hover:border-emerald-500/50 transition-colors px-3 py-1.5 rounded-sm text-xs font-bold uppercase tracking-widest flex items-center gap-2"
                                                >
                                                    <span className="material-symbols-outlined text-[16px]">table_view</span>
                                                    EXCEL
                                                </button>
                                            </div>
                                        </div>
                                        <div className="overflow-x-auto custom-scrollbar flex-1 max-h-[60vh]">
                                            <table className="w-full text-left text-sm text-slate-300">
                                                <thead className="text-[10px] uppercase tracking-widest text-slate-500 bg-slate-950 font-mono sticky top-0 z-10 shadow-sm">
                                                    <tr>
                                                        <th className="px-6 py-4 font-normal">Fecha</th>
                                                        <th className="px-6 py-4 font-normal">Concepto</th>
                                                        <th className="px-6 py-4 font-normal">Detalle / Referencia</th>
                                                        <th className="px-6 py-4 font-normal">Método</th>
                                                        <th className="px-6 py-4 font-normal text-right">Monto</th>
                                                        <th className="px-6 py-4 font-normal text-right bg-slate-900/50">Saldo Restante</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-800/50">
                                                    {estadoCuenta.movimientos.length === 0 ? (
                                                        <tr>
                                                            <td colSpan={6} className="px-6 py-12 text-center text-slate-500 font-mono">
                                                                No hay historial de movimientos para este cliente.
                                                            </td>
                                                        </tr>
                                                    ) : (
                                                        [...estadoCuenta.movimientos].reverse().map((mov, idx) => (
                                                            <tr key={idx} className="hover:bg-slate-800/30 transition-colors group">
                                                                <td className="px-6 py-4 font-mono text-xs whitespace-nowrap">{mov.fecha}</td>
                                                                <td className="px-6 py-4">
                                                                    <div className="flex items-center gap-2">
                                                                        <span className={`size-2 rounded-full ${
                                                                            mov.movimiento.includes('Abono') ? 'bg-emerald-500' :
                                                                            mov.movimiento.includes('Crédito') ? 'bg-amber-500' :
                                                                            mov.movimiento.includes('Contado') ? 'bg-sky-500' :
                                                                            'bg-rose-500'
                                                                        }`}></span>
                                                                        <span className="font-bold text-white text-xs uppercase tracking-wider">{mov.movimiento}</span>
                                                                    </div>
                                                                </td>
                                                                <td className="px-6 py-4">
                                                                    <p className="text-slate-300 truncate max-w-xs" title={mov.detalle}>{mov.detalle}</p>
                                                                    <p className="text-[10px] font-mono text-slate-500 mt-1 uppercase tracking-widest">{mov.referencia}</p>
                                                                </td>
                                                                <td className="px-6 py-4">
                                                                    <span className="font-mono text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded">
                                                                        {mov.metodo || '--'}
                                                                    </span>
                                                                </td>
                                                                <td className={`px-6 py-4 font-mono text-right font-bold ${
                                                                    mov.movimiento.includes('Abono') || mov.movimiento.includes('Contado') ? 'text-emerald-400' : 'text-amber-400'
                                                                }`}>
                                                                    {mov.movimiento.includes('Abono') || mov.movimiento.includes('Contado') ? '+' : '-'}{formatCurrency(mov.monto)}
                                                                </td>
                                                                <td className="px-6 py-4 font-mono text-right font-bold text-white bg-slate-900/30 group-hover:bg-transparent transition-colors">
                                                                    {formatCurrency(mov.saldo)}
                                                                </td>
                                                            </tr>
                                                        ))
                                                    )}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </>
                            ) : null}

                        </div>
                    )}
                </div>
            </main>

            {/* Export Selection Modal */}
            {isExportModalOpen && (
                <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-[#0b1121] border border-slate-700/50 rounded shadow-2xl p-6 w-full max-w-md animate-fade-in-up">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-black text-white uppercase tracking-tighter flex items-center gap-2">
                                <span className={`material-symbols-outlined ${exportType === 'pdf' ? 'text-rose-500' : 'text-emerald-500'}`}>
                                    {exportType === 'pdf' ? 'picture_as_pdf' : 'table_view'}
                                </span>
                                Opciones de Exportación
                            </h2>
                            <button onClick={closeExportModal} className="text-slate-500 hover:text-white transition-colors">
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>
                        
                        <p className="text-sm text-slate-400 mb-6">¿Qué rango de clientes deseas incluir en el documento {exportType === 'pdf' ? 'PDF' : 'Excel'}?</p>
                        
                        <div className="flex flex-col gap-3">
                            <button onClick={() => handleExportList('all')} className="bg-slate-800 hover:bg-slate-700 text-left px-5 py-4 rounded transition-colors flex flex-col group border border-transparent hover:border-primary/30">
                                <span className="font-bold text-white group-hover:text-primary transition-colors">Todos los clientes</span>
                                <span className="text-xs text-slate-400 mt-1">Exportará el padrón completo registrado en el sistema.</span>
                            </button>
                            
                            <div className="bg-slate-800 px-5 py-4 rounded flex flex-col group border border-transparent">
                                <span className="font-bold text-white mb-2">Por Rango de Cliente</span>
                                <span className="text-xs text-slate-400 mb-4">Exportará los clientes cuyo ID se encuentre en este rango.</span>
                                
                                <div className="flex items-center gap-4 mb-5">
                                    <div className="w-1/2 flex flex-col items-center">
                                        <label className="text-[10px] text-slate-500 uppercase tracking-widest mb-1.5 font-bold text-center">Cliente Inicial (ID)</label>
                                        <input 
                                            type="number" 
                                            min="1"
                                            value={startClientId}
                                            onChange={e => setStartClientId(e.target.value)}
                                            className="bg-slate-900/50 border border-slate-700/50 rounded-sm px-3 py-1.5 text-center text-white font-mono text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-slate-600 shadow-inner w-full"
                                            placeholder="Ej. 1"
                                        />
                                    </div>
                                    <div className="w-1/2 flex flex-col items-center">
                                        <label className="text-[10px] text-slate-500 uppercase tracking-widest mb-1.5 font-bold text-center">Cliente Final (ID)</label>
                                        <input 
                                            type="number" 
                                            min="1"
                                            value={endClientId}
                                            onChange={e => setEndClientId(e.target.value)}
                                            className="bg-slate-900/50 border border-slate-700/50 rounded-sm px-3 py-1.5 text-center text-white font-mono text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-slate-600 shadow-inner w-full"
                                            placeholder="Ej. 50"
                                        />
                                    </div>
                                </div>
                                <button 
                                    onClick={() => handleExportList('range')} 
                                    disabled={!startClientId || !endClientId}
                                    className="w-full bg-primary/20 hover:bg-primary/30 text-primary border border-primary/50 transition-colors py-2 rounded text-xs font-bold uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Exportar Rango
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CreditoCobranza;
