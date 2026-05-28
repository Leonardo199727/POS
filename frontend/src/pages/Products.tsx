import { useState, useEffect, useContext } from "react";
import { Sidebar } from "../components/Sidebar";
import { AuthContext } from "../context/AuthContext";
import api from "../api/axios";
import { useDebounce } from "../hooks/useDebounce";
import { ProductDrawer } from "../components/ProductDrawer";
import { useRefresh } from "../context/RefreshContext";

interface ProductMeta {
    count: number;
    total_pages: number;
    current_page: number;
    next: string | null;
    previous: string | null;
}

export const Products = () => {
    const { user, token } = useContext(AuthContext);
    const { refreshKey } = useRefresh();
    const [products, setProducts] = useState<any[]>([]);
    const [meta, setMeta] = useState<ProductMeta | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [searchTerm, setSearchTerm] = useState("");
    const [isLoading, setIsLoading] = useState(true);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [drawerMode, setDrawerMode] = useState<'CREATE' | 'EDIT'>('CREATE');
    const [selectedProductToEdit, setSelectedProductToEdit] = useState<any | null>(null);
    const [selectedVariantProduct, setSelectedVariantProduct] = useState<any | null>(null);

    // Filters
    const [marcas, setMarcas] = useState<{ id: number, nombre: string }[]>([]);
    const [selectedMarca, setSelectedMarca] = useState("");
    const [marcaSearchInput, setMarcaSearchInput] = useState("");
    const [isMarcaDropdownOpen, setIsMarcaDropdownOpen] = useState(false);

    const debouncedSearchTerm = useDebounce(searchTerm, 500);

    const fetchProducts = async (page: number, search: string, marca: string = "") => {
        try {
            setIsLoading(true);
            const queryParams = new URLSearchParams({ page: page.toString() });
            if (search) queryParams.append("search", search);
            if (marca) queryParams.append("marca", marca);

            const response = await api.get(`productos/?${queryParams.toString()}`, {
                headers: { Authorization: `Token ${token}` }
            });
            if (response.data.success) {
                setProducts(response.data.data);
                setMeta(response.data.meta);
            }
        } catch (error) {
            console.error("Error fetching products:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchMarcas = async () => {
        if (!token) return;
        try {
            const res = await api.get('marcas/', { headers: { Authorization: `Token ${token}` } });
            setMarcas(res.data);
        } catch (err) {
            console.error("Error fetching marcas:", err);
        }
    };

    useEffect(() => {
        fetchMarcas();
    }, [token]);

    useEffect(() => {
        setCurrentPage(1); // Reset page on new search or filter change
        fetchProducts(1, debouncedSearchTerm, selectedMarca);
    }, [debouncedSearchTerm, selectedMarca, token, refreshKey]);

    useEffect(() => {
        // Fetch when page changes, but guard against duplicate early fetches
        if (currentPage !== 1 || !debouncedSearchTerm && !selectedMarca) {
            fetchProducts(currentPage, debouncedSearchTerm, selectedMarca);
        }
    }, [currentPage]);

    const handleSaveProduct = async (productData: any) => {
        try {
            console.log("Guardando producto: ", productData);
            setIsLoading(true);

            // Extracción de metadatos de edición
            const { isEdit, productId, variantId, ...restPayload } = productData;

            // Re-inyectamos el variant_id al payload para que el backend sepa que Variante actualizar
            const payloadToSend = { ...restPayload };
            if (variantId) {
                payloadToSend.variant_id = variantId;
            }

            let res;
            if (isEdit) {
                // Modo Edición: usar PATCH hacia el ID del producto
                res = await api.patch(`productos/${productId}/`, payloadToSend, {
                    headers: { Authorization: `Token ${token}` }
                });
            } else {
                // Modo Creación: usar POST
                res = await api.post('productos/', payloadToSend, {
                    headers: { Authorization: `Token ${token}` }
                });
            }

            if (res.status === 200 || res.status === 201) {
                setIsDrawerOpen(false);
                setDrawerMode('CREATE');
                setSelectedProductToEdit(null);
                fetchProducts(1, "");
                fetchMarcas(); // Refrescar filtro de marcas (pudo haberse creado una nueva)
                alert(`✅ Producto ${isEdit ? 'actualizado' : 'creado'} con éxito`);
            }
        } catch (error: any) {
            console.error("Error al guardar producto", error.response?.data || error);
            const errorMsg = error.response?.data ? JSON.stringify(error.response.data, null, 2) : "Ocurrió un error desconocido";
            alert(`❌ Ocurrió un error al guardar el producto:\n\n${errorMsg}`);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background-dark text-slate-100 font-display">
            {/* Sidebar real de la app */}
            <Sidebar />

            {/* Contenedor Principal (Derecho) */}
            <div className="flex-1 flex flex-col bg-slate-900 overflow-hidden">
                <header className="p-4 bg-slate-950 border-b border-slate-800">
                    <div className="flex items-center gap-4">
                        <div className="flex-1 relative">
                            <span className="absolute left-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500">search</span>
                            <input
                                autoFocus
                                className="w-full bg-slate-900 border border-slate-700 text-slate-100 py-4 pl-12 pr-12 focus:border-primary focus:outline-none focus:ring-0 text-sm tracking-wider uppercase rounded-sm transition-all"
                                placeholder="BUSCAR PRODUCTO O ESCANEAR CÓDIGO..."
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                            <span className="absolute right-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-primary cursor-pointer hover:scale-110 transition-transform">barcode_scanner</span>
                        </div>

                        <div className="w-1/4 min-w-[200px] relative">
                            <input
                                type="text"
                                placeholder="FILTRAR POR MARCA..."
                                value={marcaSearchInput}
                                onChange={(e) => {
                                    setMarcaSearchInput(e.target.value);
                                    setIsMarcaDropdownOpen(true);
                                    if (e.target.value === "") {
                                        setSelectedMarca(""); // Reset si se vacía
                                    }
                                }}
                                onFocus={() => setIsMarcaDropdownOpen(true)}
                                onBlur={() => setTimeout(() => setIsMarcaDropdownOpen(false), 200)}
                                className="w-full bg-slate-900 border border-slate-700 text-slate-100 py-4 pl-4 pr-10 focus:border-primary focus:outline-none focus:ring-0 text-sm tracking-wider uppercase rounded-sm transition-all placeholder:text-slate-500"
                            />
                            {marcaSearchInput && (
                                <button
                                    onClick={() => {
                                        setMarcaSearchInput("");
                                        setSelectedMarca("");
                                        setIsMarcaDropdownOpen(false);
                                    }}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                                >
                                    <span className="material-symbols-outlined text-sm">close</span>
                                </button>
                            )}

                            {/* Autocomplete Dropdown */}
                            {isMarcaDropdownOpen && marcaSearchInput.trim().length >= 2 && (
                                <ul className="absolute z-50 w-full mt-1 bg-slate-800 border border-slate-700 rounded-sm shadow-xl max-h-60 overflow-y-auto">
                                    {marcas
                                        .filter(m => m.nombre.toLowerCase().includes(marcaSearchInput.toLowerCase()))
                                        .map(marca => (
                                            <li
                                                key={marca.id}
                                                className="px-4 py-3 text-sm text-slate-300 hover:bg-primary hover:text-white cursor-pointer uppercase tracking-wider border-b border-slate-700/50 last:border-0"
                                                onClick={() => {
                                                    setSelectedMarca(marca.id.toString());
                                                    setMarcaSearchInput(marca.nombre);
                                                    setIsMarcaDropdownOpen(false);
                                                }}
                                            >
                                                {marca.nombre}
                                            </li>
                                        ))}
                                    {marcas.filter(m => m.nombre.toLowerCase().includes(marcaSearchInput.toLowerCase())).length === 0 && (
                                        <li className="px-4 py-3 text-sm text-slate-500 uppercase tracking-wider text-center">
                                            Sin coincidencias
                                        </li>
                                    )}
                                </ul>
                            )}
                        </div>
                        <div className="flex items-center gap-2 px-4 py-3 bg-slate-800 border border-slate-700 rounded-sm">
                            <span className="material-symbols-outlined text-slate-400">person</span>
                            <span className="text-xs font-bold uppercase text-slate-300 tracking-widest">
                                Operador: {user?.username || "Desconocido"}
                            </span>
                        </div>
                    </div>
                </header>
                <main className="flex-1 p-8 flex flex-col min-h-0 bg-[#0f1523]">
                    <div className="flex items-center justify-between mb-8 shrink-0">
                        <div>
                            <h2 className="text-3xl font-black text-white tracking-tight">Gestión de Productos</h2>
                            <p className="text-slate-400 text-sm mt-1">Visualización del catálogo maestro de componentes industriales.</p>
                        </div>
                        <button
                            onClick={() => {
                                setDrawerMode('CREATE');
                                setSelectedProductToEdit(null);
                                setIsDrawerOpen(true);
                            }}
                            className="bg-primary hover:bg-orange-600 text-white font-bold py-3 px-6 flex items-center gap-2 transition-colors rounded-sm shadow-lg shadow-primary/20"
                        >
                            <span className="material-symbols-outlined">add</span>
                            NUEVO PRODUCTO
                        </button>
                    </div>
                    <div className="bg-slate-900 border border-slate-700 rounded-sm overflow-hidden flex-1 relative flex flex-col min-h-0 shadow-lg">
                        <div className="flex-1 overflow-auto w-full pb-14">
                            <table className="w-full text-left text-sm text-slate-300 border-collapse">
                                <thead className="bg-[#0b1121] border-y border-slate-700 text-[10px] uppercase text-slate-500 font-bold tracking-[0.2em] sticky top-0 z-10 shadow-sm">
                                    <tr>
                                        <th scope="col" className="px-6 py-4 w-[15%]">Código Interno</th>
                                        <th scope="col" className="px-6 py-4 w-[35%]">Producto</th>
                                        <th scope="col" className="px-6 py-4 w-[15%]">Marca / Cat</th>
                                        <th scope="col" className="px-6 py-4 text-right w-[10%]">Existencias</th>
                                        <th scope="col" className="px-6 py-4 text-right w-[15%]">Precio de Contado</th>
                                        <th scope="col" className="px-6 py-4 text-center w-[10%]">Acción</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {isLoading ? (
                                        <tr>
                                            <td colSpan={6} className="px-6 py-12 text-center text-slate-500 font-medium tracking-widest text-[11px]">
                                                <div className="flex items-center justify-center gap-3">
                                                    <span className="material-symbols-outlined animate-spin text-primary">progress_activity</span>
                                                    CARGANDO CATÁLOGO...
                                                </div>
                                            </td>
                                        </tr>
                                    ) : products.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="px-6 py-8 text-center text-slate-500 font-medium">
                                                <div className="flex flex-col items-center justify-center gap-2">
                                                    <span className="material-symbols-outlined text-red-500/50 text-5xl">inventory_2</span>
                                                    <p className="text-[10px] uppercase font-bold tracking-[0.2em] mt-2">NO SE ENCONTRARON PRODUCTOS</p>
                                                </div>
                                            </td>
                                        </tr>
                                    ) : (
                                        products.flatMap((prod) => {
                                            const normalizeText = (text: string) => text ? text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase() : '';

                                            const term = normalizeText(debouncedSearchTerm.trim());
                                            const matchesParent = normalizeText(prod.nombre).includes(term) || normalizeText(prod.codigo_interno).includes(term);

                                            const matchingVariants = prod.variantes?.filter((v: any) =>
                                                (v.sku && normalizeText(v.sku).includes(term)) ||
                                                (v.codigo_barras && normalizeText(v.codigo_barras) === term) ||
                                                (v.nombre && normalizeText(v.nombre).includes(term))
                                            ) || [];

                                            const isVariantSpecific = term.length > 0 && !matchesParent && matchingVariants.length > 0;

                                            // Si la búsqueda coincide con variantes específicas, generar UNA fila por cada variante
                                            const rowsToRender = isVariantSpecific
                                                ? matchingVariants.map((v: any) => ({ variant: v, isSpecific: true }))
                                                : [{ variant: prod.variantes?.find((v: any) => v.es_default) || prod.variantes?.[0], isSpecific: false }];

                                            return rowsToRender.map(({ variant: displayVariant, isSpecific }: any) => {
                                                const displayCode = isSpecific ? displayVariant?.sku : (prod.codigo_interno || 'S/C');
                                                const displayName = isSpecific ? `${prod.nombre} - ${displayVariant?.nombre}` : prod.nombre;
                                                const displayStock = isSpecific ? (displayVariant?.stock_actual || 0) : (prod.stock_disponible || 0);
                                                const displayPrice = isSpecific ? (displayVariant?.precio_contado || 0) : (prod.precio_contado || 0);

                                                return (
                                                    <tr key={`${prod.id}-${displayVariant?.id || 'default'}`} className="bg-slate-900 border-b border-slate-800/80 hover:bg-slate-800/50 transition-colors group">
                                                        <td className="px-6 py-4 font-mono text-primary font-medium">{displayCode}</td>
                                                        <td className="px-6 py-4 text-slate-100 font-medium">
                                                            {displayName}
                                                            {!isSpecific && displayVariant && !displayVariant.es_default && <span className="ml-2 text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded uppercase tracking-widest">{displayVariant.nombre}</span>}
                                                        </td>
                                                        <td className="px-6 py-4 text-[10px] uppercase tracking-[0.2em]">
                                                            <span className="text-slate-400">{prod.marca?.nombre || 'N/A'}</span>
                                                            <span className="mx-2 text-slate-700">|</span>
                                                            <span className="text-slate-500">{prod.categoria?.nombre || 'Genérico'}</span>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            {displayStock > 0 ? (
                                                                <span className="font-mono flex items-center justify-end gap-1 text-green-400/90 font-bold">
                                                                    <span>{displayStock}</span>
                                                                    <span className="text-[10px] uppercase text-green-600/50">UND</span>
                                                                </span>
                                                            ) : (
                                                                <span className="text-red-500/70 font-mono flex items-center justify-end gap-1 font-bold">
                                                                    <span>0</span>
                                                                    <span className="text-[10px] uppercase text-red-600/30">UND</span>
                                                                </span>
                                                            )}
                                                        </td>
                                                        <td className="px-6 py-4 text-right font-mono text-slate-100 text-lg">
                                                            <span className="text-slate-600 text-sm mr-1">$</span>
                                                            {Number(displayPrice).toFixed(2)}
                                                        </td>
                                                        <td className="px-6 py-4 text-center">
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    if (isSpecific) {
                                                                        // La fila ya muestra una variante específica, editar directamente
                                                                        const editData = {
                                                                            productId: prod.id,
                                                                            variantId: displayVariant?.id,
                                                                            nombre: prod.nombre,
                                                                            categoria_id: prod.categoria?.id || '',
                                                                            marca_nombre: prod.marca?.nombre || '',
                                                                            marca_id: prod.marca?.id || '',
                                                                            precio_compra: displayVariant?.precio_compra?.toString() ?? '',
                                                                            precio_contado: displayVariant?.precio_contado?.toString() ?? '',
                                                                            precio_credito: displayVariant?.precio_credito?.toString() ?? '',
                                                                            stock_inicial: displayVariant?.stock_actual?.toString() ?? '',
                                                                            stock_minimo: displayVariant?.stock_minimo?.toString() ?? '',
                                                                            sku: displayVariant?.sku ?? '',
                                                                            codigo_barras: displayVariant?.codigo_barras ?? '',
                                                                        };
                                                                        setSelectedProductToEdit(editData);
                                                                        setDrawerMode('EDIT');
                                                                        setIsDrawerOpen(true);
                                                                    } else if (prod.variantes && prod.variantes.length > 1) {
                                                                        // Búsqueda general + múltiples variantes → abrir modal de selección
                                                                        setSelectedVariantProduct(prod);
                                                                    } else {
                                                                        // Producto con 1 sola variante → editar directamente
                                                                        const variantToEdit = prod.variantes?.find((v: any) => v.es_default) || prod.variantes?.[0];
                                                                        const editData = {
                                                                            productId: prod.id,
                                                                            variantId: variantToEdit?.id,
                                                                            nombre: prod.nombre,
                                                                            categoria_id: prod.categoria?.id || '',
                                                                            marca_nombre: prod.marca?.nombre || '',
                                                                            marca_id: prod.marca?.id || '',
                                                                            precio_compra: variantToEdit?.precio_compra?.toString() ?? prod.precio_compra?.toString() ?? '',
                                                                            precio_contado: variantToEdit?.precio_contado?.toString() ?? prod.precio_contado?.toString() ?? '',
                                                                            precio_credito: variantToEdit?.precio_credito?.toString() ?? prod.precio_credito?.toString() ?? '',
                                                                            stock_inicial: variantToEdit?.stock_actual?.toString() ?? '',
                                                                            stock_minimo: variantToEdit?.stock_minimo?.toString() ?? '',
                                                                            sku: variantToEdit?.sku ?? '',
                                                                            codigo_barras: variantToEdit?.codigo_barras ?? '',
                                                                        };
                                                                        setSelectedProductToEdit(editData);
                                                                        setDrawerMode('EDIT');
                                                                        setIsDrawerOpen(true);
                                                                    }
                                                                }}
                                                                className="w-full flex items-center justify-center gap-2 bg-primary/10 text-primary border border-primary/30 hover:bg-primary hover:text-white hover:border-primary transition-all rounded-sm px-4 py-2 text-xs font-bold uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
                                                            >
                                                                <span className="material-symbols-outlined text-[16px]">edit</span>
                                                                <span>Editar</span>
                                                            </button>
                                                        </td>
                                                    </tr>
                                                );
                                            });
                                        })
                                    )}
                                </tbody>
                            </table>
                        </div>
                        {/* Paginación */}
                        <div className="h-14 border-t border-slate-800 flex items-center justify-between px-6 bg-slate-900 absolute bottom-0 w-full">
                            <span className="text-xs text-slate-500 font-medium tracking-wider">
                                MOSTRANDO PÁGINA {meta?.current_page || 1} DE {meta?.total_pages || 1} • {meta?.count || 0} TOTALES
                            </span>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => meta?.previous && setCurrentPage(prev => prev - 1)}
                                    disabled={!meta?.previous}
                                    className="w-8 h-8 rounded border border-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors disabled:opacity-50 disabled:bg-slate-800 disabled:hover:border-slate-700 disabled:hover:text-slate-400 disabled:cursor-not-allowed"
                                >
                                    <span className="material-symbols-outlined text-sm">chevron_left</span>
                                </button>
                                <button
                                    onClick={() => meta?.next && setCurrentPage(prev => prev + 1)}
                                    disabled={!meta?.next}
                                    className="w-8 h-8 rounded border border-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors disabled:opacity-50 disabled:bg-slate-800 disabled:hover:border-slate-700 disabled:hover:text-slate-400 disabled:cursor-not-allowed"
                                >
                                    <span className="material-symbols-outlined text-sm">chevron_right</span>
                                </button>
                            </div>
                        </div>
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
            <ProductDrawer
                isOpen={isDrawerOpen}
                onClose={() => {
                    setIsDrawerOpen(false);
                    setSelectedProductToEdit(null);
                }}
                onSave={handleSaveProduct}
                initialData={drawerMode === 'EDIT' ? selectedProductToEdit : null}
            />

            {/* Variant Selection Modal (For Edit) */}
            {selectedVariantProduct && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-background-dark/80 backdrop-blur-sm p-4">
                    <div className="bg-slate-900 border border-slate-700 shadow-2xl rounded-sm w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
                        {/* Modal Header */}
                        <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex justify-between items-center">
                            <div>
                                <h3 className="text-lg font-bold text-slate-100 uppercase tracking-wider">{selectedVariantProduct.nombre}</h3>
                                <p className="text-xs text-slate-500 font-mono mt-1">SELECCIONE QUÉ VARIANTE DESEA EDITAR</p>
                            </div>
                            <button
                                onClick={() => setSelectedVariantProduct(null)}
                                className="text-slate-500 hover:text-white transition-colors"
                            >
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>

                        {/* Modal Body: Variants List */}
                        <div className="p-6 overflow-y-auto flex-1 bg-slate-900">
                            <div className="space-y-3">
                                {selectedVariantProduct.variantes?.map((variante: any) => (
                                    <div
                                        key={variante.id}
                                        className="flex items-center justify-between p-4 bg-slate-800/50 border border-slate-700/50 rounded-sm hover:border-primary/50 transition-colors group"
                                    >
                                        <div className="flex flex-col">
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm font-medium text-slate-200 uppercase tracking-widest">{variante.nombre}</span>
                                                {variante.es_default && <span className="text-[9px] bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded uppercase tracking-widest">Default</span>}
                                            </div>
                                            <span className="text-xs text-slate-500 font-mono mt-1">SKU: {variante.sku} {variante.codigo_barras ? ` | CB: ${variante.codigo_barras}` : ''}</span>
                                        </div>

                                        <div className="flex items-center gap-6">
                                            <div className="text-right flex flex-col items-end">
                                                <span className="text-sm font-mono text-slate-100">${Number(variante.precio_contado || 0).toFixed(2)}</span>
                                                {variante.stock_actual > 0 ? (
                                                    <span className="text-[10px] text-green-400 font-bold uppercase tracking-widest">
                                                        {variante.stock_actual} Existencias
                                                    </span>
                                                ) : (
                                                    <span className="text-[10px] text-red-500 font-bold uppercase tracking-widest">Agotado</span>
                                                )}
                                            </div>
                                            <button
                                                className="bg-primary/20 hover:bg-primary text-primary hover:text-white px-4 py-2 rounded-sm text-xs font-bold uppercase tracking-widest transition-colors flex items-center gap-2"
                                                onClick={() => {
                                                    setSelectedVariantProduct(null);
                                                    setDrawerMode('EDIT');
                                                    setSelectedProductToEdit({ ...selectedVariantProduct, variantToEdit: variante });
                                                    setIsDrawerOpen(true);
                                                }}
                                            >
                                                <span className="material-symbols-outlined text-[16px]">edit</span>
                                                EDITAR
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
