// Emlak Scraper Backend API istemcisi

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

import type { ScrapeRequest, ScrapeResponse, Platform, ScrapeResult } from '@/types';

export async function startScrape(platform: Platform, data: ScrapeRequest): Promise<ScrapeResponse> {
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

export async function getResults(): Promise<ScrapeResult[]> {
    const response = await fetch(`${API_BASE_URL}/results`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('Sonuçlar alınamadı');
    }
    return response.json();
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
    items: any[];
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

export interface TaskStatus {
    task_id?: string;
    status?: string;
    is_running: boolean;
    message: string;
    progress: number;
    total: number;
    current: number;
    details: string;
    should_stop?: boolean;
    stopped_early?: boolean;
    started_at?: string;
    updated_at?: string;
}

export async function getTaskStatus(taskId?: string): Promise<TaskStatus> {
    const url = taskId
        ? `${API_BASE_URL}/status?task_id=${taskId}`
        : `${API_BASE_URL}/status`;

    const response = await fetch(url, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('Task durumu alınamadı');
    }
    return response.json();
}

export async function stopTask(taskId?: string): Promise<{ status: string; message: string; task_id?: string }> {
    const url = taskId
        ? `${API_BASE_URL}/stop?task_id=${taskId}`
        : `${API_BASE_URL}/stop`;

    const response = await fetch(url, {
        method: 'POST',
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('Task durdurulamadı');
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
