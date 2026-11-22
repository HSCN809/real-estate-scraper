'use client';

import React, { useMemo, useRef, useState, useCallback, useEffect } from 'react';
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
import type { ResultsChartsProps } from './ResultsCharts';
import { BarChart3, PieChart, TrendingUp, Building2, MapPin, DollarSign, Layers, Clock, ChevronLeft, ChevronRight } from 'lucide-react';

// Chart.js bileşenlerini kaydet
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

// Grafik renkleri
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

// Ortak grafik seçenekleri
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


// Sabit kart yüksekliği (header + chart + padding)
const CARD_HEIGHT = 'h-[420px]';

// Grafik Kartı Bileşeni - Carousel item olarak
function ChartCard({ title, icon: Icon, children, className = '' }: {
    title: string;
    icon: React.ElementType;
    children: React.ReactNode;
    className?: string;
}) {
    return (
        <div className="snap-center flex-shrink-0 w-[85vw] md:w-[600px] lg:w-[700px]">
            <ArtCard glowColor="blue" className={`${CARD_HEIGHT} flex flex-col ${className}`}>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-blue-500/20 rounded-lg">
                        <Icon className="w-5 h-5 text-blue-400" />
                    </div>
                    <h3 className="text-lg font-bold text-white">{title}</h3>
                </div>
                <div className="flex-1 min-h-0">
                    {children}
                </div>
            </ArtCard>
        </div>
    );
}

// Placeholder Kartı - Fiyat filtreleri seçilmediğinde
function PlaceholderCard({ title, icon: Icon }: { title: string; icon: React.ElementType }) {
    return (
        <div className="snap-center flex-shrink-0 w-[85vw] md:w-[600px] lg:w-[700px]">
            <ArtCard glowColor="blue" className={`${CARD_HEIGHT} flex flex-col items-center justify-center text-center`}>
                <Icon className="w-12 h-12 text-gray-600 mb-4" />
                <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
                <p className="text-gray-400 text-sm">Fiyat analizini görmek için<br /><span className="text-amber-400">Kategori</span> ve <span className="text-amber-400">İlan Tipi</span> filtresi seçin</p>
            </ArtCard>
        </div>
    );
}

