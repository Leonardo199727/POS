import { useState, useEffect, useContext } from "react";
import { Sidebar } from "../components/Sidebar";
import { AuthContext } from "../context/AuthContext";
import { useDebounce } from "../hooks/useDebounce";
import api from "../api/axios";
import { useCart } from "../context/CartContext";
import { useRefresh } from "../context/RefreshContext";

export const Home = () => {
    const { user, token } = useContext(AuthContext);
    const { addToCart } = useCart();
    const { refreshKey } = useRefresh();

    const [searchTerm, setSearchTerm] = useState("");
    const [isSearching, setIsSearching] = useState(false);
    const [results, setResults] = useState<any[]>([]);
    const [selectedVariantProduct, setSelectedVariantProduct] = useState<any>(null);

    const debouncedSearchTerm = useDebounce(searchTerm, 300);

    // ... useEffect remains the same ...
    useEffect(() => {
        if (debouncedSearchTerm.length >= 3) {
            setIsSearching(true);
            api.get(`productos/?search=${debouncedSearchTerm}`, {
                headers: { Authorization: `Token ${token}` }
            })
                .then(res => {
                    setResults(res.data.data);
                })
                .catch(err => console.error(err))
                .finally(() => setIsSearching(false));
        } else {
            setResults([]);
        }
    }, [debouncedSearchTerm, token, refreshKey]);


    return (
        <div className="flex h-screen w-full overflow-hidden bg-background-dark text-slate-100 font-display">
            <Sidebar />

            <main className="flex-1 flex flex-col bg-slate-900 overflow-hidden relative">
                {/* ... header ... */}
                <header className="p-4 bg-slate-950 border-b border-slate-800 shrink-0">
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
                        <div className="flex items-center gap-2 px-4 py-3 bg-slate-800 border border-slate-700 rounded-sm">
                            <span className="material-symbols-outlined text-slate-400">person</span>
                            <span className="text-xs font-bold uppercase text-slate-300 tracking-widest">
                                Operador: {user?.username || "Desconocido"}
                            </span>
                        </div>
                    </div>
                </header>

                <section className="flex-1 bg-slate-900 flex flex-col relative shadow-inner overflow-hidden">
                    {/* ... placeholders & loading ... */}
                    {debouncedSearchTerm.length < 3 && results.length === 0 && (
                        <>
                            <div className="absolute inset-0 flex items-center justify-center opacity-[0.03] pointer-events-none select-none">
                                <span className="material-symbols-outlined text-[20rem]">terminal</span>
                                <h2 className="text-6xl font-bold uppercase tracking-[2rem] -mt-12 absolute">LMSolutions</h2>
                            </div>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <div className="text-center space-y-2 translate-y-[-20px]">
                                    <span className="material-symbols-outlined text-slate-700 text-5xl">search_insights</span>
                                    <p className="text-slate-500 text-xs font-bold uppercase tracking-[0.2em]">Ingrese 3 o más caracteres para buscar</p>
                                </div>
                            </div>
                        </>
                    )}

                    {isSearching && (
                        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-slate-800 text-slate-300 px-4 py-2 rounded-full flex items-center gap-2 shadow-lg z-20">
                            <span className="material-symbols-outlined animate-spin text-sm">cycle</span>
                            <span className="text-xs uppercase font-bold tracking-widest">Buscando...</span>
                        </div>
                    )}

                    {/* Results Table */}
                    {debouncedSearchTerm.length >= 3 && results.length > 0 && (
                        <div className="flex-1 overflow-auto w-full px-6 pb-6 relative z-10">
                            <table className="w-full text-left text-sm text-slate-300 border-collapse">
                                <thead className="bg-[#0b1121] border-y border-slate-700 text-[10px] uppercase text-slate-500 font-bold tracking-[0.2em] sticky top-0 z-10">
                                    <tr>
                                        <th scope="col" className="px-6 py-4">Código Interno</th>
                                        <th scope="col" className="px-6 py-4">Producto</th>
                                        <th scope="col" className="px-6 py-4">Marca / Cat</th>
                                        <th scope="col" className="px-6 py-4 text-right">Existencias</th>
                                        <th scope="col" className="px-6 py-4 text-right">Precio de Contado</th>
                                        <th scope="col" className="px-6 py-4 text-center">Acción</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.flatMap((prod: any) => {
                                        const normalizeText = (text: string) => text ? text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase() : '';

                                        const term = normalizeText(debouncedSearchTerm.trim());
                                        const matchesParent = normalizeText(prod.nombre).includes(term) || normalizeText(prod.codigo_interno).includes(term);

                                        const matchingVariants = prod.variantes?.filter((v: any) =>
                                            (v.sku && normalizeText(v.sku).includes(term)) ||
                                            (v.codigo_barras && normalizeText(v.codigo_barras) === term) ||
                                            (v.nombre && normalizeText(v.nombre).includes(term))
                                        ) || [];

                                        const isVariantSpecific = !matchesParent && matchingVariants.length > 0;

                                        // Si la búsqueda coincide con variantes específicas, generar UNA fila por cada variante
                                        const rowsToRender = isVariantSpecific
                                            ? matchingVariants.map((v: any) => ({ variant: v, isSpecific: true }))
                                            : [{ variant: prod.variantes?.find((v: any) => v.es_default) || prod.variantes?.[0], isSpecific: false }];

                                        return rowsToRender.map(({ variant: displayVariant, isSpecific }: any) => {
                                            const displayCode = isSpecific ? displayVariant?.sku : prod.codigo_interno;
                                            const displayName = isSpecific ? `${prod.nombre} - ${displayVariant?.nombre}` : prod.nombre;
                                            const displayStock = isSpecific ? displayVariant?.stock_actual : prod.stock_disponible;
                                            const displayPrice = isSpecific ? displayVariant?.precio_contado : prod.precio_contado;
                                            const canAdd = displayStock > 0;

                                            return (
                                                <tr key={`${prod.id}-${displayVariant?.id || 'default'}`} className="bg-slate-900 hover:bg-slate-800 border-b border-slate-800/80 transition-colors cursor-pointer group">
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
                                                        {displayPrice ? Number(displayPrice).toFixed(2) : '0.00'}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <button
                                                            className="w-full flex items-center justify-center gap-2 bg-primary/10 text-primary border border-primary/30 hover:bg-primary hover:text-white hover:border-primary transition-all rounded-sm px-4 py-2 text-xs font-bold uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
                                                            disabled={!canAdd}
                                                            onClick={(e) => {
                                                                e.stopPropagation();

                                                                if (isSpecific) {
                                                                    addToCart(prod, displayVariant);
                                                                } else if (prod.variantes?.length === 1) {
                                                                    addToCart(prod, prod.variantes[0]);
                                                                } else {
                                                                    setSelectedVariantProduct(prod);
                                                                }
                                                            }}
                                                        >
                                                            <span className="material-symbols-outlined text-[16px]">{!isSpecific && prod.variantes?.length > 1 ? 'visibility' : 'add_shopping_cart'}</span>
                                                            <span>{!isSpecific && prod.variantes?.length > 1 ? 'Ver más' : 'Agregar'}</span>
                                                        </button>
                                                    </td>
                                                </tr>
                                            );
                                        });
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* No Results */}
                    {!isSearching && debouncedSearchTerm.length >= 3 && results.length === 0 && (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="text-center space-y-2">
                                <span className="material-symbols-outlined text-red-500/50 text-5xl">inventory_2</span>
                                <p className="text-slate-500 text-xs font-bold uppercase tracking-[0.2em]">No se encontraron productos para "{searchTerm}"</p>
                            </div>
                        </div>
                    )}
                </section>

                {/* Variant Selection Modal */}
                {selectedVariantProduct && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background-dark/80 backdrop-blur-sm p-4">
                        <div className="bg-slate-900 border border-slate-700 shadow-2xl rounded-sm w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
                            {/* Modal Header */}
                            <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex justify-between items-center">
                                <div>
                                    <h3 className="text-lg font-bold text-slate-100 uppercase tracking-wider">{selectedVariantProduct.nombre}</h3>
                                    <p className="text-xs text-slate-500 font-mono mt-1">CÓDIGO: {selectedVariantProduct.codigo_interno}</p>
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
                                    <p className="text-[10px] uppercase text-slate-400 font-bold tracking-[0.2em] mb-4">Seleccione la variante a vender:</p>
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
                                                            {variante.stock_actual} Disponibles
                                                        </span>
                                                    ) : (
                                                        <span className="text-[10px] text-red-500 font-bold uppercase tracking-widest">Agotado</span>
                                                    )}
                                                </div>
                                                <button
                                                    className="bg-primary hover:bg-primary-dark text-white px-4 py-2 rounded-sm text-xs font-bold uppercase tracking-widest transition-colors disabled:opacity-50 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed flex items-center gap-2"
                                                    disabled={variante.stock_actual <= 0}
                                                    onClick={() => {
                                                        addToCart(selectedVariantProduct, variante);
                                                        setSelectedVariantProduct(null);
                                                    }}
                                                >
                                                    <span className="material-symbols-outlined text-[16px]">add</span>
                                                    <span>Añadir</span>
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}



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
            </main>
        </div>
    );
};

export default Home;
