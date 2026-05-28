import { useState, useContext } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import { AuthContext } from "../context/AuthContext";
import { useCurrentTime } from "../hooks/useCurrentTime";

const Login = () => {
    const { login } = useContext(AuthContext);
    const { time, seconds, weekday, dateStr } = useCurrentTime();
    const navigate = useNavigate();

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [errorMsg, setErrorMsg] = useState("");

    const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setErrorMsg("");

        try {
            const response = await api.post("login/", {
                username,
                password,
            });

            const { token, user } = response.data.data;
            login(token, user);
            navigate("/home", { replace: true });
        } catch (error: any) {

            if (error.response?.data?.detail) {
                setErrorMsg(error.response.data.detail);
            } else {
                setErrorMsg("Error de conexión con el servidor");
            }
        }
    };

    return (
        <div className="bg-slate-industrial dark:bg-background-dark overflow-hidden h-screen w-screen font-display">
            <div className="flex h-full w-full">

                {/* Left Panel: Auth Sidebar (30%) */}
                <aside className="w-[400px] min-w-[400px] h-full bg-navy-industrial text-slate-100 flex flex-col justify-between p-10 border-r-4 border-primary shadow-2xl z-20">

                    {/* Top Section: Logo & Branding */}
                    <div className="flex flex-col gap-8">
                        <div className="flex items-center gap-3">
                            <div className="bg-primary p-2 rounded">
                                <span className="material-symbols-outlined text-white text-3xl">terminal</span>
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold tracking-tight leading-none">LMSolutions</h1>
                                <p className="text-xs uppercase tracking-[0.2em] text-slate-400 font-medium mt-1">Terminal de Punto de Venta</p>
                            </div>
                        </div>

                        {/* Login Form */}
                        <form onSubmit={handleSubmit} className="space-y-6 mt-10">
                            <div className="space-y-2">
                                <label className="block text-sm font-bold uppercase tracking-wider text-slate-300">Usuario</label>
                                <div className="relative group">
                                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors">person</span>
                                    <input
                                        className="w-full bg-transparent border-2 border-slate-700 rounded-none h-16 pl-12 pr-4 text-white placeholder:text-slate-600 focus:border-primary focus:ring-0 text-lg tracking-widest uppercase transition-all"
                                        placeholder="INGRESAR USUARIO"
                                        type="text"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="block text-sm font-bold uppercase tracking-wider text-slate-300">Contraseña</label>
                                <div className="relative group">
                                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors">lock</span>
                                    <input
                                        className="w-full bg-transparent border-2 border-slate-700 rounded-none h-16 pl-12 pr-4 text-white placeholder:text-slate-600 focus:border-primary focus:ring-0 text-lg tracking-widest transition-all"
                                        placeholder="••••••••"
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>


                            <button type="submit" className="w-full bg-primary hover:bg-orange-600 text-white py-6 px-4 rounded-none flex items-center justify-center gap-3 group transition-all transform active:scale-[0.98] mt-12">
                                <span className="text-xl font-bold tracking-[0.1em]">INICIAR TURNO</span>
                                <span className="material-symbols-outlined font-bold transition-transform group-hover:translate-x-1">login</span>
                            </button>

                            {/* Error Message Box */}
                            {errorMsg && (
                                <div className="mt-4 p-4 border border-red-500/50 bg-red-950/30 flex items-center gap-3 animate-pulse">
                                    <span className="material-symbols-outlined text-red-500">warning</span>
                                    <p className="text-sm font-bold text-red-400 uppercase tracking-widest">{errorMsg}</p>
                                </div>
                            )}
                        </form>
                    </div>

                    {/* Bottom Section: Diagnostics */}
                    <div className="flex flex-col gap-8">
                        <div className="flex flex-col gap-1 opacity-60">
                            <div className="h-[1px] w-full bg-slate-700 mb-2"></div>
                            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-tighter">
                                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                                <p>DB: local | Status: <span className="text-red-400">Offline</span> | Ver. 0.0.1</p>
                            </div>
                            <p className="font-mono text-[10px] uppercase tracking-tighter">Machine ID: LM-TEST-ANGELITO-W01</p>
                        </div>
                    </div>
                </aside>

                {/* Right Panel: Information Hub (70%) */}
                <main className="flex-1 h-full relative watermark-overlay flex items-center justify-center p-20">
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.03]">
                        <span className="material-symbols-outlined text-[40rem]">warehouse</span>
                    </div>

                    <div className="relative z-10 text-center space-y-4">
                        <div className="inline-block px-6 py-2 bg-slate-200/50 rounded-full mb-6">
                            <p className="text-slate-500 font-bold uppercase tracking-[0.3em] text-sm">Control completo de tu negocio </p>
                        </div>

                        {/* Digital Clock Placeholder */}
                        <div className="flex flex-col items-center">
                            <h2 className="text-[10rem] font-light text-slate-900 leading-none tracking-tighter flex items-baseline">
                                {time}<span className="text-4xl ml-4 font-bold text-slate-400 self-center">{seconds}</span>
                            </h2>
                            <div className="flex items-center gap-4 text-3xl font-medium text-slate-500 uppercase tracking-widest mt-4">
                                <span>{weekday}</span>
                                <span className="w-2 h-2 rounded-full bg-slate-300"></span>
                                <span>{dateStr}</span>
                            </div>
                        </div>

                    </div>

                    {/* Subtle Bottom Branding for Right Panel */}

                </main>
            </div>

            {/* Background Pattern */}
            <div className="fixed inset-0 pointer-events-none opacity-[0.02] z-0">
                <svg height="100%" width="100%">
                    <pattern height="40" id="grid" patternUnits="userSpaceOnUse" width="40">
                        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1"></path>
                    </pattern>
                    <rect fill="url(#grid)" height="100%" width="100%"></rect>
                </svg>
            </div>
        </div>
    );
};

export default Login;