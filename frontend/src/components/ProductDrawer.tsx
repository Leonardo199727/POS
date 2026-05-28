import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../api/axios';

// Props para controlar el Drawer desde Products.tsx
interface ProductDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (productData: any) => void;
    isLoading?: boolean;
    // Opcional: Para el futuro estado de "Edición"
    initialData?: any;
}

export const ProductDrawer: React.FC<ProductDrawerProps> = ({
    isOpen,
    onClose,
    onSave,
    isLoading = false,
    initialData = null
}) => {
    const { user, token } = useContext(AuthContext);
    const isAdmin = user?.rol === 'ADMIN';

    const [autoGenerateCode, setAutoGenerateCode] = useState(true);

    // Estado inicial del formulario (Basado en el Schema del Backend)
    const emptyForm = {
        nombre: '',
        categoria_id: '',
        marca_nombre: '',
        precio_compra: '',
        precio_contado: '',
        precio_credito: '',
        stock_inicial: '',
        stock_minimo: '',
        sku: '',
        codigo_barras: ''
    };

    const [formData, setFormData] = useState(emptyForm);

    const [tieneVariantes, setTieneVariantes] = useState(false);
    const [variantes, setVariantes] = useState([
        { id: Date.now(), nombre: '', sku: '', codigo_barras: '', stock_inicial: '', precio_contado: '', precio_credito: '', precio_compra: '' }
    ]);

    const addVariante = () => {
        setVariantes([...variantes, { id: Date.now(), nombre: '', sku: '', codigo_barras: '', stock_inicial: '', precio_contado: '', precio_credito: '', precio_compra: '' }]);
    };
    const removeVariante = (idToRemove: number) => {
        setVariantes(variantes.filter(v => v.id !== idToRemove));
    };
    const handleVarianteChange = (id: number, field: string, value: string) => {
        setVariantes(variantes.map(v => v.id === id ? { ...v, [field]: value } : v));
    };

    const [categorias, setCategorias] = useState<{ id: number, nombre: string }[]>([]);
    const [marcas, setMarcas] = useState<{ id: number, nombre: string }[]>([]);

    useEffect(() => {
        const fetchFilters = async () => {
            if (!token) return;
            try {
                const [catsRes, marcasRes] = await Promise.all([
                    api.get('categorias/', { headers: { Authorization: `Token ${token}` } }),
                    api.get('marcas/', { headers: { Authorization: `Token ${token}` } })
                ]);
                setCategorias(catsRes.data);
                setMarcas(marcasRes.data);
            } catch (error) {
                console.error("Error fetching categorias/marcas", error);
            }
        };
        fetchFilters();
    }, [token]);

    useEffect(() => {
        if (isOpen) {
            if (initialData) {
                // Modo Edición: Mapear datos del Padre + Variante Seleccionada
                const isEditingSpecificVariant = !!initialData.variantToEdit;
                const targetVariant = isEditingSpecificVariant ? initialData.variantToEdit : (initialData.variantes?.find((v: any) => v.es_default) || initialData.variantes?.[0] || {});

                setFormData({
                    nombre: initialData.nombre || '',
                    categoria_id: initialData.categoria_id?.toString() || initialData.categoria?.id?.toString() || '',
                    marca_nombre: initialData.marca_nombre || initialData.marca?.nombre || '',
                    precio_compra: initialData.precio_compra?.toString() || targetVariant.precio_compra?.toString() || '',
                    precio_contado: initialData.precio_contado?.toString() || targetVariant.precio_contado?.toString() || '',
                    precio_credito: initialData.precio_credito?.toString() || targetVariant.precio_credito?.toString() || '',
                    stock_inicial: initialData.stock_inicial?.toString() || targetVariant.stock_actual?.toString() || '', // Usamos stock_actual/stock_inicial
                    stock_minimo: initialData.stock_minimo?.toString() || targetVariant.stock_minimo?.toString() || '',
                    sku: initialData.sku || targetVariant.sku || '',
                    codigo_barras: initialData.codigo_barras || targetVariant.codigo_barras || ''
                });
                setAutoGenerateCode(false); // En edición, asumimos que ya tiene código a menos que lo borren
                setTieneVariantes(false);

                // Si es producto simple (1 variante), permitir agregar variantes
                const variantCount = initialData.variantes?.length || 0;
                if (variantCount <= 1) {
                    // Pre-popular la variante existente en el builder para cuando se active el toggle
                    setVariantes([{
                        id: Date.now(),
                        nombre: targetVariant.nombre || 'Principal',
                        sku: targetVariant.sku || initialData.sku || '',
                        codigo_barras: targetVariant.codigo_barras || initialData.codigo_barras || '',
                        stock_inicial: targetVariant.stock_actual?.toString() || initialData.stock_inicial?.toString() || '',
                        precio_contado: '',
                        precio_credito: '',
                        precio_compra: ''
                    }]);
                }
            } else {
                setFormData(emptyForm);
                setTieneVariantes(false);
                setVariantes([{ id: Date.now(), nombre: '', sku: '', codigo_barras: '', stock_inicial: '', precio_contado: '', precio_credito: '', precio_compra: '' }]);
                setAutoGenerateCode(true);
            }
        } else {
            setFormData(emptyForm);
            setTieneVariantes(false);
        }
    }, [isOpen, initialData]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        // Limpiar campos numéricos o inyectables si están vacíos
        const cleanData: any = { ...formData };
        // En modo edición, NO eliminar precios/stock del payload para que el backend los procese
        const autoDeleteIfEmpty = initialData
            ? ['categoria_id', 'marca_id']
            : ['categoria_id', 'marca_id', 'precio_compra', 'precio_contado', 'precio_credito', 'stock_inicial', 'stock_minimo'];
        Object.keys(cleanData).forEach(key => {
            if (cleanData[key] === '') {
                if (autoDeleteIfEmpty.includes(key)) {
                    delete cleanData[key];
                }
            }
        });

        const cleanVariantes = variantes.map(v => {
            const vCopy: any = { ...v };
            Object.keys(vCopy).forEach(key => {
                if (vCopy[key] === '') {
                    delete vCopy[key];
                }
            });
            return vCopy;
        });

        if (initialData) {
            const addingVariants = tieneVariantes && variantes.length > 0;
            onSave({
                ...cleanData,
                isEdit: true,
                productId: initialData.productId || initialData.id,
                variantId: initialData.variantId || (initialData.variantToEdit ? initialData.variantToEdit.id : (initialData.variantes?.find((v: any) => v.es_default) || initialData.variantes?.[0])?.id),
                auto_generar_codigo: autoGenerateCode,
                tiene_variantes: addingVariants,
                variantes: addingVariants ? cleanVariantes.slice(1) : [] // Solo enviar las NUEVAS (índice > 0)
            });
        } else {
            onSave({
                ...cleanData,
                auto_generar_codigo: autoGenerateCode,
                tiene_variantes: tieneVariantes,
                variantes: tieneVariantes ? cleanVariantes : []
            });
        }
    };

    // Si no está abierto, no renderizamos nada (o podríamos usar transform translateX para animación)
    // Usaremos un renderizado condicional simple combinado con animaciones de Tailwind si es requerido.
    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop / Overlay oscuro y blur */}
            <div
                className="fixed inset-0 bg-[#0b1121]/80 backdrop-blur-sm z-40 flex items-center justify-center transition-opacity"
                onClick={onClose}
            ></div>

            {/* Product Drawer Container */}
            <div
                className="fixed inset-y-0 right-0 w-full max-w-[450px] bg-[#0f1523] border-l border-slate-700 shadow-2xl z-50 flex flex-col transform transition-transform duration-300 translate-x-0"
            >
                <form onSubmit={handleSubmit} className="flex flex-col h-full">

                    {/* Header */}
                    <header className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between shrink-0">
                        <div className="flex items-center gap-3">
                            <span className="material-symbols-outlined text-primary text-2xl">
                                {initialData ? 'edit_square' : 'inventory_2'}
                            </span>
                            <div>
                                <h2 className="text-slate-100 text-lg font-bold tracking-tight uppercase">
                                    {initialData ? 'Editar Producto' : 'Nuevo Producto'}
                                </h2>
                                <p className="text-[10px] uppercase font-mono tracking-[0.2em] text-slate-500">
                                    {initialData
                                        ? (initialData.variantToEdit ? `VARIANTE: ${initialData.variantToEdit.nombre}` : `CÓDIGO: ${initialData.codigo_interno || 'S/C'}`)
                                        : 'CÓDIGO AUTO-GENERADO'}
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

                        {/* Card 1: General */}
                        <section className="bg-slate-900 border border-slate-800/80 p-5 rounded-sm space-y-4 shadow-sm">
                            <div className="flex items-center gap-2 mb-2">
                                <span className="material-symbols-outlined text-primary text-sm">info</span>
                                <h3 className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500">Información General</h3>
                            </div>

                            <div className="space-y-4">
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Nombre del Producto *</label>
                                    <input
                                        name="nombre"
                                        value={formData.nombre}
                                        onChange={handleChange}
                                        required
                                        className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono"
                                        placeholder="Ej. Rodamiento Industrial SKF"
                                        type="text"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="flex flex-col gap-1.5">
                                        <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Categoría</label>
                                        <select
                                            name="categoria_id"
                                            value={formData.categoria_id}
                                            onChange={handleChange}
                                            className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono appearance-none"
                                        >
                                            <option value="">Seleccionar...</option>
                                            {categorias.map(cat => (
                                                <option key={cat.id} value={cat.id}>{cat.nombre}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="flex flex-col gap-1.5">
                                        <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Marca</label>
                                        <div className="relative">
                                            <input
                                                name="marca_nombre"
                                                value={formData.marca_nombre}
                                                onChange={handleChange}
                                                list="marcas-list"
                                                className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono"
                                                placeholder="Seleccionar o escribir nueva..."
                                                type="text"
                                                autoComplete="off"
                                            />
                                            <datalist id="marcas-list">
                                                {marcas.map(marca => (
                                                    <option key={marca.id} value={marca.nombre} />
                                                ))}
                                            </datalist>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Card 2: Precios */}
                        <section className="bg-slate-900 border border-slate-800/80 p-5 rounded-sm space-y-4 shadow-sm">
                            <div className="flex items-center gap-2 mb-2">
                                <span className="material-symbols-outlined text-primary text-sm">payments</span>
                                <h3 className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500">Esquema de Precios</h3>
                            </div>

                            <div className={`grid ${isAdmin ? 'grid-cols-3' : 'grid-cols-2'} gap-3`}>
                                {isAdmin && (
                                    <div className="flex flex-col gap-1.5">
                                        <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 text-center">Compra</label>
                                        <div className="relative">
                                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-primary font-mono text-sm">$</span>
                                            <input
                                                name="precio_compra"
                                                value={formData.precio_compra}
                                                onChange={handleChange}
                                                className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 font-mono text-right focus:outline-none focus:border-primary transition-all text-sm py-2 pl-6 pr-3 placeholder-slate-600"
                                                placeholder="0.00"
                                                step="0.01"
                                                type="number"
                                            />
                                        </div>
                                    </div>
                                )}

                                <div className="flex flex-col gap-1.5">
                                    <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 text-center">Contado *</label>
                                    <div className="relative">
                                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-primary font-mono text-sm">$</span>
                                        <input
                                            name="precio_contado"
                                            value={formData.precio_contado}
                                            onChange={handleChange}
                                            required
                                            className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 font-mono text-right focus:outline-none focus:border-primary transition-all text-sm py-2 pl-6 pr-3 placeholder-slate-600"
                                            placeholder="0.00"
                                            step="0.01"
                                            type="number"
                                        />
                                    </div>
                                </div>

                                <div className="flex flex-col gap-1.5">
                                    <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 text-center">Crédito *</label>
                                    <div className="relative">
                                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-primary font-mono text-sm">$</span>
                                        <input
                                            name="precio_credito"
                                            value={formData.precio_credito}
                                            onChange={handleChange}
                                            required
                                            className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 font-mono text-right focus:outline-none focus:border-primary transition-all text-sm py-2 pl-6 pr-3 placeholder-slate-600"
                                            placeholder="0.00"
                                            step="0.01"
                                            type="number"
                                        />
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Layout Toggle Variantes */}
                        {(!initialData || (initialData && (initialData.variantes?.length || 0) <= 1 && !initialData.variantToEdit)) && (
                            <div className="flex items-center gap-3 bg-slate-900 border border-slate-800/80 p-4 rounded-sm shadow-sm transition-all">
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input type="checkbox" className="sr-only peer" checked={tieneVariantes} onChange={(e) => setTieneVariantes(e.target.checked)} />
                                    <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                                </label>
                                <span className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-400">
                                    {initialData ? '¿Expandir a múltiples variantes?' : '¿Habilitar variantes (Tallas/Colores)?'}
                                </span>
                            </div>
                        )}

                        {/* Card 3: Inventario (Oculto si hay variantes) */}
                        {!tieneVariantes && (
                            <section className="bg-slate-900 border border-slate-800/80 p-5 rounded-sm space-y-4 shadow-sm">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="material-symbols-outlined text-primary text-sm">inventory</span>
                                    <h3 className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500">Gestión de Inventario</h3>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    {!tieneVariantes && (
                                        <div className="flex flex-col gap-1.5">
                                            <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Stock Actual *</label>
                                            <input
                                                name="stock_inicial"
                                                value={formData.stock_inicial}
                                                onChange={handleChange}
                                                required={!tieneVariantes}
                                                className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono placeholder-slate-600"
                                                placeholder="0"
                                                type="number"
                                            />
                                        </div>
                                    )}

                                    <div className="flex flex-col gap-1.5">
                                        <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Stock Mínimo</label>
                                        <input
                                            name="stock_minimo"
                                            value={formData.stock_minimo}
                                            onChange={handleChange}
                                            className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono placeholder-slate-600"
                                            placeholder="5"
                                            type="number"
                                        />
                                    </div>
                                </div>
                            </section>
                        )}

                        {/* Card 4: Códigos (Sólo si no hay variantes) */}
                        {!tieneVariantes && (
                            <section className="bg-slate-900 border border-slate-800/80 p-5 rounded-sm space-y-4 shadow-sm">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="material-symbols-outlined text-primary text-sm">qr_code_scanner</span>
                                    <h3 className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500">Identificadores</h3>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex flex-col gap-1.5">
                                        <div className="flex items-center justify-between pr-1">
                                            <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">SKU / Referencia Interna</label>
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="checkbox"
                                                    id="auto-gen"
                                                    checked={autoGenerateCode}
                                                    onChange={(e) => setAutoGenerateCode(e.target.checked)}
                                                    className="rounded bg-slate-900 border-slate-700 text-primary focus:ring-primary focus:ring-offset-slate-900 cursor-pointer"
                                                />
                                                <label htmlFor="auto-gen" className="text-[10px] text-slate-400 cursor-pointer select-none">Auto</label>
                                            </div>
                                        </div>
                                        <input
                                            name="sku"
                                            value={formData.sku}
                                            onChange={handleChange}
                                            disabled={autoGenerateCode}
                                            className="w-full bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono disabled:opacity-50 disabled:bg-slate-800"
                                            placeholder={autoGenerateCode ? "Generado automáticamente" : "Ej. LMS-10293"}
                                            type="text"
                                        />
                                    </div>

                                    <div className="flex flex-col gap-1.5">
                                        <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500 ml-1">Código de Barras (EAN/UPC)</label>
                                        <div className="flex gap-2">
                                            <input
                                                name="codigo_barras"
                                                value={formData.codigo_barras}
                                                onChange={handleChange}
                                                className="flex-1 bg-slate-900 border border-slate-800/80 rounded-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary transition-all text-sm py-2 px-3 font-mono"
                                                placeholder="Escanee o ingrese código"
                                                type="text"
                                            />
                                            <button
                                                type="button"
                                                className="bg-slate-800 border border-slate-700 text-slate-400 hover:text-primary hover:border-primary/50 w-12 flex items-center justify-center rounded-sm transition-colors"
                                            >
                                                <span className="material-symbols-outlined text-lg">barcode_scanner</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </section>
                        )}

                        {/* Card 5: Múltiples Variantes */}
                        {tieneVariantes && (
                            <section className="bg-slate-900 border border-slate-800/80 p-5 rounded-sm space-y-4 shadow-sm">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <span className="material-symbols-outlined text-primary text-sm">style</span>
                                        <h3 className="text-[10px] uppercase font-bold tracking-[0.2em] text-slate-500">Lista de Variantes</h3>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={addVariante}
                                        className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold uppercase tracking-widest py-1.5 px-3 rounded-sm transition-colors border border-slate-700 flex items-center gap-1"
                                    >
                                        <span className="material-symbols-outlined text-sm">add</span> Add Variante
                                    </button>
                                </div>

                                <div className="space-y-3">
                                    {variantes.map((v) => (
                                        <div key={v.id} className="bg-slate-950/50 p-3 border border-slate-800 rounded-sm relative group space-y-2">
                                            {variantes.length > 1 && (
                                                <button
                                                    type="button"
                                                    onClick={() => removeVariante(v.id)}
                                                    className="absolute -right-2 -top-2 bg-slate-800 text-rose-500 border border-slate-700 rounded-full w-6 h-6 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10 hover:bg-rose-500/20"
                                                >
                                                    <span className="material-symbols-outlined text-[14px]">close</span>
                                                </button>
                                            )}

                                            {/* Fila 1: Nombre, Stock, SKU */}
                                            <div className="grid grid-cols-12 gap-3 items-start">
                                                <div className="col-span-4">
                                                    <label className="text-[9px] uppercase font-bold tracking-[0.2em] text-slate-500 mb-1 block">Nombre *</label>
                                                    <input
                                                        required={tieneVariantes}
                                                        value={v.nombre}
                                                        onChange={e => handleVarianteChange(v.id, 'nombre', e.target.value)}
                                                        className="w-full bg-slate-900 border border-slate-700 rounded-sm text-slate-200 focus:outline-none focus:border-primary text-xs py-1.5 px-2"
                                                        placeholder="255/45 R17"
                                                        type="text"
                                                    />
                                                </div>
                                                <div className="col-span-3">
                                                    <label className="text-[9px] uppercase font-bold tracking-[0.2em] text-slate-500 mb-1 block">Stock *</label>
                                                    <input
                                                        required={tieneVariantes}
                                                        value={v.stock_inicial}
                                                        onChange={e => handleVarianteChange(v.id, 'stock_inicial', e.target.value)}
                                                        className="w-full bg-slate-900 border border-slate-700 rounded-sm text-slate-200 focus:outline-none focus:border-primary text-xs py-1.5 px-2 font-mono"
                                                        placeholder="0"
                                                        type="number"
                                                    />
                                                </div>
                                                <div className="col-span-5">
                                                    <label className="text-[9px] uppercase font-bold tracking-[0.2em] text-slate-500 mb-1 block">SKU / CB</label>
                                                    <input
                                                        value={v.sku}
                                                        onChange={e => handleVarianteChange(v.id, 'sku', e.target.value)}
                                                        className="w-full bg-slate-900 border border-slate-700 rounded-sm text-slate-200 focus:outline-none focus:border-primary text-xs py-1.5 px-2 font-mono placeholder-slate-600"
                                                        placeholder="SKU Opcional"
                                                        type="text"
                                                    />
                                                </div>
                                            </div>

                                            {/* Fila 2: Precios individuales (opcionales, override del precio base) */}
                                            <div className={`grid ${isAdmin ? 'grid-cols-3' : 'grid-cols-2'} gap-2`}>
                                                <div>
                                                    <label className="text-[9px] uppercase font-bold tracking-[0.2em] text-slate-500 mb-1 block">Contado</label>
                                                    <div className="relative">
                                                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-primary font-mono text-[10px]">$</span>
                                                        <input
                                                            value={v.precio_contado}
                                                            onChange={e => handleVarianteChange(v.id, 'precio_contado', e.target.value)}
                                                            className="w-full bg-slate-900 border border-slate-700 rounded-sm text-slate-200 font-mono text-right focus:outline-none focus:border-primary text-xs py-1.5 pl-5 pr-2 placeholder-slate-600"
                                                            placeholder="Heredar base"
                                                            step="0.01"
                                                            type="number"
                                                        />
                                                    </div>
                                                </div>
                                                <div>
                                                    <label className="text-[9px] uppercase font-bold tracking-[0.2em] text-slate-500 mb-1 block">Crédito</label>
                                                    <div className="relative">
                                                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-primary font-mono text-[10px]">$</span>
                                                        <input
                                                            value={v.precio_credito}
                                                            onChange={e => handleVarianteChange(v.id, 'precio_credito', e.target.value)}
                                                            className="w-full bg-slate-900 border border-slate-700 rounded-sm text-slate-200 font-mono text-right focus:outline-none focus:border-primary text-xs py-1.5 pl-5 pr-2 placeholder-slate-600"
                                                            placeholder="Heredar base"
                                                            step="0.01"
                                                            type="number"
                                                        />
                                                    </div>
                                                </div>
                                                {isAdmin && (
                                                    <div>
                                                        <label className="text-[9px] uppercase font-bold tracking-[0.2em] text-slate-500 mb-1 block">Compra</label>
                                                        <div className="relative">
                                                            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-primary font-mono text-[10px]">$</span>
                                                            <input
                                                                value={v.precio_compra}
                                                                onChange={e => handleVarianteChange(v.id, 'precio_compra', e.target.value)}
                                                                className="w-full bg-slate-900 border border-slate-700 rounded-sm text-slate-200 font-mono text-right focus:outline-none focus:border-primary text-xs py-1.5 pl-5 pr-2 placeholder-slate-600"
                                                                placeholder="Heredar base"
                                                                step="0.01"
                                                                type="number"
                                                            />
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

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
                                {initialData ? 'Guardar Cambios' : 'Guardar Producto'}
                            </span>
                        </button>
                    </footer>
                </form>
            </div>
        </>
    );
};
