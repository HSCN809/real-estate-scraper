// Emlak Scraper Backend API istemcisi

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

import type { ScrapeRequest, ScrapeStartResponse, Platform, PriceSummary, ResultsFacets, ResultsFilters, ResultsOverview, ResultsPageParams, ResultsPageResponse } from '@/types';

export async function startScrape(platform: Platform, data: ScrapeRequest): Promise<ScrapeStartResponse> {
    const response = await fetch(`${API_BASE_URL}/scrape/${platform}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API error: ${response.status}`);
    }

    return response.json();
}

// Health check URL - API base'den türetilir
const API_HEALTH_URL = process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '/')
    : 'http://localhost:8000/';

export async function healthCheck(): Promise<boolean> {
    try {
        const response = await fetch(API_HEALTH_URL);
        return response.ok;
    } catch {
        return false;
    }
}


export async function getStats() {
    const response = await fetch(`${API_BASE_URL}/stats`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('İstatistikler alınamadı');
    }
    return response.json();
}

async function getResultsData<T>(path: string, params: ResultsPageParams, signal?: AbortSignal): Promise<T> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
        if (Array.isArray(value)) {
            for (const item of value) query.append(key, item);
        } else if (value !== undefined && value !== 'all') {
            query.set(key, String(value));
        }
    }
    const url = `${API_BASE_URL}${path}`;
    const response = await fetch(query.size ? `${url}?${query}` : url, {
        credentials: 'include',
        signal,
    });
    if (!response.ok) {
        throw new Error('Sonuçlar alınamadı');
    }
    return response.json();
}

export function getResults(params: ResultsPageParams = {}, signal?: AbortSignal) {
    return getResultsData<ResultsPageResponse>('/results', params, signal);
}

export function getResultsFilters(signal?: AbortSignal) {
    return getResultsData<ResultsFacets>('/results/filters', {}, signal);
}

export function getResultsOverview(filters: ResultsFilters = {}, signal?: AbortSignal) {
    return getResultsData<ResultsOverview>('/results/overview', filters, signal);
}

export function getPriceSummary(filters: ResultsFilters, signal?: AbortSignal) {
    return getResultsData<PriceSummary>('/analytics/prices', filters, signal);
}

export interface Category {
    id: string;
    name: string;
}

export interface CategoriesResponse {
    emlakjet: {
        satilik: Category[];
        kiralik: Category[];
    };
    hepsiemlak: {
        satilik: Category[];
        kiralik: Category[];
    };
}

export async function getCategories(): Promise<CategoriesResponse> {
    const response = await fetch(`${API_BASE_URL}/config/categories`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('Kategoriler alınamadı');
    }
    return response.json();
}

// Subtype (alt kategori) için API
export interface Subtype {
    id: string;
    name: string;
    path: string;
}

export interface SubtypesResponse {
    subtypes: Subtype[];
    cached: boolean;
    error?: string;
}

export async function getSubtypes(listingType: string, category: string, platform: string = 'hepsiemlak'): Promise<SubtypesResponse> {
    const response = await fetch(`${API_BASE_URL}/config/subtypes?listing_type=${listingType}&category=${category}&platform=${platform}`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('Alt kategoriler alınamadı');
    }
    return response.json();
}

// Veritabanı tabanlı ilan endpoint'i
export interface ListingsResponse {
    total: number;
    page: number;
    limit: number;
    pages: number;
    items: Array<Record<string, unknown>>;
}

export async function getListings(params: {
    platform?: string;
    kategori?: string;
    ilan_tipi?: string;
    city?: string;
    district?: string;
    page?: number;
    limit?: number;
}): Promise<ListingsResponse> {
    const searchParams = new URLSearchParams();
    if (params.platform) searchParams.set('platform', params.platform);
    if (params.kategori) searchParams.set('kategori', params.kategori);
    if (params.ilan_tipi) searchParams.set('ilan_tipi', params.ilan_tipi);
    if (params.city) searchParams.set('city', params.city);
    if (params.district) searchParams.set('district', params.district);
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.limit) searchParams.set('limit', params.limit.toString());

    const response = await fetch(`${API_BASE_URL}/listings?${searchParams}`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('İlanlar alınamadı');
    }
    return response.json();
}

// Excel dışa aktarma fonksiyonu
export async function exportToExcel(params: {
    platform?: string;
    kategori?: string;
    ilan_tipi?: string;
    city?: string;
    district?: string;
}): Promise<Blob> {
    const searchParams = new URLSearchParams();
    if (params.platform && params.platform !== 'all') searchParams.set('platform', params.platform);
    if (params.kategori && params.kategori !== 'all') searchParams.set('kategori', params.kategori);
    if (params.ilan_tipi && params.ilan_tipi !== 'all') searchParams.set('ilan_tipi', params.ilan_tipi);
    if (params.city) searchParams.set('city', params.city);
    if (params.district) searchParams.set('district', params.district);

    const response = await fetch(`${API_BASE_URL}/export/excel?${searchParams}`, {
        method: 'POST',
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Excel export başarısız');
    }

    return response.blob();
}

// Veritabanından şehirler ve ilçeler
export async function getCities(): Promise<{ cities: string[] }> {
    const response = await fetch(`${API_BASE_URL}/cities`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('Şehirler alınamadı');
    }
    return response.json();
}

export async function getDistricts(city: string): Promise<{ city: string; districts: string[] }> {
    const response = await fetch(`${API_BASE_URL}/cities/${city}/districts`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('İlçeler alınamadı');
    }
    return response.json();
}

// ==================== İlçe GeoJSON API ====================

export interface DistrictIndexEntry {
    file: string;
    count: number;
    districts: string[];
}

export interface DistrictIndex {
    [province: string]: DistrictIndexEntry;
}

export async function getDistrictsIndex(): Promise<DistrictIndex> {
    const response = await fetch(`${API_BASE_URL}/districts/index`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('İlçe index alınamadı');
    }
    return response.json();
}

export async function getDistrictGeoJSON(provinceName: string): Promise<GeoJSON.FeatureCollection> {
    const response = await fetch(`${API_BASE_URL}/districts/${encodeURIComponent(provinceName)}`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error(`${provinceName} ilçe verisi alınamadı`);
    }
    return response.json();
}

// ==================== Görev Durumu API (Celery Entegrasyonu) ====================

export type TaskLifecycleStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface TaskStatus {
    task_id: string;
    status: TaskLifecycleStatus;
    message: string;
    progress: number;
    total: number;
    current: number;
    details: string;
    unit?: string;
    logs?: Array<{ text: string; level?: string }>;
    error?: string | null;
    platform?: 'emlakjet' | 'hepsiemlak';
    started_at?: string;
    updated_at?: string;
    finished_at?: string | null;
}

export class TaskRequestError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.name = 'TaskRequestError';
        this.status = status;
    }
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new TaskRequestError('Task durumu alınamadı', response.status);
    }
    return response.json();
}


export async function getActiveTasks(): Promise<{ active_tasks: TaskStatus[]; count: number }> {
    const response = await fetch(`${API_BASE_URL}/tasks/active`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('Aktif tasklar alınamadı');
    }
    return response.json();
}

export async function cancelTask(taskId: string): Promise<TaskStatus> {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/cancel`, {
        method: 'POST',
        credentials: 'include',
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new TaskRequestError(
            errorData.detail || 'Görev iptal edilemedi',
            response.status,
        );
    }
    return response.json();
}