export default function ResultsChartsInner({ overview, priceData, categoryFilter, listingTypeFilter }: ResultsChartsProps) {
    const showPriceCharts = categoryFilter !== 'all' && listingTypeFilter !== 'all';

    const { cityDistributionData, platformData, listingTypeData, categoryData, scrapingHistoryData } = useMemo(() => {
        const topCities = overview.cities.slice(0, 10);
        return {
            cityDistributionData: {
                labels: topCities.map(({ city }) => city),
                datasets: [{
                    label: 'İlan Sayısı',
                    data: topCities.map(({ count }) => count),
                    backgroundColor: CHART_PALETTE,
                    borderColor: CHART_PALETTE.map(c => c.replace('0.8', '1')),
                    borderWidth: 1,
                }],
            },
            platformData: {
                labels: Object.keys(overview.platforms),
                datasets: [{
                    data: Object.values(overview.platforms),
                    backgroundColor: [COLORS.purple, COLORS.blue, COLORS.emerald],
                    borderColor: ['rgba(139, 92, 246, 1)', 'rgba(59, 130, 246, 1)', 'rgba(16, 185, 129, 1)'],
                    borderWidth: 2,
                }],
            },
            listingTypeData: {
                labels: Object.keys(overview.listing_types),
                datasets: [{
                    data: Object.values(overview.listing_types),
                    backgroundColor: [COLORS.amber, COLORS.orange, COLORS.slate],
                    borderColor: ['rgba(245, 158, 11, 1)', 'rgba(249, 115, 22, 1)', 'rgba(100, 116, 139, 1)'],
                    borderWidth: 2,
                }],
            },
            categoryData: {
                labels: Object.keys(overview.categories),
                datasets: [{
                    data: Object.values(overview.categories),
                    backgroundColor: [COLORS.emerald, COLORS.cyan, COLORS.purple, COLORS.pink],
                    borderColor: ['rgba(16, 185, 129, 1)', 'rgba(6, 182, 212, 1)', 'rgba(139, 92, 246, 1)', 'rgba(236, 72, 153, 1)'],
                    borderWidth: 2,
                }],
            },
            scrapingHistoryData: {
                labels: overview.history.map(({ date }) => date.split('-').reverse().join('.')),
                datasets: [{
                    label: 'Toplam İlan',
                    data: overview.history.map(({ count }) => count),
                    fill: true,
                    backgroundColor: COLORS.blueBg,
                    borderColor: COLORS.blue,
                    borderWidth: 2,
                    tension: 0.4,
                }],
            },
        };
    }, [overview]);

    const { cityPriceData, priceHistogramData, platformPriceData } = useMemo(() => {
        const cities = priceData?.cities ?? [];
        const bins = priceData?.histogram ?? [];
        const platforms = priceData?.platforms ?? [];
        const formatPrice = (price: number) => {
            if (price >= 1000000) return (price / 1000000).toFixed(1) + 'M';
            if (price >= 1000) return (price / 1000).toFixed(0) + 'K';
            return price.toFixed(0);
        };
        return {
            cityPriceData: {
                labels: cities.map(({ city }) => city),
                datasets: [{
                    label: 'Ortalama Fiyat (₺)',
                    data: cities.map(({ avg_price }) => Math.round(avg_price)),
                    backgroundColor: COLORS.emeraldBg,
                    borderColor: COLORS.emerald,
                    borderWidth: 2,
                }],
            },
            priceHistogramData: {
                labels: bins.map(({ min, max }) => formatPrice(min) + ' - ' + formatPrice(max)),
                datasets: [{
                    label: 'İlan Sayısı',
                    data: bins.map(({ count }) => count),
                    backgroundColor: COLORS.purpleBg,
                    borderColor: COLORS.purple,
                    borderWidth: 2,
                }],
            },
            platformPriceData: {
                labels: platforms.map(({ platform }) => platform),
                datasets: [{
                    label: 'Ortalama Fiyat (₺)',
                    data: platforms.map(({ avg_price }) => Math.round(avg_price)),
                    backgroundColor: [COLORS.purple, COLORS.blue, COLORS.emerald],
                    borderColor: ['rgba(139, 92, 246, 1)', 'rgba(59, 130, 246, 1)', 'rgba(16, 185, 129, 1)'],
                    borderWidth: 2,
                }],
            },
        };
    }, [priceData]);

    // Pasta grafik seçenekleri
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

    // Yatay çubuk grafik seçenekleri
    const horizontalBarOptions = {
        ...commonOptions,
        indexAxis: 'y' as const,
        plugins: {
            ...commonOptions.plugins,
            legend: { display: false }
        }
    };

    // Çizgi grafik seçenekleri
    const lineOptions = {
        ...commonOptions,
        plugins: {
            ...commonOptions.plugins,
            legend: { display: false }
        }
    };

    // Carousel state
    const scrollRef = useRef<HTMLDivElement>(null);
    const [activeIndex, setActiveIndex] = useState(0);
    const totalSlides = showPriceCharts ? 8 : 8; // Her zaman 8 kart (placeholder dahil)

    // Scroll event'inde aktif index'i güncelle
    const handleScroll = useCallback(() => {
        const container = scrollRef.current;
        if (!container) return;
        const children = Array.from(container.children) as HTMLElement[];
        if (children.length === 0) return;

        const containerCenter = container.scrollLeft + container.clientWidth / 2;
        let closestIndex = 0;
        let closestDistance = Infinity;

        children.forEach((child, index) => {
            const childCenter = child.offsetLeft + child.offsetWidth / 2;
            const distance = Math.abs(containerCenter - childCenter);
            if (distance < closestDistance) {
                closestDistance = distance;
                closestIndex = index;
            }
        });

        setActiveIndex(closestIndex);
    }, []);

    useEffect(() => {
        const container = scrollRef.current;
        if (!container) return;
        container.addEventListener('scroll', handleScroll, { passive: true });
        return () => container.removeEventListener('scroll', handleScroll);
    }, [handleScroll]);

    // Belirli bir slide'a kaydır
    const scrollToIndex = useCallback((index: number) => {
        const container = scrollRef.current;
        if (!container) return;
        const children = Array.from(container.children) as HTMLElement[];
        if (!children[index]) return;

        const child = children[index];
        const scrollLeft = child.offsetLeft - (container.clientWidth / 2) + (child.offsetWidth / 2);
        container.scrollTo({ left: scrollLeft, behavior: 'smooth' });
    }, []);

    const scrollPrev = useCallback(() => {
        scrollToIndex(Math.max(0, activeIndex - 1));
    }, [activeIndex, scrollToIndex]);

    const scrollNext = useCallback(() => {
        scrollToIndex(Math.min(totalSlides - 1, activeIndex + 1));
    }, [activeIndex, totalSlides, scrollToIndex]);

    if (overview.cities.length === 0) {
        return (
            <div className="text-center py-20 text-gray-400">
                <BarChart3 className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Grafik oluşturmak için veri bulunamadı</p>
            </div>
        );
    }

    // Grafik başlıkları (dot indicator için)
    const chartTitles = [
        'Şehir Dağılımı', 'Platform', 'Satılık/Kiralık', 'Kategori',
        'Şehir Fiyat', 'Fiyat Aralığı', 'Platform Fiyat', 'Tarama Geçmişi'
    ];

    return (
        <div className="relative">
            {/* Carousel Container */}
            <div
                ref={scrollRef}
                className="flex gap-6 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-4 px-[calc(50%-min(42.5vw,350px))]"
            >
                {/* 1. Şehir Dağılımı */}
                <ChartCard title="Şehir Bazlı İlan Dağılımı" icon={MapPin}>
                    <Bar data={cityDistributionData} options={horizontalBarOptions} />
                </ChartCard>

                {/* 2. Platform Karşılaştırması */}
                <ChartCard title="Platform Karşılaştırması" icon={Building2}>
                    <Doughnut data={platformData} options={pieOptions} />
                </ChartCard>

                {/* 3. Satılık vs Kiralık */}
                <ChartCard title="Satılık vs Kiralık" icon={Layers}>
                    <Pie data={listingTypeData} options={pieOptions} />
                </ChartCard>

                {/* 4. Kategori Dağılımı */}
                <ChartCard title="Kategori Dağılımı" icon={PieChart}>
                    <Doughnut data={categoryData} options={pieOptions} />
                </ChartCard>

                {/* 5. Şehir Bazlı Ortalama Fiyat */}
                {showPriceCharts ? (
                    <ChartCard title="Şehir Bazlı Ortalama Fiyat" icon={DollarSign}>
                        <Bar data={cityPriceData} options={horizontalBarOptions} />
                    </ChartCard>
                ) : (
                    <PlaceholderCard title="Şehir Bazlı Ortalama Fiyat" icon={DollarSign} />
                )}

                {/* 6. Fiyat Aralığı Dağılımı */}
                {showPriceCharts ? (
                    <ChartCard title="Fiyat Aralığı Dağılımı" icon={BarChart3}>
                        <Bar data={priceHistogramData} options={{
                            ...commonOptions,
                            plugins: { ...commonOptions.plugins, legend: { display: false } }
                        }} />
                    </ChartCard>
                ) : (
                    <PlaceholderCard title="Fiyat Aralığı Dağılımı" icon={BarChart3} />
                )}

                {/* 7. Platform Fiyat Karşılaştırması */}
                {showPriceCharts ? (
                    <ChartCard title="Platform Fiyat Karşılaştırması" icon={TrendingUp}>
                        <Bar data={platformPriceData} options={{
                            ...commonOptions,
                            plugins: { ...commonOptions.plugins, legend: { display: false } }
                        }} />
                    </ChartCard>
                ) : (
                    <PlaceholderCard title="Platform Fiyat Karşılaştırması" icon={TrendingUp} />
                )}

                {/* 8. Tarama Geçmişi */}
                <ChartCard title="Tarama Geçmişi" icon={Clock}>
                    <Line data={scrapingHistoryData} options={lineOptions} />
                </ChartCard>
            </div>

            {/* Navigasyon Okları */}
            <button
                onClick={scrollPrev}
                disabled={activeIndex === 0}
                className={`absolute left-2 top-1/2 -translate-y-1/2 z-10 p-2.5 rounded-full bg-slate-800/80 border border-slate-700/50 backdrop-blur-sm transition-all ${
                    activeIndex === 0 ? 'opacity-30 cursor-not-allowed' : 'hover:bg-slate-700 hover:scale-110'
                }`}
                aria-label="Önceki grafik"
            >
                <ChevronLeft className="w-5 h-5 text-white" />
            </button>
            <button
                onClick={scrollNext}
                disabled={activeIndex === totalSlides - 1}
                className={`absolute right-2 top-1/2 -translate-y-1/2 z-10 p-2.5 rounded-full bg-slate-800/80 border border-slate-700/50 backdrop-blur-sm transition-all ${
                    activeIndex === totalSlides - 1 ? 'opacity-30 cursor-not-allowed' : 'hover:bg-slate-700 hover:scale-110'
                }`}
                aria-label="Sonraki grafik"
            >
                <ChevronRight className="w-5 h-5 text-white" />
            </button>

            {/* Dot Indicator + Başlık */}
            <div className="flex flex-col items-center gap-2 mt-4">
                <span className="text-sm text-gray-400 font-medium">{chartTitles[activeIndex]}</span>
                <div className="flex items-center gap-2">
                    {Array.from({ length: totalSlides }).map((_, i) => (
                        <button
                            key={i}
                            onClick={() => scrollToIndex(i)}
                            className={`rounded-full transition-all duration-300 ${
                                i === activeIndex
                                    ? 'w-6 h-2.5 bg-blue-500'
                                    : 'w-2.5 h-2.5 bg-slate-600 hover:bg-slate-500'
                            }`}
                            aria-label={`${chartTitles[i]} grafiğine git`}
                        />
                    ))}
                </div>
                <span className="text-xs text-gray-500">{activeIndex + 1} / {totalSlides}</span>
            </div>
        </div>
    );
}
