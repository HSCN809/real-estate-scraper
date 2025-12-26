'use client';

import React, { useMemo } from 'react';
import { ArtCard } from '@/components/ui/ArtCard';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    PointElement,
    LineElement,
    Filler,
} from 'chart.js';
import { Bar, Doughnut, Pie, Line } from 'react-chartjs-2';
import { ScrapeResult } from '@/types';
import { BarChart3, PieChart, TrendingUp, Building2, MapPin, DollarSign, Layers, Clock } from 'lucide-react';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    PointElement,
    LineElement,
    Filler
);

// Chart colors
const COLORS = {
    blue: 'rgba(59, 130, 246, 0.8)',
    blueBg: 'rgba(59, 130, 246, 0.2)',
    emerald: 'rgba(16, 185, 129, 0.8)',
    emeraldBg: 'rgba(16, 185, 129, 0.2)',
    purple: 'rgba(139, 92, 246, 0.8)',
    purpleBg: 'rgba(139, 92, 246, 0.2)',
    amber: 'rgba(245, 158, 11, 0.8)',
    amberBg: 'rgba(245, 158, 11, 0.2)',
    pink: 'rgba(236, 72, 153, 0.8)',
    pinkBg: 'rgba(236, 72, 153, 0.2)',
    cyan: 'rgba(6, 182, 212, 0.8)',
    cyanBg: 'rgba(6, 182, 212, 0.2)',
    orange: 'rgba(249, 115, 22, 0.8)',
    orangeBg: 'rgba(249, 115, 22, 0.2)',
    slate: 'rgba(100, 116, 139, 0.8)',
    slateBg: 'rgba(100, 116, 139, 0.2)',
};

const CHART_PALETTE = [
    COLORS.blue, COLORS.emerald, COLORS.purple, COLORS.amber,
    COLORS.pink, COLORS.cyan, COLORS.orange, COLORS.slate,
    'rgba(34, 197, 94, 0.8)', 'rgba(239, 68, 68, 0.8)'
];

// Common chart options
const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                color: '#94a3b8',
                font: { size: 12 }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.9)',
            titleColor: '#f1f5f9',
            bodyColor: '#cbd5e1',
            borderColor: 'rgba(100, 116, 139, 0.3)',
            borderWidth: 1,
        }
    },
    scales: {
        x: {
            ticks: { color: '#64748b' },
            grid: { color: 'rgba(100, 116, 139, 0.1)' }
        },
        y: {
            ticks: { color: '#64748b' },
            grid: { color: 'rgba(100, 116, 139, 0.1)' }
        }
    }
};

interface PriceData {
    city: string;
    platform: string;
    category: string;
    listing_type: string;
    price: number;
}

interface ResultsChartsProps {
    results: ScrapeResult[];
    priceData: PriceData[];
    categoryFilter: string;
    listingTypeFilter: string;
}

// Chart Card Component
function ChartCard({ title, icon: Icon, children, className = '' }: {
    title: string;
    icon: React.ElementType;
    children: React.ReactNode;
    className?: string;
}) {
    return (
        <ArtCard glowColor="blue" className={`${className}`}>
            <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                    <Icon className="w-5 h-5 text-blue-400" />
                </div>
                <h3 className="text-lg font-bold text-white">{title}</h3>
            </div>
            <div className="h-[280px]">
                {children}
            </div>
        </ArtCard>
    );
}

