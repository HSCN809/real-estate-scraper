'use client';

import dynamic from 'next/dynamic';
import { Suspense } from 'react';
import { Map, Loader2 } from 'lucide-react';
import type { ScrapeResult } from '@/types';

// Loading component
function MapLoadingSkeleton() {
    return (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <Loader2 className="w-12 h-12 animate-spin text-blue-400 mb-4" />
            <Map className="w-16 h-16 opacity-50 mb-2" />
            <p className="text-sm">Harita yükleniyor...</p>
        </div>
    );
}

// Lazy load the heavy D3-geo component
const ResultsMapInner = dynamic(() => import('./ResultsMapInner'), {
    loading: () => <MapLoadingSkeleton />,
    ssr: false
});

interface ResultsMapProps {
    results: ScrapeResult[];
    platformFilter?: string;
    categoryFilter?: string;
    listingTypeFilter?: string;
    subtypeFilter?: string;
}

export function ResultsMap({
    results,
    platformFilter = 'all',
    categoryFilter = 'all',
    listingTypeFilter = 'all',
    subtypeFilter = 'all',
}: ResultsMapProps) {
    return (
        <Suspense fallback={<MapLoadingSkeleton />}>
            <ResultsMapInner
                results={results}
                platformFilter={platformFilter}
                categoryFilter={categoryFilter}
                listingTypeFilter={listingTypeFilter}
                subtypeFilter={subtypeFilter}
            />
        </Suspense>
    );
}
