'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertCircle, X } from 'lucide-react';

type ToastType = 'success' | 'error';

interface Toast {
    id: number;
    type: ToastType;
    message: string;
}

interface ToastContextType {
    success: (message: string) => void;
    error: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

let toastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const addToast = useCallback((type: ToastType, message: string) => {
        const id = ++toastId;
        setToasts((prev) => [...prev, { id, type, message }]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 4000);
    }, []);

    const removeToast = useCallback((id: number) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    const success = useCallback((message: string) => addToast('success', message), [addToast]);
    const error = useCallback((message: string) => addToast('error', message), [addToast]);

    return (
        <ToastContext.Provider value={{ success, error }}>
            {children}
            {/* Toast Container */}
            <div className="fixed top-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
                <AnimatePresence>
                    {toasts.map((toast) => (
                        <motion.div
                            key={toast.id}
                            initial={{ opacity: 0, x: 80, scale: 0.95 }}
                            animate={{ opacity: 1, x: 0, scale: 1 }}
                            exit={{ opacity: 0, x: 80, scale: 0.95 }}
                            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                            className="pointer-events-auto"
                        >
                            <div
                                className={`
                                    flex items-center gap-3 px-5 py-4 rounded-xl
                                    backdrop-blur-xl shadow-2xl min-w-[320px] max-w-[420px]
                                    border
                                    ${toast.type === 'success'
                                        ? 'bg-emerald-500/15 border-emerald-500/30 shadow-emerald-500/10'
                                        : 'bg-red-500/15 border-red-500/30 shadow-red-500/10'
                                    }
                                `}
                            >
                                {/* Icon */}
                                <div className={`
                                    flex-shrink-0 p-1.5 rounded-lg
                                    ${toast.type === 'success'
                                        ? 'bg-emerald-500/20'
                                        : 'bg-red-500/20'
                                    }
                                `}>
                                    {toast.type === 'success'
                                        ? <CheckCircle className="w-5 h-5 text-emerald-400" />
                                        : <AlertCircle className="w-5 h-5 text-red-400" />
                                    }
                                </div>

                                {/* Message */}
                                <p className={`
                                    text-sm font-medium flex-1
                                    ${toast.type === 'success' ? 'text-emerald-200' : 'text-red-200'}
                                `}>
                                    {toast.message}
                                </p>

                                {/* Close */}
                                <button
                                    onClick={() => removeToast(toast.id)}
                                    className="flex-shrink-0 text-gray-400 hover:text-white transition-colors p-1 rounded-md hover:bg-white/10"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>

                            {/* Progress bar */}
                            <motion.div
                                initial={{ scaleX: 1 }}
                                animate={{ scaleX: 0 }}
                                transition={{ duration: 4, ease: 'linear' }}
                                className={`
                                    h-0.5 mt-0 mx-3 rounded-b-full origin-left
                                    ${toast.type === 'success' ? 'bg-emerald-400/50' : 'bg-red-400/50'}
                                `}
                            />
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>
        </ToastContext.Provider>
    );
}

export function useToast(): ToastContextType {
    const context = useContext(ToastContext);
    if (context === undefined) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
}