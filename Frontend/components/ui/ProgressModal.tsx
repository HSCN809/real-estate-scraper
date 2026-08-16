'use client';

import { useEffect, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence, useDragControls } from 'framer-motion';
import { Loader2, CheckCircle2, Minus, XCircle, Ban, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useScraping } from '@/contexts/ScrapingContext';
import { formatIstanbulTime, parseAppDate } from '@/lib/datetime';
import type { TaskLifecycleStatus } from '@/lib/api';

const subscribe = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

function isTimeoutMessage(text?: string | null): boolean {
    const value = (text || '').toLocaleLowerCase('tr-TR');
    return value.includes('zaman limiti') || value.includes('zaman aşımı') || value.includes('timeout');
}

function panelCopy(status?: TaskLifecycleStatus | null, message?: string | null) {
    if (!status || status === 'queued') {
        return {
            title: 'Sırada bekliyor',
            tone: 'queued' as const,
        };
    }
    if (status === 'cancelled') {
        return {
            title: 'İptal edildi',
            tone: 'cancelled' as const,
        };
    }
    if (status === 'failed') {
        return {
            title: isTimeoutMessage(message) ? 'Zaman aşımı' : 'Başarısız',
            tone: 'failed' as const,
        };
    }
    if (status === 'completed') {
        return {
            title: 'Tamamlandı',
            tone: 'completed' as const,
        };
    }
    return {
        title: 'Tarama devam ediyor',
        tone: 'running' as const,
    };
}

