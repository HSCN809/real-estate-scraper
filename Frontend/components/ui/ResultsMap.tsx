'use client';

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { X, Building2, BarChart3, TrendingUp } from 'lucide-react';
import { ScrapeResult } from '@/types';
import { geoMercator, geoPath } from 'd3-geo';

// GeoJSON URL
const GEOJSON_URL = 'https://raw.githubusercontent.com/alpers/Turkey-Maps-GeoJSON/master/tr-cities.json';

// GeoJSON şehir adlarını veri kaynağı adlarına eşleştirme
const CITY_NAME_MAP: Record<string, string> = {
    'Afyon': 'Afyonkarahisar',
    'Nevsehir': 'Nevşehir',
    'Içel': 'Mersin',
    'Kirsehir': 'Kırşehir',
    'Kirikkale': 'Kırıkkale',
    'Kirklareli': 'Kırklareli',
    'Karabuk': 'Karabük',
    'Sanliurfa': 'Şanlıurfa',
    'Usak': 'Uşak',
    'Mugla': 'Muğla',
    'Igdir': 'Iğdır',
    'Agri': 'Ağrı',
    'Gumushane': 'Gümüşhane',
    'Duzce': 'Düzce',
    'Cankiri': 'Çankırı',
    'Canakkale': 'Çanakkale',
    'Corum': 'Çorum',
    'Eskisehir': 'Eskişehir',
    'Tekirdag': 'Tekirdağ',
    'Sirnak': 'Şırnak',
    'Mus': 'Muş',
    'Nigde': 'Niğde',
    'Isparta': 'Isparta',
    'Bolu': 'Bolu',
};

// Fiyat formatlama
const formatPrice = (price: number): string => {
    if (price >= 1000000) return `${(price / 1000000).toFixed(2)}M`;
    if (price >= 1000) return `${(price / 1000).toFixed(2)}K`;
    return price.toFixed(2);
};

// İlan sayısına göre renk belirleme
const getColorByCount = (count: number): string => {
    if (count >= 1000) return '#059669';
    if (count >= 50) return '#10b981';
    if (count >= 1) return '#6ee7b7';
    return '#334155';
};

interface GeoFeature {
    type: string;
    properties: { name: string; number: number };
    geometry: { type: string; coordinates: number[][][] | number[][][][] };
}

interface FileStats {
    stats: {
        count: number;
        mean: number;
        std: number;
        min: number;
        q25: number;
        median: number;
        q75: number;
        max: number;
    };
    price_ranges: Array<{
        range: string;
        count: number;
        percentage: number;
    }>;
    total_listings: number;
    districts?: string[];  // Şehir bazlı aggregation için ilçeler listesi
    files_count?: number;  // Kaç dosya işlendi
}

interface ResultsMapProps {
    results: ScrapeResult[];
}

