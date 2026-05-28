import { createContext, useState } from "react";
import type { ReactNode } from "react";

interface User {
    id: number;
    username: string;
    rol: string | null;
}

interface AuthContextType {
    token: string | null;
    user: User | null;
    login: (newToken: string, userData: User) => void;
    logout: () => void;
}

export const AuthContext = createContext<AuthContextType>({
    token: null,
    user: null,
    login: () => { },
    logout: () => { }
});

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [token, setToken] = useState<string | null>(
        localStorage.getItem("token") || null
    );
    const [user, setUser] = useState<User | null>(
        localStorage.getItem("user") ? JSON.parse(localStorage.getItem("user") as string) : null
    );

    const login = (newToken: string, userData: User) => {
        localStorage.setItem("token", newToken);
        localStorage.setItem("user", JSON.stringify(userData));
        setToken(newToken);
        setUser(userData);
    };

    const logout = () => {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ token, user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};