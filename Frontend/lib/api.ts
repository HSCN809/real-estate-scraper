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
        throw new Error(`API error: ${response.status}`);
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