export function ProgressPanel() {
    const mounted = useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);
    const {
        activeTask,
        isPanelVisible,
        isCancelling,
        stopTracking,
        hidePanel,
        cancelActiveTask,
    } = useScraping();
    const dragControls = useDragControls();

    const status = activeTask?.status;
    const taskStatus = status?.status;
    const isFinished = Boolean(activeTask?.isFinished);
    const copy = panelCopy(taskStatus, status?.message || status?.error);
    const visible = Boolean(mounted && activeTask && isPanelVisible);

    useEffect(() => {
        if (!visible) return undefined;
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                hidePanel();
            }
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [hidePanel, visible]);

    if (!mounted) return null;

    const progressValue = Math.max(0, Math.min(100, Math.round(status?.progress || 0)));
    const counterLabel = (status?.unit?.trim() || 'Sayfa').replace(/^./, (char) => char.toLocaleUpperCase('tr-TR'));
    const subtitle = status?.error || status?.message || (taskStatus === 'queued' ? 'İşçi bekleniyor...' : 'Başlatılıyor...');

    return createPortal(
        <AnimatePresence>
            {activeTask && isPanelVisible && (
                <motion.div
                    key="progress-panel"
                    role="dialog"
                    aria-modal="false"
                    aria-labelledby="progress-panel-title"
                    aria-describedby="progress-panel-message"
                    initial={{ opacity: 0, x: 100, y: 0 }}
                    animate={{ opacity: 1, x: 0, y: 0 }}
                    exit={{ opacity: 0, x: 100, y: 0 }}
                    drag
                    dragControls={dragControls}
                    dragListener={false}
                    dragMomentum={false}
                    className="fixed bottom-6 right-6 z-50 w-96"
                >
                    <div className="bg-slate-900/95 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl">
                        <div
                            className="p-4 border-b border-slate-800 cursor-move select-none"
                            onPointerDown={(event) => dragControls.start(event)}
                        >
                            <div className="flex items-center gap-3">
                                {copy.tone === 'completed' ? (
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-green-500/20">
                                        <CheckCircle2 className="w-5 h-5 text-green-500" aria-hidden="true" />
                                    </div>
                                ) : copy.tone === 'failed' ? (
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-red-500/20">
                                        <XCircle className="w-5 h-5 text-red-400" aria-hidden="true" />
                                    </div>
                                ) : copy.tone === 'cancelled' ? (
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-amber-500/20">
                                        <Ban className="w-5 h-5 text-amber-400" aria-hidden="true" />
                                    </div>
                                ) : copy.tone === 'queued' ? (
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-slate-500/20">
                                        <Clock className="w-5 h-5 text-slate-300" aria-hidden="true" />
                                    </div>
                                ) : (
                                    <div className="w-10 h-10 bg-blue-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                                        <Loader2 className="w-5 h-5 text-blue-500 animate-spin" aria-hidden="true" />
                                    </div>
                                )}

                                <div className="flex-1 min-w-0">
                                    <h3 id="progress-panel-title" className="text-sm font-semibold text-white truncate">
                                        {copy.title}
                                    </h3>
                                    <p id="progress-panel-message" className="text-xs text-slate-400 line-clamp-2">
                                        {subtitle}
                                    </p>
                                </div>

                                {activeTask.taskId && (
                                    <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-2 py-1 rounded">
                                        {activeTask.taskId.slice(0, 8)}
                                    </span>
                                )}

                                <button
                                    type="button"
                                    onClick={hidePanel}
                                    className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                                    aria-label="Paneli küçült"
                                    title="Küçült"
                                >
                                    <Minus className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        <div className="p-4 space-y-3">
                            <div className="space-y-1.5">
                                <div className="flex justify-between text-xs font-medium text-slate-400">
                                    <span>İlerleme</span>
                                    <span>%{progressValue}</span>
                                </div>
                                <div
                                    role="progressbar"
                                    aria-valuemin={0}
                                    aria-valuemax={100}
                                    aria-valuenow={progressValue}
                                    aria-label="Tarama ilerlemesi"
                                    className="h-1.5 bg-slate-800 rounded-full overflow-hidden"
                                >
                                    <motion.div
                                        className={cn(
                                            'h-full rounded-full transition-colors',
                                            copy.tone === 'completed' && 'bg-green-500',
                                            copy.tone === 'failed' && 'bg-red-500',
                                            copy.tone === 'cancelled' && 'bg-amber-500',
                                            (copy.tone === 'running' || copy.tone === 'queued') && 'bg-blue-500',
                                        )}
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progressValue}%` }}
                                        transition={{ duration: 0.3 }}
                                    />
                                </div>
                            </div>

                            {status?.current !== undefined && status?.total !== undefined && status.total > 0 && (
                                <div className="flex items-center justify-between text-xs text-slate-500">
                                    <span>{counterLabel}: {status.current} / {status.total}</span>
                                    {status.started_at && (
                                        <span>
                                            Başlangıç: {(() => {
                                                const startedAt = parseAppDate(status.started_at);
                                                return startedAt ? formatIstanbulTime(startedAt) : '-';
                                            })()}
                                        </span>
                                    )}
                                </div>
                            )}

                            {status?.details && (
                                <div className="p-2 bg-slate-800/50 rounded-lg text-xs text-slate-400 font-mono whitespace-pre-wrap break-words max-h-20 overflow-y-auto">
                                    {status.details}
                                </div>
                            )}

                            {activeTask.logs.length > 0 && (
                                <div
                                    role="log"
                                    aria-live="polite"
                                    aria-relevant="additions"
                                    className="max-h-28 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/60 p-2 space-y-1"
                                >
                                    {activeTask.logs.map((entry, index) => (
                                        <p
                                            key={`${index}-${entry.text}`}
                                            className={cn(
                                                'text-[11px] break-words',
                                                entry.level === 'error' && 'text-red-300',
                                                entry.level === 'warning' && 'text-amber-300',
                                                entry.level === 'info' && 'text-slate-400',
                                            )}
                                        >
                                            {entry.text}
                                        </p>
                                    ))}
                                </div>
                            )}

                            <div className="flex gap-2">
                                {isFinished ? (
                                    <motion.button
                                        type="button"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        onClick={stopTracking}
                                        className={cn(
                                            'flex-1 py-2 px-3 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2 text-white',
                                            copy.tone === 'completed' && 'bg-green-600 hover:bg-green-700',
                                            copy.tone === 'failed' && 'bg-red-600 hover:bg-red-700',
                                            copy.tone === 'cancelled' && 'bg-amber-600 hover:bg-amber-700',
                                        )}
                                    >
                                        {copy.tone === 'completed' ? (
                                            <CheckCircle2 className="w-4 h-4" />
                                        ) : copy.tone === 'cancelled' ? (
                                            <Ban className="w-4 h-4" />
                                        ) : (
                                            <XCircle className="w-4 h-4" />
                                        )}
                                        Kapat
                                    </motion.button>
                                ) : (
                                    <>
                                        <button
                                            type="button"
                                            onClick={hidePanel}
                                            className="flex-1 px-3 py-2 text-sm font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                                        >
                                            Arka planda devam et
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => { void cancelActiveTask(); }}
                                            disabled={isCancelling}
                                            className="px-3 py-2 text-sm font-medium rounded-lg bg-red-600/90 hover:bg-red-600 disabled:opacity-60 text-white transition-colors"
                                            aria-label="Taramayı durdur"
                                        >
                                            {isCancelling ? 'Durduruluyor...' : 'Durdur'}
                                        </button>
                                    </>
                                )}
                            </div>

                            {!isFinished && (
                                <p className="text-[10px] text-center text-slate-500">
                                    Diğer sayfalara geçebilirsiniz, tarama arka planda devam edecek
                                </p>
                            )}
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>,
        document.body
    );
}
