import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import api from "../api/axios";
import { AuthContext } from "./AuthContext";

interface CajaState {
    cajaAbierta: boolean;
    cajaId: number | null;
    showCajaModal: boolean;
    isLoading: boolean;
}

interface CajaContextType extends CajaState {
    abrirCaja: (montoInicial: number) => Promise<void>;
    cerrarCaja: (montoFinalReal: number) => Promise<void>;
    triggerCajaModal: () => void;
    dismissModal: () => void;
    checkCajaStatus: () => Promise<void>;
}

const CajaContext = createContext<CajaContextType>({
    cajaAbierta: false,
    cajaId: null,
    showCajaModal: false,
    isLoading: true,
    abrirCaja: async () => { },
    cerrarCaja: async () => { },
    triggerCajaModal: () => { },
    dismissModal: () => { },
    checkCajaStatus: async () => { },
});

export const useCaja = () => useContext(CajaContext);

export const CajaProvider = ({ children }: { children: ReactNode }) => {
    const { token } = useContext(AuthContext);
    const [state, setState] = useState<CajaState>({
        cajaAbierta: false,
        cajaId: null,
        showCajaModal: false,
        isLoading: true,
    });

    const checkCajaStatus = async () => {
        if (!token) {
            setState(prev => ({ ...prev, isLoading: false, showCajaModal: false }));
            return;
        }
        try {
            const res = await api.get('caja/estado/', {
                headers: { Authorization: `Token ${token}` }
            });
            if (res.data.caja_abierta) {
                setState({
                    cajaAbierta: true,
                    cajaId: res.data.data.id,
                    showCajaModal: false,
                    isLoading: false,
                });
            } else {
                setState({
                    cajaAbierta: false,
                    cajaId: null,
                    showCajaModal: true,
                    isLoading: false,
                });
            }
        } catch (err) {
            console.error("Error checking caja status:", err);
            setState(prev => ({ ...prev, isLoading: false }));
        }
    };

    const abrirCaja = async (montoInicial: number) => {
        try {
            const res = await api.post('caja/abrir/', { monto_inicial: montoInicial }, {
                headers: { Authorization: `Token ${token}` }
            });
            if (res.data.success) {
                setState({
                    cajaAbierta: true,
                    cajaId: res.data.data.id,
                    showCajaModal: false,
                    isLoading: false,
                });
            }
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || err.response?.data?.error || "Error al abrir la caja";
            alert(`❌ ${errorMsg}`);
            console.error("Error opening caja:", err);
        }
    };

    const dismissModal = () => {
        setState(prev => ({ ...prev, showCajaModal: false }));
    };

    const triggerCajaModal = () => {
        setState(prev => ({ ...prev, showCajaModal: true }));
    };

    const cerrarCaja = async (montoFinalReal: number) => {
        try {
            await api.post('caja/cerrar/', { monto_final_real: montoFinalReal }, {
                headers: { Authorization: `Token ${token}` }
            });
            setState({
                cajaAbierta: false,
                cajaId: null,
                showCajaModal: false,
                isLoading: false,
            });
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || err.response?.data?.error || "Error al cerrar la caja";
            alert(`\u274C ${errorMsg}`);
            console.error("Error closing caja:", err);
        }
    };

    useEffect(() => {
        checkCajaStatus();
    }, [token]);

    return (
        <CajaContext.Provider value={{
            ...state,
            abrirCaja,
            cerrarCaja,
            triggerCajaModal,
            dismissModal,
            checkCajaStatus,
        }}>
            {children}
        </CajaContext.Provider>
    );
};
