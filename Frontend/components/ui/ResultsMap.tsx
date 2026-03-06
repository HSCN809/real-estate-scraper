'use client';

import dynamic from 'next/dynamic';
import { Suspense } from 'react';
import { Map, Loader2 } from 'lucide-react';

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
    results: any[];
}

export function ResultsMap({ results }: ResultsMapProps) {
    return (
        <Suspense fallback={<MapLoadingSkeleton />}>
            <ResultsMapInner results={results} />
        </Suspense>
    );
}
