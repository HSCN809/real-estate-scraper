'use client';

import { useEffect, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle2, XCircle, StopCircle, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getTaskStatus, stopTask, type TaskStatus } from '@/lib/api';

interface ProgressModalProps {
    isOpen: boolean;
    onClose: () => void;
    taskId?: string;  // Optional task ID for tracking specific Celery tasks
}

export function ProgressModal({ isOpen, onClose, taskId }: ProgressModalProps) {
    const [mounted, setMounted] = useState(false);
    const [status, setStatus] = useState<TaskStatus | null>(null);
    const [isFinished, setIsFinished] = useState(false);
    const [isStopping, setIsStopping] = useState(false);
    const [currentTaskId, setCurrentTaskId] = useState<string | undefined>(taskId);

    useEffect(() => {
        setMounted(true);
        return () => setMounted(false);
    }, []);

    // Update currentTaskId when prop changes
    useEffect(() => {
        if (taskId) {
            setCurrentTaskId(taskId);
        }
    }, [taskId]);

    const pollStatus = useCallback(async () => {
        try {
            const data = await getTaskStatus(currentTaskId);
            setStatus(data);

            // Update currentTaskId if we got one from the server
            if (data.task_id && !currentTaskId) {
                setCurrentTaskId(data.task_id);
            }

            // Check if finished
            if (!data.is_running && data.progress === 100) {
                setIsFinished(true);
            }

            // Check if stopped early
            if (!data.is_running && data.stopped_early && isStopping) {
                setIsFinished(true);
                // Auto close after 2 seconds
                setTimeout(() => {
                    onClose();
                }, 2000);
            }

            // Check if task completed or failed
            if (data.status === 'completed' || data.status === 'failed' || data.status === 'stopped') {
                setIsFinished(true);
            }
        } catch (error) {
            console.error("Status check failed", error);
        }
    }, [currentTaskId, isStopping, onClose]);

    useEffect(() => {
        if (!isOpen) {
            setStatus(null);
            setIsFinished(false);
            setIsStopping(false);
            setCurrentTaskId(taskId);
            return;
        }

        // Smart polling: faster during stopping, normal otherwise
        const pollInterval = isStopping ? 1000 : 2000;
        const interval = setInterval(pollStatus, pollInterval);
        pollStatus(); // Initial call

        return () => clearInterval(interval);
    }, [isOpen, isStopping, pollStatus, taskId]);

    const handleStop = async () => {
        setIsStopping(true);
        try {
            const result = await stopTask(currentTaskId);
            console.log("Stop request sent:", result);
        } catch (error) {
            console.error("Stop request failed", error);
        }
    };

    if (!mounted) return null;

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop - allows clicking through for navigation */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
                        onClick={onClose}
                    />

                    {/* Floating Progress Panel - positioned at bottom right */}
                    <motion.div
                        initial={{ opacity: 0, x: 100, y: 0 }}
                        animate={{ opacity: 1, x: 0, y: 0 }}
                        exit={{ opacity: 0, x: 100, y: 0 }}
                        drag
                        dragMomentum={false}
                        className="fixed bottom-6 right-6 z-50 w-96"
                    >
                        <div className="bg-slate-900/95 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl">
                            {/* Header - Draggable */}
                            <div className="p-4 border-b border-slate-800 cursor-move select-none">
                                <div className="flex items-center gap-3">
                                    {isFinished ? (
                                        <div className={cn(
                                            "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0",
                                            status?.stopped_early ? "bg-yellow-500/20" : "bg-green-500/20"
                                        )}>
                                            {status?.stopped_early ? (
                                                <StopCircle className="w-5 h-5 text-yellow-500" />
                                            ) : (
                                                <CheckCircle2 className="w-5 h-5 text-green-500" />
                                            )}
                                        </div>
                                    ) : (
                                        <div className="w-10 h-10 bg-blue-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                                            <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                                        </div>
                                    )}

                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-sm font-semibold text-white truncate">
                                            {isFinished
                                                ? (status?.stopped_early ? 'Durduruldu' : 'Tamamlandi')
                                                : 'Tarama Devam Ediyor'}
                                        </h3>
                                        <p className="text-xs text-slate-400 truncate">
                                            {status?.message || 'Baslatiliyor...'}
                                        </p>
                                    </div>

                                    {/* Task ID badge */}
                                    {currentTaskId && (
                                        <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-2 py-1 rounded">
                                            {currentTaskId.slice(0, 8)}
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Content */}
                            <div className="p-4 space-y-3">
                                {/* Progress Bar */}
                                <div className="space-y-1.5">
                                    <div className="flex justify-between text-xs font-medium text-slate-400">
                                        <span>Ilerleme</span>
                                        <span>%{Math.round(status?.progress || 0)}</span>
                                    </div>
                                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                        <motion.div
                                            className={cn(
                                                "h-full rounded-full transition-colors",
                                                status?.stopped_early
                                                    ? "bg-yellow-500"
                                                    : isFinished
                                                        ? "bg-green-500"
                                                        : "bg-blue-500"
                                            )}
                                            initial={{ width: 0 }}
                                            animate={{ width: `${status?.progress || 0}%` }}
                                            transition={{ duration: 0.3 }}
                                        />
                                    </div>
                                </div>

                                {/* Stats */}
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

                                {/* Details */}
                                {status?.details && (
                                    <div className="p-2 bg-slate-800/50 rounded-lg text-xs text-slate-400 font-mono truncate">
                                        {status.details}
                                    </div>
                                )}

                                {/* Action Buttons */}
                                <div className="flex gap-2">
                                    {!isFinished ? (
                                        <motion.button
                                            onClick={handleStop}
                                            disabled={isStopping || status?.should_stop}
                                            className={cn(
                                                "flex-1 py-2 px-3 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2",
                                                isStopping || status?.should_stop
                                                    ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                                                    : "bg-red-600 hover:bg-red-700 text-white"
                                            )}
                                        >
                                            <StopCircle className="w-4 h-4" />
                                            {isStopping || status?.should_stop ? 'Durduruluyor...' : 'Durdur'}
                                        </motion.button>
                                    ) : (
                                        <motion.button
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            onClick={onClose}
                                            className={cn(
                                                "flex-1 py-2 px-3 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2",
                                                status?.stopped_early
                                                    ? "bg-yellow-600 hover:bg-yellow-700 text-white"
                                                    : "bg-green-600 hover:bg-green-700 text-white"
                                            )}
                                        >
                                            <CheckCircle2 className="w-4 h-4" />
                                            {status?.stopped_early ? 'Kaydedildi' : 'Tamam'}
                                        </motion.button>
                                    )}

                                    {/* Minimize/Close button when running */}
                                    {!isFinished && (
                                        <button
                                            onClick={onClose}
                                            className="px-3 py-2 text-sm font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                                            title="Arka planda devam et"
                                        >
                                            <ExternalLink className="w-4 h-4" />
                                        </button>
                                    )}
                                </div>

                                {/* Background task notice */}
                                {!isFinished && (
                                    <p className="text-[10px] text-center text-slate-500">
                                        Diger sayfalara gecebilirsiniz, tarama arka planda devam edecek
                                    </p>
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
