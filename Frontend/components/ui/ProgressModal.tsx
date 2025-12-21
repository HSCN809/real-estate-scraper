'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle2, XCircle, StopCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProgressModalProps {
    isOpen: boolean;
    onClose: () => void;
}

interface TaskStatus {
    is_running: boolean;
    message: string;
    progress: number;
    total: number;
    current: number;
    details: string;
    should_stop?: boolean;
    stopped_early?: boolean;
}

export function ProgressModal({ isOpen, onClose }: ProgressModalProps) {
    const [mounted, setMounted] = useState(false);
    const [status, setStatus] = useState<TaskStatus | null>(null);
    const [isFinished, setIsFinished] = useState(false);
    const [isStopping, setIsStopping] = useState(false);

    useEffect(() => {
        setMounted(true);
        return () => setMounted(false);
    }, []);

    useEffect(() => {
        if (!isOpen) {
            setStatus(null);
            setIsFinished(false);
            setIsStopping(false);
            return;
        }

        const pollStatus = async () => {
            try {
                const res = await fetch('http://localhost:8000/api/v1/status');
                if (res.ok) {
                    const data = await res.json();
                    setStatus(data);

                    if (!data.is_running && data.progress === 100) {
                        setIsFinished(true);
                    }

                    // Eğer erken durdurulduysa da finished say
                    if (!data.is_running && data.stopped_early) {
                        setIsFinished(true);
                    }
                }
            } catch (error) {
                console.error("Status check failed", error);
            }
        };

        // Poll every 1 second
        const interval = setInterval(pollStatus, 1000);
        pollStatus(); // Initial call

        return () => clearInterval(interval);
    }, [isOpen]);

    const handleStop = async () => {
        setIsStopping(true);
        try {
            const res = await fetch('http://localhost:8000/api/v1/stop', {
                method: 'POST'
            });
            if (res.ok) {
                console.log("Stop request sent");
            }
        } catch (error) {
            console.error("Stop request failed", error);
        }
    };

    if (!mounted) return null;

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50"
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    >
                        <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden">
                            {/* Header */}
                            <div className="p-6 text-center border-b border-slate-800">
                                {isFinished ? (
                                    <div className={cn(
                                        "mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-4",
                                        status?.stopped_early ? "bg-yellow-500/20" : "bg-green-500/20"
                                    )}>
                                        {status?.stopped_early ? (
                                            <StopCircle className="w-10 h-10 text-yellow-500" />
                                        ) : (
                                            <CheckCircle2 className="w-10 h-10 text-green-500" />
                                        )}
                                    </div>
                                ) : (
                                    <div className="mx-auto w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mb-4">
                                        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                                    </div>
                                )}

                                <h2 className="text-xl font-bold text-white mb-2">
                                    {isFinished
                                        ? (status?.stopped_early ? 'İşlem Durduruldu' : 'İşlem Tamamlandı')
                                        : 'İşlem Devam Ediyor'}
                                </h2>
                                <p className="text-slate-400 text-sm">
                                    {status?.message || 'Başlatılıyor...'}
                                </p>
                            </div>

                            {/* Content */}
                            <div className="p-6 space-y-4">
                                {/* Progress Bar */}
                                <div className="space-y-2">
                                    <div className="flex justify-between text-xs font-medium text-slate-400">
                                        <span>İlerleme</span>
                                        <span>%{Math.round(status?.progress || 0)}</span>
                                    </div>
                                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                        <motion.div
                                            className={cn(
                                                "h-full rounded-full",
                                                status?.stopped_early ? "bg-yellow-500" : "bg-blue-500"
                                            )}
                                            initial={{ width: 0 }}
                                            animate={{ width: `${status?.progress || 0}%` }}
                                            transition={{ duration: 0.5 }}
                                        />
                                    </div>
                                </div>

                                {/* Details if any */}
                                {status?.details && (
                                    <div className="p-3 bg-slate-800/50 rounded-lg text-xs text-slate-400 font-mono">
                                        {status.details}
                                    </div>
                                )}

                                {/* Durdur Butonu - sadece çalışırken göster */}
                                {!isFinished && (
                                    <motion.button
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        onClick={handleStop}
                                        disabled={isStopping || status?.should_stop}
                                        className={cn(
                                            "w-full py-3 px-4 font-medium rounded-xl transition-colors flex items-center justify-center gap-2",
                                            isStopping || status?.should_stop
                                                ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                                                : "bg-red-600 hover:bg-red-700 text-white"
                                        )}
                                    >
                                        <StopCircle className="w-5 h-5" />
                                        {isStopping || status?.should_stop ? 'Durduruluyor...' : 'İşlemi Durdur'}
                                    </motion.button>
                                )}

                                {/* Close Button (only when finished) */}
                                {isFinished && (
                                    <motion.button
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        onClick={onClose}
                                        className={cn(
                                            "w-full py-3 px-4 font-medium rounded-xl transition-colors flex items-center justify-center gap-2",
                                            status?.stopped_early
                                                ? "bg-yellow-600 hover:bg-yellow-700 text-white"
                                                : "bg-green-600 hover:bg-green-700 text-white"
                                        )}
                                    >
                                        <CheckCircle2 className="w-5 h-5" />
                                        {status?.stopped_early ? 'Kaydedildi - Kapat' : 'Tamam'}
                                    </motion.button>
                                )}
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>,
        document.body
    );
}