export function ResultsCharts({ results, priceData, categoryFilter, listingTypeFilter }: ResultsChartsProps) {
    // Check if price charts should be shown (only when BOTH category AND listing type filters are active)
    const showPriceCharts = categoryFilter !== 'all' && listingTypeFilter !== 'all';

    // 1. City Distribution - Top 10 cities by listing count
    const cityDistributionData = useMemo(() => {
        const cityCount: Record<string, number> = {};
        results.forEach(r => {
            if (r.city) {
                cityCount[r.city] = (cityCount[r.city] || 0) + (r.count || 0);
            }
        });

        const sorted = Object.entries(cityCount)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);

        return {
            labels: sorted.map(([city]) => city),
            datasets: [{
                label: 'İlan Sayısı',
                data: sorted.map(([, count]) => count),
                backgroundColor: CHART_PALETTE,
                borderColor: CHART_PALETTE.map(c => c.replace('0.8', '1')),
                borderWidth: 1,
            }]
        };
    }, [results]);

    // 2. Platform Comparison
    const platformData = useMemo(() => {
        const platformCount: Record<string, number> = {};
        results.forEach(r => {
            platformCount[r.platform] = (platformCount[r.platform] || 0) + (r.count || 0);
        });

        return {
            labels: Object.keys(platformCount),
            datasets: [{
                data: Object.values(platformCount),
                backgroundColor: [COLORS.purple, COLORS.blue, COLORS.emerald],
                borderColor: ['rgba(139, 92, 246, 1)', 'rgba(59, 130, 246, 1)', 'rgba(16, 185, 129, 1)'],
                borderWidth: 2,
            }]
        };
    }, [results]);

    // 3. Listing Type (Satılık vs Kiralık)
    const listingTypeData = useMemo(() => {
        const typeCount: Record<string, number> = {};
        results.forEach(r => {
            const type = r.listing_type || 'Bilinmiyor';
            typeCount[type] = (typeCount[type] || 0) + (r.count || 0);
        });

        return {
            labels: Object.keys(typeCount),
            datasets: [{
                data: Object.values(typeCount),
                backgroundColor: [COLORS.amber, COLORS.orange, COLORS.slate],
                borderColor: ['rgba(245, 158, 11, 1)', 'rgba(249, 115, 22, 1)', 'rgba(100, 116, 139, 1)'],
                borderWidth: 2,
            }]
        };
    }, [results]);

    // 4. Category Distribution
    const categoryData = useMemo(() => {
        const catCount: Record<string, number> = {};
        results.forEach(r => {
            catCount[r.category] = (catCount[r.category] || 0) + (r.count || 0);
        });

        return {
            labels: Object.keys(catCount),
            datasets: [{
                data: Object.values(catCount),
                backgroundColor: [COLORS.emerald, COLORS.cyan, COLORS.purple, COLORS.pink],
                borderColor: ['rgba(16, 185, 129, 1)', 'rgba(6, 182, 212, 1)', 'rgba(139, 92, 246, 1)', 'rgba(236, 72, 153, 1)'],
                borderWidth: 2,
            }]
        };
    }, [results]);

    // 5. City Average Price - Top 10
    const cityPriceData = useMemo(() => {
        const cityPrices: Record<string, number[]> = {};
        priceData.forEach(p => {
            if (!cityPrices[p.city]) cityPrices[p.city] = [];
            cityPrices[p.city].push(p.price);
        });

        const avgPrices = Object.entries(cityPrices)
            .map(([city, prices]) => ({
                city,
                avg: prices.reduce((a, b) => a + b, 0) / prices.length
            }))
            .sort((a, b) => b.avg - a.avg)
            .slice(0, 10);

        return {
            labels: avgPrices.map(p => p.city),
            datasets: [{
                label: 'Ortalama Fiyat (₺)',
                data: avgPrices.map(p => Math.round(p.avg)),
                backgroundColor: COLORS.emeraldBg,
                borderColor: COLORS.emerald,
                borderWidth: 2,
            }]
        };
    }, [priceData]);

    // 6. Price Histogram - Quantile-based bins for meaningful distribution
    const priceHistogramData = useMemo(() => {
        if (priceData.length === 0) {
            return { labels: [], datasets: [{ label: 'İlan Sayısı', data: [], backgroundColor: COLORS.blue }] };
        }

        const prices = priceData.map(p => p.price).sort((a, b) => a - b);
        const n = prices.length;

        // Dynamic formatting based on price value
        const formatPrice = (price: number): string => {
            if (price >= 1000000) {
                return `${(price / 1000000).toFixed(1)}M`;
            } else if (price >= 1000) {
                return `${(price / 1000).toFixed(0)}K`;
            } else {
                return `${price.toFixed(0)}`;
            }
        };

        // Calculate quantile edges (10 bins = 9 cut points)
        const numBins = 10;
        const edges: number[] = [prices[0]]; // Start with min

        for (let i = 1; i < numBins; i++) {
            const idx = Math.floor((i / numBins) * n);
            edges.push(prices[idx]);
        }
        edges.push(prices[n - 1]); // End with max

        // Remove duplicate edges and create unique bins
        const uniqueEdges: number[] = [edges[0]];
        for (let i = 1; i < edges.length; i++) {
            if (edges[i] > uniqueEdges[uniqueEdges.length - 1]) {
                uniqueEdges.push(edges[i]);
            }
        }

        // Create labels and count items in each bin
        const bins: number[] = [];
        const labels: string[] = [];

        for (let i = 0; i < uniqueEdges.length - 1; i++) {
            const low = uniqueEdges[i];
            const high = uniqueEdges[i + 1];
            labels.push(`${formatPrice(low)} - ${formatPrice(high)}`);

            // Count items in this range
            let count = 0;
            if (i === uniqueEdges.length - 2) {
                // Last bin includes upper edge
                count = prices.filter(p => p >= low && p <= high).length;
            } else {
                count = prices.filter(p => p >= low && p < high).length;
            }
            bins.push(count);
        }

        return {
            labels,
            datasets: [{
                label: 'İlan Sayısı',
                data: bins,
                backgroundColor: COLORS.purpleBg,
                borderColor: COLORS.purple,
                borderWidth: 2,
            }]
        };
    }, [priceData]);

    // 7. Platform Price Comparison
    const platformPriceData = useMemo(() => {
        const platformPrices: Record<string, number[]> = {};
        priceData.forEach(p => {
            if (!platformPrices[p.platform]) platformPrices[p.platform] = [];
            platformPrices[p.platform].push(p.price);
        });

        const platforms = Object.keys(platformPrices);
        const avgPrices = platforms.map(platform => {
            const prices = platformPrices[platform];
            return Math.round(prices.reduce((a, b) => a + b, 0) / prices.length);
        });

        return {
            labels: platforms,
            datasets: [{
                label: 'Ortalama Fiyat (₺)',
                data: avgPrices,
                backgroundColor: [COLORS.purple, COLORS.blue, COLORS.emerald],
                borderColor: ['rgba(139, 92, 246, 1)', 'rgba(59, 130, 246, 1)', 'rgba(16, 185, 129, 1)'],
                borderWidth: 2,
            }]
        };
    }, [priceData]);

    // 8. Scraping History (by date)
    const scrapingHistoryData = useMemo(() => {
        const dateCount: Record<string, number> = {};
        results.forEach(r => {
            if (r.date) {
                const datePart = r.date.split(' ')[0]; // Get only date part
                dateCount[datePart] = (dateCount[datePart] || 0) + (r.count || 0);
            }
        });

        const sorted = Object.entries(dateCount)
            .sort((a, b) => a[0].localeCompare(b[0]))
            .slice(-10); // Last 10 dates

        return {
            labels: sorted.map(([date]) => date),
            datasets: [{
                label: 'Toplam İlan',
                data: sorted.map(([, count]) => count),
                fill: true,
                backgroundColor: COLORS.blueBg,
                borderColor: COLORS.blue,
                borderWidth: 2,
                tension: 0.4,
            }]
        };
    }, [results]);

    // Pie/Doughnut options (no scales)
    const pieOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom' as const,
                labels: {
                    color: '#94a3b8',
                    font: { size: 11 },
                    padding: 15,
                }
            },
            tooltip: commonOptions.plugins.tooltip
        }
    };

    // Horizontal bar options
    const horizontalBarOptions = {
        ...commonOptions,
        indexAxis: 'y' as const,
        plugins: {
            ...commonOptions.plugins,
            legend: { display: false }
        }
    };

    // Line chart options
    const lineOptions = {
        ...commonOptions,
        plugins: {
            ...commonOptions.plugins,
            legend: { display: false }
        }
    };

    if (results.length === 0) {
        return (
            <div className="text-center py-20 text-gray-400">
                <BarChart3 className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Grafik oluşturmak için veri bulunamadı</p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-h-[calc(100vh-300px)] overflow-y-auto pr-2 pb-4">
            {/* 1. City Distribution */}
            <ChartCard title="Şehir Bazlı İlan Dağılımı" icon={MapPin}>
                <Bar data={cityDistributionData} options={horizontalBarOptions} />
            </ChartCard>

            {/* 2. Platform Comparison */}
            <ChartCard title="Platform Karşılaştırması" icon={Building2}>
                <Doughnut data={platformData} options={pieOptions} />
            </ChartCard>

            {/* 3. Listing Type */}
            <ChartCard title="Satılık vs Kiralık" icon={Layers}>
                <Pie data={listingTypeData} options={pieOptions} />
            </ChartCard>

            {/* 4. Category Distribution */}
            <ChartCard title="Kategori Dağılımı" icon={PieChart}>
                <Doughnut data={categoryData} options={pieOptions} />
            </ChartCard>

            {/* 5. City Average Price - Conditional */}
            {showPriceCharts ? (
                <ChartCard title="Şehir Bazlı Ortalama Fiyat" icon={DollarSign}>
                    <Bar data={cityPriceData} options={horizontalBarOptions} />
                </ChartCard>
            ) : (
                <ArtCard glowColor="blue" className="flex flex-col items-center justify-center text-center">
                    <DollarSign className="w-12 h-12 text-gray-600 mb-4" />
                    <h3 className="text-lg font-bold text-white mb-2">Şehir Bazlı Ortalama Fiyat</h3>
                    <p className="text-gray-400 text-sm">Fiyat analizini görmek için<br /><span className="text-amber-400">Kategori</span> ve <span className="text-amber-400">İlan Tipi</span> filtresi seçin</p>
                </ArtCard>
            )}

            {/* 6. Price Histogram - Conditional */}
            {showPriceCharts ? (
                <ChartCard title="Fiyat Aralığı Dağılımı" icon={BarChart3}>
                    <Bar data={priceHistogramData} options={{
                        ...commonOptions,
                        plugins: { ...commonOptions.plugins, legend: { display: false } }
                    }} />
                </ChartCard>
            ) : (
                <ArtCard glowColor="blue" className="flex flex-col items-center justify-center text-center">
                    <BarChart3 className="w-12 h-12 text-gray-600 mb-4" />
                    <h3 className="text-lg font-bold text-white mb-2">Fiyat Aralığı Dağılımı</h3>
                    <p className="text-gray-400 text-sm">Fiyat analizini görmek için<br /><span className="text-amber-400">Kategori</span> ve <span className="text-amber-400">İlan Tipi</span> filtresi seçin</p>
                </ArtCard>
            )}

            {/* 7. Platform Price Comparison - Conditional */}
            {showPriceCharts ? (
                <ChartCard title="Platform Fiyat Karşılaştırması" icon={TrendingUp}>
                    <Bar data={platformPriceData} options={{
                        ...commonOptions,
                        plugins: { ...commonOptions.plugins, legend: { display: false } }
                    }} />
                </ChartCard>
            ) : (
                <ArtCard glowColor="blue" className="flex flex-col items-center justify-center text-center">
                    <TrendingUp className="w-12 h-12 text-gray-600 mb-4" />
                    <h3 className="text-lg font-bold text-white mb-2">Platform Fiyat Karşılaştırması</h3>
                    <p className="text-gray-400 text-sm">Fiyat analizini görmek için<br /><span className="text-amber-400">Kategori</span> ve <span className="text-amber-400">İlan Tipi</span> filtresi seçin</p>
                </ArtCard>
            )}

            {/* 8. Scraping History */}
            <ChartCard title="Tarama Geçmişi" icon={Clock}>
                <Line data={scrapingHistoryData} options={lineOptions} />
            </ChartCard>
        </div>
    );
}
