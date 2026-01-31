// API client for Real Estate Scraper Backend

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

import type { ScrapeRequest, ScrapeResponse, Platform, ScrapeResult } from '@/types';

export async function startScrape(platform: Platform, data: ScrapeRequest): Promise<ScrapeResponse> {
    const response = await fetch(`${API_BASE_URL}/scrape/${platform}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API error: ${response.status}`);
    }

    return response.json();
}

export async function healthCheck(): Promise<boolean> {
    try {
        const response = await fetch('http://localhost:8000/');
        return response.ok;
    } catch {
        return false;
    }
}


export async function getStats() {
    const response = await fetch(`${API_BASE_URL}/stats`);
    if (!response.ok) {
        throw new Error('İstatistikler alınamadı');
    }
    return response.json();
}

export async function getResults(): Promise<ScrapeResult[]> {
    const response = await fetch(`${API_BASE_URL}/results`);
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
    const response = await fetch(`${API_BASE_URL}/config/categories`);
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

export async function getSubtypes(listingType: string, category: string): Promise<SubtypesResponse> {
    const response = await fetch(`${API_BASE_URL}/config/subtypes?listing_type=${listingType}&category=${category}`);
    if (!response.ok) {
        throw new Error('Alt kategoriler alınamadı');
    }
    return response.json();
}

// DB-based listings endpoint
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

    const response = await fetch(`${API_BASE_URL}/listings?${searchParams}`);
    if (!response.ok) {
        throw new Error('İlanlar alınamadı');
    }
    return response.json();
}

// Excel export function
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
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Excel export başarısız');
    }

    return response.blob();
}

// Cities and districts from DB
export async function getCities(): Promise<{ cities: string[] }> {
    const response = await fetch(`${API_BASE_URL}/cities`);
    if (!response.ok) {
        throw new Error('Şehirler alınamadı');
    }
    return response.json();
}

export async function getDistricts(city: string): Promise<{ city: string; districts: string[] }> {
    const response = await fetch(`${API_BASE_URL}/cities/${city}/districts`);
    if (!response.ok) {
        throw new Error('İlçeler alınamadı');
    }
    return response.json();
}