export function ResultsMap({ results }: ResultsMapProps) {
    const [selectedCityName, setSelectedCityName] = useState<string | null>(null);
    const [hoveredCity, setHoveredCity] = useState<string | null>(null);
    const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
    const [geoData, setGeoData] = useState<GeoFeature[]>([]);
    const [cityStats, setCityStats] = useState<FileStats | null>(null);
    const [statsLoading, setStatsLoading] = useState(false);

    // GeoJSON yükle
    useEffect(() => {
        fetch(GEOJSON_URL)
            .then(res => res.json())
            .then(data => setGeoData(data.features || []))
            .catch(err => console.error('GeoJSON yüklenemedi:', err));
    }, []);

    // Türkçe karakterleri ASCII'ye çevir (helper function)
    const normalizeTurkish = (text: string) => {
        return text
            .replace(/İ/g, 'i').replace(/I/g, 'i')
            .replace(/Ş/g, 's').replace(/ş/g, 's')
            .replace(/Ğ/g, 'g').replace(/ğ/g, 'g')
            .replace(/Ü/g, 'u').replace(/ü/g, 'u')
            .replace(/Ö/g, 'o').replace(/ö/g, 'o')
            .replace(/Ç/g, 'c').replace(/ç/g, 'c')
            .toLowerCase();
    };

    // Şehir seçildiğinde o şehrin tüm ilçe verilerini aggregated olarak yükle
    useEffect(() => {
        if (selectedCityName) {
            setStatsLoading(true);
            setCityStats(null);

            const cityNameNormalized = normalizeTurkish(selectedCityName);
            console.log('Fetching city analytics for:', selectedCityName, '-> normalized:', cityNameNormalized);

            fetch(`http://localhost:8000/api/v1/analytics/city/${cityNameNormalized}`)
                .then(res => res.json())
                .then(data => {
                    console.log('City analytics response:', data);
                    if (data.stats) {
                        setCityStats(data);
                    } else {
                        console.warn('No stats in response:', data);
                    }
                })
                .catch(err => console.error('City stats yüklenemedi:', err))
                .finally(() => setStatsLoading(false));
        }
    }, [selectedCityName]);

    // Şehir verilerini map'e dönüştür
    const cityDataMap = useMemo(() => {
        const map = new Map<string, ScrapeResult>();
        results.forEach(result => {
            if (result.city) {
                map.set(result.city.toLowerCase(), result);
            }
        });
        return map;
    }, [results]);

    // SVG projeksiyon
    const { pathGenerator, width, height } = useMemo(() => {
        const w = 900;
        const h = 450;
        const projection = geoMercator()
            .center([35, 39])
            .scale(2200)
            .translate([w / 2, h / 2]);
        return { pathGenerator: geoPath().projection(projection), width: w, height: h };
    }, []);

    const handleCityClick = useCallback((cityName: string) => {
        const result = cityDataMap.get(cityName.toLowerCase());
        if (result) setSelectedCityName(cityName);
    }, [cityDataMap]);

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        setMousePosition({ x: e.clientX, y: e.clientY });
    }, []);

    return (
        <div className="flex flex-col gap-6" onMouseMove={handleMouseMove}>
            <div className="w-full flex justify-center items-center bg-slate-900/30 rounded-2xl border border-slate-700/50 p-4 md:p-8 min-h-[600px]">
                <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
                    {geoData.map((feature, i) => {
                        const geoName = feature.properties.name;
                        const dataName = CITY_NAME_MAP[geoName] || geoName;
                        const result = cityDataMap.get(dataName.toLowerCase());
                        const fillColor = result ? getColorByCount(result.count || 0) : '#334155';
                        const d = pathGenerator(feature.geometry as any) || '';

                        return (
                            <path
                                key={i}
                                d={d}
                                fill={fillColor}
                                stroke="#1e293b"
                                strokeWidth="0.5"
                                className="cursor-pointer transition-opacity hover:opacity-80"
                                onClick={() => handleCityClick(dataName)}
                                onMouseEnter={() => {
                                    const count = result?.count || 0;
                                    setHoveredCity(`${dataName}${count > 0 ? ` (${count} ilan)` : ''}`);
                                }}
                                onMouseLeave={() => setHoveredCity(null)}
                            />
                        );
                    })}
                </svg>
            </div>

            {hoveredCity && (
                <div
                    className="fixed pointer-events-none z-50 px-3 py-1.5 bg-slate-800 text-white text-sm rounded-lg shadow-lg border border-slate-600"
                    style={{ left: mousePosition.x + 15, top: mousePosition.y + 15 }}
                >
                    {hoveredCity}
                </div>
            )}

            <div className="flex justify-center gap-6 text-sm text-gray-400">
                <div className="flex items-center gap-2"><div className="w-4 h-4 rounded" style={{ backgroundColor: '#334155' }}></div><span>Veri Yok</span></div>
                <div className="flex items-center gap-2"><div className="w-4 h-4 rounded" style={{ backgroundColor: '#6ee7b7' }}></div><span>1-49 İlan</span></div>
                <div className="flex items-center gap-2"><div className="w-4 h-4 rounded" style={{ backgroundColor: '#10b981' }}></div><span>50-999 İlan</span></div>
                <div className="flex items-center gap-2"><div className="w-4 h-4 rounded" style={{ backgroundColor: '#059669' }}></div><span>1000+ İlan</span></div>
            </div>

            {selectedCityName && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setSelectedCityName(null)}>
                    <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-2xl w-full shadow-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-emerald-500/20 rounded-lg"><Building2 className="w-6 h-6 text-emerald-400" /></div>
                                <div>
                                    <h3 className="text-xl font-bold text-white">{selectedCityName}</h3>
                                    <p className="text-sm text-gray-400">
                                        Şehir Bazlı Toplu İstatistikler
                                    </p>
                                </div>
                            </div>
                            <button onClick={() => setSelectedCityName(null)} className="p-2 hover:bg-slate-800 rounded-lg"><X className="w-5 h-5 text-gray-400" /></button>
                        </div>

                        {/* Basic Stats Grid */}
                        <div className="grid grid-cols-2 gap-4 mb-6">
                            <div className="bg-slate-800/50 rounded-xl p-4">
                                <p className="text-gray-400 text-sm mb-1">Toplam İlan</p>
                                <p className="text-2xl font-bold text-emerald-400">
                                    {cityStats?.total_listings ? cityStats.total_listings.toLocaleString() : '0'}
                                </p>
                            </div>
                            <div className="bg-slate-800/50 rounded-xl p-4">
                                <p className="text-gray-400 text-sm mb-1">Ortalama Fiyat</p>
                                <p className="text-2xl font-bold text-blue-400">
                                    {cityStats?.stats?.mean ? `${formatPrice(cityStats.stats.mean)} ₺` : 'Veri yok'}
                                </p>
                            </div>
                        </div>

                        {/* Descriptive Statistics */}
                        {statsLoading ? (
                            <div className="flex items-center justify-center py-8">
                                <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                                <span className="ml-3 text-gray-400">İstatistikler yükleniyor...</span>
                            </div>
                        ) : cityStats?.stats ? (
                            <>
                                {/* Describe Stats */}
                                <div className="mb-6">
                                    <div className="flex items-center gap-2 mb-3">
                                        <TrendingUp className="w-5 h-5 text-purple-400" />
                                        <h4 className="text-lg font-semibold text-white">Fiyat İstatistikleri</h4>
                                    </div>
                                    <div className="grid grid-cols-4 gap-2 text-sm">
                                        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                            <p className="text-gray-500 text-xs">Min</p>
                                            <p className="text-white font-semibold">{formatPrice(cityStats.stats.min)} ₺</p>
                                        </div>
                                        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                            <p className="text-gray-500 text-xs">Q1</p>
                                            <p className="text-white font-semibold">{formatPrice(cityStats.stats.q25)} ₺</p>
                                        </div>
                                        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                            <p className="text-gray-500 text-xs">Medyan</p>
                                            <p className="text-amber-400 font-semibold">{formatPrice(cityStats.stats.median)} ₺</p>
                                        </div>
                                        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                            <p className="text-gray-500 text-xs">Q3</p>
                                            <p className="text-white font-semibold">{formatPrice(cityStats.stats.q75)} ₺</p>
                                        </div>
                                        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                            <p className="text-gray-500 text-xs">Max</p>
                                            <p className="text-white font-semibold">{formatPrice(cityStats.stats.max)} ₺</p>
                                        </div>
                                        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                            <p className="text-gray-500 text-xs">Ortalama</p>
                                            <p className="text-blue-400 font-semibold">{formatPrice(cityStats.stats.mean)} ₺</p>
                                        </div>
                                        <div className="bg-slate-800/50 rounded-lg p-3 text-center col-span-2">
                                            <p className="text-gray-500 text-xs">Std. Sapma</p>
                                            <p className="text-white font-semibold">{formatPrice(cityStats.stats.std)} ₺</p>
                                        </div>
                                    </div>
                                </div>

                                {/* Price Range Distribution */}
                                <div className="mb-6">
                                    <div className="flex items-center gap-2 mb-3">
                                        <BarChart3 className="w-5 h-5 text-cyan-400" />
                                        <h4 className="text-lg font-semibold text-white">Fiyat Aralığı Dağılımı</h4>
                                    </div>
                                    <div className="space-y-2">
                                        {cityStats.price_ranges.map((range, idx) => (
                                            <div key={idx} className="flex items-center gap-3">
                                                <div className="w-32 text-xs text-gray-400 truncate" title={range.range}>{range.range}</div>
                                                <div className="flex-1 h-6 bg-slate-800 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-full transition-all duration-500"
                                                        style={{ width: `${range.percentage}%` }}
                                                    ></div>
                                                </div>
                                                <div className="w-20 text-right text-xs">
                                                    <span className="text-white font-medium">{range.count}</span>
                                                    <span className="text-gray-500 ml-1">(%{range.percentage})</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </>
                        ) : null}
                    </div>
                </div>
            )}
        </div>
    );
}
