// API client for Real Estate Scraper Backend

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

import type { ScrapeRequest, ScrapeResponse, Platform } from '@/types';

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
