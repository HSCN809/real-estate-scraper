'use client';

import dynamic from 'next/dynamic';
import { Suspense } from 'react';
import { BarChart3 } from 'lucide-react';

// Loading component
function ChartLoadingSpinner() {
    return (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <div className="relative w-16 h-16 mb-4">
                <div className="absolute inset-0 border-4 border-blue-500/20 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-blue-500/80 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <BarChart3 className="w-12 h-12 opacity-50 mb-2" />
            <p className="text-sm">Grafikler yükleniyor...</p>
        </div>
    );
}

// Lazy load the heavy Chart.js component
const ResultsChartsInner = dynamic(() => import('./ResultsChartsInner'), {
    loading: () => <ChartLoadingSpinner />,
    ssr: false
});

interface PriceData {
    city: string;
    platform: string;
    category: string;
    listing_type: string;
    price: number;
}

interface ResultsChartsProps {
    results: any[];
    priceData: PriceData[];
    categoryFilter: string;
    listingTypeFilter: string;
}

export function ResultsCharts({ results, priceData, categoryFilter, listingTypeFilter }: ResultsChartsProps) {
    return (
        <Suspense fallback={<ChartLoadingSpinner />}>
            <ResultsChartsInner
                results={results}
                priceData={priceData}
                categoryFilter={categoryFilter}
                listingTypeFilter={listingTypeFilter}
            />
        </Suspense>
    );
}
