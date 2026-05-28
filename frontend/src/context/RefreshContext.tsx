import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

/**
 * RefreshContext — event bus ligero para sincronizar datos en la app.
 * 
 * Después de una venta exitosa (u otra mutación), se llama a `triggerRefresh()`
 * que incrementa un contador. Los componentes que dependen de datos frescos
 * observan `refreshKey` en sus useEffect para re-fetchar automáticamente.
 */

interface RefreshContextType {
    refreshKey: number;
    triggerRefresh: () => void;
}

const RefreshContext = createContext<RefreshContextType>({
    refreshKey: 0,
    triggerRefresh: () => { },
});

export const RefreshProvider = ({ children }: { children: ReactNode }) => {
    const [refreshKey, setRefreshKey] = useState(0);

    const triggerRefresh = useCallback(() => {
        setRefreshKey(prev => prev + 1);
    }, []);

    return (
        <RefreshContext.Provider value={{ refreshKey, triggerRefresh }}>
            {children}
        </RefreshContext.Provider>
    );
};

export const useRefresh = () => useContext(RefreshContext);
