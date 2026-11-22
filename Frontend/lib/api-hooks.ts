// React Query hooks for API calls
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getStats,
    getResults,
    getResultsFilters,
    getResultsOverview,
    getPriceSummary,
    getCategories,
    getSubtypes,
    getListings,
    getTaskStatus,
    getActiveTasks,
    startScrape,
    getCities,
    getDistricts,
    exportToExcel,
    type TaskStatus
} from './api';
import type { Platform, ResultsFilters, ResultsPageParams, ScrapeRequest } from '@/types';

// ==================== Statistics & Data Hooks ====================

export function useStats() {
    return useQuery({
        queryKey: ['stats'],
        queryFn: getStats,
        staleTime: 0,
        refetchOnWindowFocus: false,
    });
}

export function useResults(params: ResultsPageParams = {}, enabled = true) {
    return useQuery({
        queryKey: ['results', 'page', params],
        queryFn: ({ signal }) => getResults(params, signal),
        enabled,
        staleTime: 0,
        refetchOnWindowFocus: false,
    });
}

export function useResultsFilters() {
    return useQuery({
        queryKey: ['results', 'filters'],
        queryFn: ({ signal }) => getResultsFilters(signal),
        staleTime: 0,
    });
}

export function useResultsOverview(filters: ResultsFilters = {}, enabled = true) {
    return useQuery({
        queryKey: ['results', 'overview', filters],
        queryFn: ({ signal }) => getResultsOverview(filters, signal),
        enabled,
        staleTime: 0,
    });
}

export function usePriceSummary(filters: ResultsFilters, enabled: boolean) {
    return useQuery({
        queryKey: ['results', 'prices', filters],
        queryFn: ({ signal }) => getPriceSummary(filters, signal),
        enabled,
        staleTime: 0,
    });
}

export function useCategories() {
    return useQuery({
        queryKey: ['categories'],
        queryFn: getCategories,
        staleTime: 60 * 60 * 1000, // 1 hour - categories rarely change
        refetchOnWindowFocus: false,
    });
}

export function useSubtypes(listingType: string, category: string, platform: string = 'hepsiemlak') {
    return useQuery({
        queryKey: ['subtypes', listingType, category, platform],
        queryFn: () => getSubtypes(listingType, category, platform),
        enabled: !!listingType && !!category,
        staleTime: 60 * 60 * 1000, // 1 hour
        refetchOnWindowFocus: false,
    });
}

// ==================== Scraping Task Hooks ====================

export function useTaskStatus(taskId: string | null) {
    return useQuery({
        queryKey: ['task-status', taskId],
        queryFn: () => getTaskStatus(taskId!),
        enabled: !!taskId,
        refetchInterval: (query) => {
            // Auto-poll while task is still active
            const taskData = query.state.data as TaskStatus | undefined;
            if (taskData?.status === 'queued' || taskData?.status === 'running') {
                return 2000;
            }
            return false;
        },
        staleTime: 1000, // 1 second cache
        refetchOnWindowFocus: false,
    });
}

export function useActiveTasks() {
    return useQuery({
        queryKey: ['active-tasks'],
        queryFn: getActiveTasks,
        refetchInterval: (query) => {
            const data = query.state.data as { active_tasks: TaskStatus[]; count: number } | undefined;
            if (data?.active_tasks && data.active_tasks.length > 0) {
                return 3000;
            }
            return 15000;
        },
        staleTime: 1000,
        refetchOnWindowFocus: true,
    });
}

export function useScrapeMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ platform, data }: { platform: Platform; data: ScrapeRequest }) => {
            const result = await startScrape(platform, data);
            return result;
        },
        onSuccess: () => {
            // Invalidate active tasks query when scraping starts
            queryClient.invalidateQueries({ queryKey: ['active-tasks'] });
        },
    });
}


// ==================== Listings & Location Hooks ====================

export function useListings(params: {
    platform?: string;
    kategori?: string;
    ilan_tipi?: string;
    city?: string;
    district?: string;
    page?: number;
    limit?: number;
}) {
    return useQuery({
        queryKey: ['listings', params],
        queryFn: () => getListings(params),
        enabled: Object.keys(params).length > 0,
        staleTime: 2 * 60 * 1000, // 2 minutes
        refetchOnWindowFocus: false,
    });
}

export function useCities() {
    return useQuery({
        queryKey: ['cities'],
        queryFn: getCities,
        staleTime: 24 * 60 * 60 * 1000, // 24 hours - cities rarely change
        refetchOnWindowFocus: false,
    });
}

export function useDistricts(city?: string) {
    return useQuery({
        queryKey: ['districts', city],
        queryFn: () => getDistricts(city || ''),
        enabled: !!city,
        staleTime: 24 * 60 * 60 * 1000, // 24 hours
        refetchOnWindowFocus: false,
    });
}

export function useExportToExcelMutation() {
    return useMutation({
        mutationFn: exportToExcel,
    });
}

// ==================== Utility Hooks ====================

export function useInvalidateActiveTasks() {
    const queryClient = useQueryClient();

    return () => {
        queryClient.invalidateQueries({ queryKey: ['active-tasks'] });
    };
}

export function useInvalidateResults() {
    const queryClient = useQueryClient();

    return () => {
        queryClient.invalidateQueries({ queryKey: ['results'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
    };
}
