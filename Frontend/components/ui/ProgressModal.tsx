'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle2, ExternalLink, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useScraping } from '@/contexts/ScrapingContext';

export function ProgressPanel() {
    const [mounted, setMounted] = useState(false);
    const {
        activeTask,
        isPanelVisible,
        stopTracking,
        hidePanel,
    } = useScraping();

    useEffect(() => {
        setMounted(true);
        return () => setMounted(false);
    }, []);

    if (!mounted || !activeTask || !isPanelVisible) return null;

    const { status, isFinished, taskId } = activeTask;

    return createPortal(
        <AnimatePresence>
            <motion.div
                key="progress-panel"
                initial={{ opacity: 0, x: 100, y: 0 }}
                animate={{ opacity: 1, x: 0, y: 0 }}
                exit={{ opacity: 0, x: 100, y: 0 }}
                drag
                dragMomentum={false}
                className="fixed bottom-6 right-6 z-50 w-96"
            >
                <div className="bg-slate-900/95 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl">
                    <div className="p-4 border-b border-slate-800 cursor-move select-none">
                        <div className="flex items-center gap-3">
                            {isFinished ? (
                                <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-green-500/20">
                                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                                </div>
                            ) : (
                                <div className="w-10 h-10 bg-blue-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                                </div>
                            )}

                            <div className="flex-1 min-w-0">
                                <h3 className="text-sm font-semibold text-white truncate">
                                    {isFinished ? 'Tamamlandi' : 'Tarama Devam Ediyor'}
                                </h3>
                                <p className="text-xs text-slate-400 truncate">
                                    {status?.message || 'Baslatiliyor...'}
                                </p>
                            </div>

                            {taskId && (
                                <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-2 py-1 rounded">
                                    {taskId.slice(0, 8)}
                                </span>
                            )}

                            {!isFinished && (
                                <button
                                    onClick={hidePanel}
                                    className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                                    title="Kucult"
                                >
                                    <Minus className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                    </div>

                    <div className="p-4 space-y-3">
                        <div className="space-y-1.5">
                            <div className="flex justify-between text-xs font-medium text-slate-400">
                                <span>Ilerleme</span>
                                <span>%{Math.round(status?.progress || 0)}</span>
                            </div>
                            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <motion.div
                                    className={cn(
                                        'h-full rounded-full transition-colors',
                                        isFinished ? 'bg-green-500' : 'bg-blue-500'
                                    )}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${status?.progress || 0}%` }}
                                    transition={{ duration: 0.3 }}
                                />
                            </div>
                        </div>

                        {status?.current !== undefined && status?.total !== undefined && status.total > 0 && (
                            <div className="flex items-center justify-between text-xs text-slate-500">
                                <span>{status.current} / {status.total}</span>
                                {status.started_at && (
                                    <span>
                                        Baslangic: {new Date(status.started_at).toLocaleTimeString('tr-TR')}
                                    </span>
                                )}
                            </div>
                        )}

                        {status?.details && (
                            <div className="p-2 bg-slate-800/50 rounded-lg text-xs text-slate-400 font-mono truncate">
                                {status.details}
                            </div>
                        )}

                        <div className="flex gap-2">
                            {isFinished ? (
                                <motion.button
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    onClick={stopTracking}
                                    className="flex-1 py-2 px-3 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white"
                                >
                                    <CheckCircle2 className="w-4 h-4" />
                                    Tamam
                                </motion.button>
                            ) : (
                                <button
                                    onClick={hidePanel}
                                    className="flex-1 px-3 py-2 text-sm font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors flex items-center justify-center gap-2"
                                    title="Arka planda devam et"
                                >
                                    <ExternalLink className="w-4 h-4" />
                                    Arka planda devam et
                                </button>
                            )}
                        </div>

                        {!isFinished && (
                            <p className="text-[10px] text-center text-slate-500">
                                Diger sayfalara gecebilirsiniz, tarama arka planda devam edecek
                            </p>
                        )}
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>,
        document.body
    );
}
