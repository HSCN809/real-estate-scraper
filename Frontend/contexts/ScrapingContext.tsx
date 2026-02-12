'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { getTaskStatus, stopTask, getActiveTasks, type TaskStatus } from '@/lib/api';

interface ScrapingTask {
    taskId: string;
    platform?: string;
    status: TaskStatus | null;
    isFinished: boolean;
    isStopping: boolean;
}

interface ScrapingContextType {
    activeTask: ScrapingTask | null;
    isPanelVisible: boolean;
    startTracking: (taskId: string, platform?: string) => void;
    stopTracking: () => void;
    requestStop: () => Promise<void>;
    togglePanel: () => void;
    showPanel: () => void;
    hidePanel: () => void;
}

const TASK_STORAGE_KEY = 'scraping_active_task';

const ScrapingContext = createContext<ScrapingContextType | undefined>(undefined);

export function ScrapingProvider({ children }: { children: ReactNode }) {
    const [activeTask, setActiveTask] = useState<ScrapingTask | null>(null);
    const [isPanelVisible, setIsPanelVisible] = useState(false);
    const taskIdRef = useRef<string | undefined>(undefined);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Yüklendiğinde sessionStorage'dan geri yükle
    useEffect(() => {
        const stored = sessionStorage.getItem(TASK_STORAGE_KEY);
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                if (parsed.taskId) {
                    taskIdRef.current = parsed.taskId;
                    setActiveTask({
                        taskId: parsed.taskId,
                        platform: parsed.platform,
                        status: null,
                        isFinished: false,
                        isStopping: false,
                    });
                    setIsPanelVisible(true);
                }
            } catch {
                sessionStorage.removeItem(TASK_STORAGE_KEY);
            }
        } else {
            // sessionStorage yok — backend'den aktif görevleri kontrol et (yeni sekme)
            getActiveTasks().then(response => {
                if (response.count > 0 && response.active_tasks.length > 0) {
                    const task = response.active_tasks[0];
                    if (task.task_id) {
                        taskIdRef.current = task.task_id;
                        setActiveTask({
                            taskId: task.task_id,
                            status: task,
                            isFinished: false,
                            isStopping: false,
                        });
                        setIsPanelVisible(true);
                    }
                }
            }).catch(() => {});
        }
    }, []);

    // sessionStorage'a kaydet
    useEffect(() => {
        if (activeTask && !activeTask.isFinished) {
            sessionStorage.setItem(TASK_STORAGE_KEY, JSON.stringify({
                taskId: activeTask.taskId,
                platform: activeTask.platform,
            }));
        } else {
            sessionStorage.removeItem(TASK_STORAGE_KEY);
        }
    }, [activeTask]);

    // Durum sorgulama mantığı
    const pollStatus = useCallback(async () => {
        const currentTaskId = taskIdRef.current;
        if (!currentTaskId) return;

        try {
            const data = await getTaskStatus(currentTaskId);

            if (taskIdRef.current !== currentTaskId) return;
            if (data.task_id && data.task_id !== currentTaskId) return;

            const isTaskFinished = data.status === 'completed'
                || data.status === 'failed'
                || data.status === 'stopped';

            // Görev devam ediyor — bitmiş olarak işaretleme
            if (data.status === 'pending' || data.status === 'running' || data.is_running) {
                setActiveTask(prev => {
                    if (!prev || prev.taskId !== currentTaskId) return prev;
                    return { ...prev, status: data };
                });
                return;
            }

            setActiveTask(prev => {
                if (!prev || prev.taskId !== currentTaskId) return prev;
                return {
                    ...prev,
                    status: data,
                    isFinished: isTaskFinished,
                };
            });
        } catch (error) {
            console.error('Durum kontrolü başarısız', error);
        }
    }, []);

    // Polling aralığını yönet
    useEffect(() => {
        if (!activeTask || activeTask.isFinished) {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
            return;
        }

        const interval = activeTask.isStopping ? 1000 : 2000;

        const initialTimer = setTimeout(pollStatus, 500);
        pollIntervalRef.current = setInterval(pollStatus, interval);

        return () => {
            clearTimeout(initialTimer);
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
        };
    }, [activeTask?.taskId, activeTask?.isFinished, activeTask?.isStopping, pollStatus]);

    const startTracking = useCallback((taskId: string, platform?: string) => {
        taskIdRef.current = taskId;
        setActiveTask({
            taskId,
            platform,
            status: null,
            isFinished: false,
            isStopping: false,
        });
        setIsPanelVisible(true);
    }, []);

    const stopTracking = useCallback(() => {
        taskIdRef.current = undefined;
        setActiveTask(null);
        setIsPanelVisible(false);
        sessionStorage.removeItem(TASK_STORAGE_KEY);
    }, []);

    const requestStop = useCallback(async () => {
        if (!activeTask) return;
        setActiveTask(prev => prev ? { ...prev, isStopping: true } : null);
        try {
            await stopTask(activeTask.taskId);
        } catch (error) {
            console.error('Durdurma isteği başarısız', error);
        }
    }, [activeTask]);

    const togglePanel = useCallback(() => setIsPanelVisible(v => !v), []);
    const showPanel = useCallback(() => setIsPanelVisible(true), []);
    const hidePanel = useCallback(() => setIsPanelVisible(false), []);

    return (
        <ScrapingContext.Provider value={{
            activeTask,
            isPanelVisible,
            startTracking,
            stopTracking,
            requestStop,
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
        throw new Error('useScraping ScrapingProvider içinde kullanılmalıdır');
    }
    return context;
}
