'use client';

import { createContext, startTransition, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { cancelTask, getTaskStatus, getActiveTasks, TaskRequestError, type TaskStatus } from '@/lib/api';

const MAX_LOG_LINES = 8;
const MAX_POLL_FAILURES = 8;

interface ScrapingTask {
    taskId: string;
    platform?: string;
    status: TaskStatus | null;
    isFinished: boolean;
    logs: string[];
}

interface ScrapingContextType {
    activeTask: ScrapingTask | null;
    isPanelVisible: boolean;
    isCancelling: boolean;
    startTracking: (taskId: string, platform?: string) => void;
    stopTracking: () => void;
    cancelActiveTask: () => Promise<void>;
    togglePanel: () => void;
    showPanel: () => void;
    hidePanel: () => void;
}

const TASK_STORAGE_KEY = 'scraping_active_task';

const ScrapingContext = createContext<ScrapingContextType | undefined>(undefined);

function isTerminalStatus(status: TaskStatus['status'] | undefined): boolean {
    return status === 'completed' || status === 'failed' || status === 'cancelled';
}

function appendLog(logs: string[], message?: string | null): string[] {
    const next = (message || '').trim();
    if (!next || logs[logs.length - 1] === next) {
        return logs;
    }
    return [...logs, next].slice(-MAX_LOG_LINES);
}

export function ScrapingProvider({ children }: { children: ReactNode }) {
    const [activeTask, setActiveTask] = useState<ScrapingTask | null>(null);
    const [isPanelVisible, setIsPanelVisible] = useState(false);
    const [isCancelling, setIsCancelling] = useState(false);
    const taskIdRef = useRef<string | undefined>(undefined);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const pollFailuresRef = useRef(0);

    useEffect(() => {
        const stored = sessionStorage.getItem(TASK_STORAGE_KEY);
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                if (parsed.taskId) {
                    taskIdRef.current = parsed.taskId;
                    startTransition(() => {
                        setActiveTask({
                            taskId: parsed.taskId,
                            platform: parsed.platform,
                            status: null,
                            isFinished: false,
                            logs: [],
                        });
                        setIsPanelVisible(true);
                    });
                }
            } catch {
                sessionStorage.removeItem(TASK_STORAGE_KEY);
            }
        } else {
            getActiveTasks()
                .then(response => {
                    if (response.count > 0 && response.active_tasks.length > 0) {
                        const task = response.active_tasks[0];
                        if (task.task_id) {
                            taskIdRef.current = task.task_id;
                            startTransition(() => {
                                setActiveTask({
                                    taskId: task.task_id,
                                    platform: task.platform,
                                    status: task,
                                    isFinished: false,
                                    logs: appendLog([], task.message),
                                });
                                setIsPanelVisible(true);
                            });
                        }
                    }
                })
                .catch(() => {});
        }
    }, []);

    useEffect(() => {
        if (activeTask) {
            sessionStorage.setItem(TASK_STORAGE_KEY, JSON.stringify({
                taskId: activeTask.taskId,
                platform: activeTask.platform,
            }));
        } else {
            sessionStorage.removeItem(TASK_STORAGE_KEY);
        }
    }, [activeTask]);

    const applyTaskSnapshot = useCallback((currentTaskId: string, data: TaskStatus) => {
        const finished = isTerminalStatus(data.status);
        setActiveTask(prev => {
            if (!prev || prev.taskId !== currentTaskId) return prev;
            return {
                ...prev,
                status: data,
                isFinished: finished,
                logs: appendLog(prev.logs, data.message || data.details || data.error),
            };
        });
        return finished;
    }, []);

    const pollStatus = useCallback(async () => {
        const currentTaskId = taskIdRef.current;
        if (!currentTaskId) return;

        try {
            const data = await getTaskStatus(currentTaskId);

            if (taskIdRef.current !== currentTaskId) return;
            if (data.task_id && data.task_id !== currentTaskId) return;

            pollFailuresRef.current = 0;
            applyTaskSnapshot(currentTaskId, data);
        } catch (error) {
            const statusCode = error instanceof TaskRequestError ? error.status : 0;
            pollFailuresRef.current += 1;
            const lost = statusCode === 404 || pollFailuresRef.current >= MAX_POLL_FAILURES;
            if (!lost) {
                console.error('Durum kontrolü başarısız', error);
                return;
            }

            setActiveTask(prev => {
                if (!prev || prev.taskId !== currentTaskId) return prev;
                const message = statusCode === 404
                    ? 'Görev bulunamadı veya süresi doldu.'
                    : 'Tarama durumu alınamıyor.';
                const error = statusCode === 404
                    ? 'Görev kaydı silindi.'
                    : 'Sunucuya birkaç kez ulaşılamadı.';
                return {
                    ...prev,
                    isFinished: true,
                    status: {
                        task_id: currentTaskId,
                        status: 'failed',
                        message,
                        progress: prev.status?.progress || 0,
                        total: prev.status?.total || 0,
                        current: prev.status?.current || 0,
                        details: prev.status?.details || '',
                        error,
                        platform: prev.status?.platform,
                    },
                    logs: appendLog(prev.logs, message),
                };
            });
        }
    }, [applyTaskSnapshot]);

    const activeTaskId = activeTask?.taskId;
    const activeTaskFinished = activeTask?.isFinished ?? false;

    useEffect(() => {
        if (!activeTaskId || activeTaskFinished) {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
            return;
        }

        const initialTimer = setTimeout(pollStatus, 500);
        pollIntervalRef.current = setInterval(pollStatus, 2000);

        return () => {
            clearTimeout(initialTimer);
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
        };
    }, [activeTaskFinished, activeTaskId, pollStatus]);

    const startTracking = useCallback((taskId: string, platform?: string) => {
        taskIdRef.current = taskId;
        pollFailuresRef.current = 0;
        setIsCancelling(false);
        setActiveTask({
            taskId,
            platform,
            status: null,
            isFinished: false,
            logs: ['Sıraya alındı'],
        });
        setIsPanelVisible(true);
    }, []);

    const stopTracking = useCallback(() => {
        taskIdRef.current = undefined;
        pollFailuresRef.current = 0;
        setIsCancelling(false);
        setActiveTask(null);
        setIsPanelVisible(false);
        sessionStorage.removeItem(TASK_STORAGE_KEY);
    }, []);

    const cancelActiveTask = useCallback(async () => {
        const taskId = taskIdRef.current;
        if (!taskId) return;
        setIsCancelling(true);
        try {
            const data = await cancelTask(taskId);
            applyTaskSnapshot(taskId, data);
        } catch (error) {
            console.error('Görev iptal edilemedi', error);
        } finally {
            setIsCancelling(false);
        }
    }, [applyTaskSnapshot]);

    const togglePanel = useCallback(() => setIsPanelVisible(v => !v), []);
    const showPanel = useCallback(() => setIsPanelVisible(true), []);
    const hidePanel = useCallback(() => setIsPanelVisible(false), []);

    return (
        <ScrapingContext.Provider value={{
            activeTask,
            isPanelVisible,
            isCancelling,
            startTracking,
            stopTracking,
            cancelActiveTask,
            togglePanel,
            showPanel,
            hidePanel,
        }}>
            {children}
        </ScrapingContext.Provider>
    );
}

export function useScraping() {
    const context = useContext(ScrapingContext);
    if (context === undefined) {
        throw new Error('useScraping, ScrapingProvider içinde kullanılmalıdır');
    }
    return context;
}
