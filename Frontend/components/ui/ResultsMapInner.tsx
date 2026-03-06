'use client';

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { X, Building2, BarChart3, TrendingUp, MapPin, Database, Sparkles, TrendingUp as TrendIcon } from 'lucide-react';
import { ScrapeResult } from '@/types';
import { geoMercator, geoPath } from 'd3-geo';
import SpotlightCard from '@/components/ui/SpotlightCard';
import { GlassCard } from '@/components/ui/GlassCard';
import { motion } from 'framer-motion';

// GeoJSON adresi
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

export default function ResultsMapInner({ results }: ResultsMapProps) {
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

    // Türkçe karakterleri normalize et
    const normalizeCity = (name: string): string => {
        return name.toLowerCase()
            .replace(/ı/g, 'i')
            .replace(/ğ/g, 'g')
            .replace(/ü/g, 'u')
            .replace(/ş/g, 's')
            .replace(/ö/g, 'o')
            .replace(/ç/g, 'c');
    };

    // Şehir verilerini map'e dönüştür (aynı şehir için count'ları topla)
    const cityDataMap = useMemo(() => {
        const map = new Map<string, ScrapeResult>();
        results.forEach(result => {
            if (result.city) {
                const normalizedCity = normalizeCity(result.city);
                const existing = map.get(normalizedCity);
                if (existing) {
                    // Aynı şehir için count'ları topla
                    map.set(normalizedCity, {
                        ...existing,
                        count: (existing.count || 0) + (result.count || 0)
                    });
                } else {
                    map.set(normalizedCity, result);
                }
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
        const result = cityDataMap.get(normalizeCity(cityName));
        if (result) setSelectedCityName(cityName);
    }, [cityDataMap]);

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        setMousePosition({ x: e.clientX, y: e.clientY });
    }, []);

    return (
        <div className="flex flex-col gap-6" onMouseMove={handleMouseMove}>
            <SpotlightCard className="p-4 md:p-8 min-h-[600px]">
                <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
                    {geoData.map((feature, i) => {
                        const geoName = feature.properties.name;
                        const dataName = CITY_NAME_MAP[geoName] || geoName;
                        const result = cityDataMap.get(normalizeCity(dataName));
                        const fillColor = result ? getColorByCount(result.count || 0) : '#334155';
                        const d = pathGenerator(feature.geometry as any) || '';

                        return (
                            <motion.path
                                key={i}
                                d={d}
                                fill={fillColor}
                                stroke="#1e293b"
                                strokeWidth="0.5"
                                className="cursor-pointer transition-opacity"
                                initial={{ opacity: 0.8 }}
                                whileHover={{ opacity: 0.6, scale: 1.02 }}
                                transition={{ duration: 0.2 }}
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
            </SpotlightCard>

            {hoveredCity && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="fixed pointer-events-none z-50 px-4 py-2 bg-gradient-to-br from-slate-900 to-slate-800 text-white text-sm rounded-xl shadow-2xl border border-slate-600/50 backdrop-blur-sm"
                    style={{ left: mousePosition.x + 15, top: mousePosition.y + 15 }}
                >
                    <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-emerald-400" />
                        {hoveredCity}
                    </div>
                </motion.div>
            )}

            <GlassCard variant="default" className="p-4">
                <div className="flex justify-center gap-6 md:gap-8 text-sm text-gray-400 flex-wrap">
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#334155' }}></div>
                        <span>Veri Yok</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#6ee7b7' }}></div>
                        <span>1-49 İlan</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#10b981' }}></div>
                        <span>50-999 İlan</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#059669' }}></div>
                        <span>1000+ İlan</span>
                    </div>
                </div>
            </GlassCard>

            {selectedCityName && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                    onClick={() => setSelectedCityName(null)}
                >
                    <motion.div
                        initial={{ scale: 0.95, y: 20 }}
                        animate={{ scale: 1, y: 0 }}
                        exit={{ scale: 0.95, y: 20 }}
                        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                        className="max-w-2xl w-full max-h-[90vh] overflow-y-auto"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <SpotlightCard className="p-8">
                            {/* Header */}
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-4">
                                    <motion.div
                                        whileHover={{ scale: 1.1, rotate: 5 }}
                                        className="p-3 bg-gradient-to-br from-emerald-500/20 to-emerald-600/20 rounded-xl border border-emerald-500/30"
                                    >
                                        <Building2 className="w-7 h-7 text-emerald-400" />
                                    </motion.div>
                                    <div>
                                        <motion.h3
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: 0.1 }}
                                            className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400"
                                        >
                                            {selectedCityName}
                                        </motion.h3>
                                        <p className="text-sm text-gray-400 flex items-center gap-2">
                                            <Sparkles className="w-3.5 h-3.5 text-yellow-400" />
                                            Şehir Bazlı Toplu İstatistikler
                                        </p>
                                    </div>
                                </div>
                                <motion.button
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.9 }}
                                    onClick={() => setSelectedCityName(null)}
                                    className="p-2 hover:bg-slate-700/50 rounded-xl transition-colors"
                                >
                                    <X className="w-6 h-6 text-gray-400 hover:text-white" />
                                </motion.button>
                            </div>

                            {/* Stats Grid */}
                            <div className="grid grid-cols-2 gap-4 mb-6">
                                <GlassCard variant="default" neonBorder="emerald" glow className="p-5">
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="p-2 bg-emerald-500/20 rounded-lg">
                                            <Database className="w-5 h-5 text-emerald-400" />
                                        </div>
                                        <span className="text-gray-400 text-sm">Toplam İlan</span>
                                    </div>
                                    <motion.p
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.2 }}
                                        className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-green-400"
                                    >
                                        {cityStats?.total_listings ? cityStats.total_listings.toLocaleString() : '0'}
                                    </motion.p>
                                </GlassCard>

                                <GlassCard variant="default" neonBorder="blue" glow className="p-5">
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="p-2 bg-blue-500/20 rounded-lg">
                                            <TrendIcon className="w-5 h-5 text-blue-400" />
                                        </div>
                                        <span className="text-gray-400 text-sm">Ortalama Fiyat</span>
                                    </div>
                                    <motion.p
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.3 }}
                                        className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400"
                                    >
                                        {cityStats?.stats?.mean ? `${formatPrice(cityStats.stats.mean)} ₺` : 'Veri yok'}
                                    </motion.p>
                                </GlassCard>
                            </div>

                            {/* Descriptive Statistics */}
                            {statsLoading ? (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="flex flex-col items-center justify-center py-12"
                                >
                                    <div className="w-10 h-10 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4" />
                                    <span className="text-gray-400">İstatistikler yükleniyor...</span>
                                </motion.div>
                            ) : cityStats?.stats ? (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: 0.4 }}
                                >
                                    {/* Price Statistics */}
                                    <div className="mb-6">
                                        <div className="flex items-center gap-3 mb-4">
                                            <motion.div
                                                whileHover={{ scale: 1.1 }}
                                                className="p-2 bg-purple-500/20 rounded-lg"
                                            >
                                                <TrendingUp className="w-5 h-5 text-purple-400" />
                                            </motion.div>
                                            <h4 className="text-lg font-semibold text-white">Fiyat İstatistikleri</h4>
                                        </div>
                                        <div className="grid grid-cols-4 gap-3 text-sm">
                                            {[
                                                { label: 'Min', value: formatPrice(cityStats.stats.min), color: 'text-white' },
                                                { label: 'Q1', value: formatPrice(cityStats.stats.q25), color: 'text-white' },
                                                { label: 'Medyan', value: formatPrice(cityStats.stats.median), color: 'text-amber-400' },
                                                { label: 'Q3', value: formatPrice(cityStats.stats.q75), color: 'text-white' },
                                            ].map((stat, idx) => (
                                                <GlassCard key={idx} variant="dark" className="p-3 text-center">
                                                    <p className="text-gray-500 text-xs mb-1">{stat.label}</p>
                                                    <motion.p
                                                        initial={{ opacity: 0, scale: 0.9 }}
                                                        animate={{ opacity: 1, scale: 1 }}
                                                        transition={{ delay: 0.5 + idx * 0.05 }}
                                                        className={`${stat.color} font-semibold text-lg`}
                                                    >
                                                        {stat.value} ₺
                                                    </motion.p>
                                                </GlassCard>
                                            ))}
                                            <GlassCard variant="dark" className="p-3 text-center">
                                                <p className="text-gray-500 text-xs mb-1">Max</p>
                                                <p className="text-white font-semibold text-lg">{formatPrice(cityStats.stats.max)} ₺</p>
                                            </GlassCard>
                                            <GlassCard variant="dark" className="p-3 text-center">
                                                <p className="text-gray-500 text-xs mb-1">Ortalama</p>
                                                <p className="text-blue-400 font-semibold text-lg">{formatPrice(cityStats.stats.mean)} ₺</p>
                                            </GlassCard>
                                            <GlassCard variant="dark" className="p-3 text-center col-span-2">
                                                <p className="text-gray-500 text-xs mb-1">Std. Sapma</p>
                                                <p className="text-white font-semibold text-lg">{formatPrice(cityStats.stats.std)} ₺</p>
                                            </GlassCard>
                                        </div>
                                    </div>

                                    {/* Price Range Distribution */}
                                    <div>
                                        <div className="flex items-center gap-3 mb-4">
                                            <motion.div
                                                whileHover={{ scale: 1.1 }}
                                                className="p-2 bg-cyan-500/20 rounded-lg"
                                            >
                                                <BarChart3 className="w-5 h-5 text-cyan-400" />
                                            </motion.div>
                                            <h4 className="text-lg font-semibold text-white">Fiyat Aralığı Dağılımı</h4>
                                        </div>
                                        <div className="space-y-3">
                                            {cityStats.price_ranges.map((range, idx) => (
                                                <motion.div
                                                    key={idx}
                                                    initial={{ opacity: 0, x: -20 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    transition={{ delay: 0.6 + idx * 0.05 }}
                                                    className="flex items-center gap-3"
                                                >
                                                    <div className="w-36 text-xs text-gray-400 truncate font-medium" title={range.range}>
                                                        {range.range}
                                                    </div>
                                                    <div className="flex-1 h-7 bg-slate-800/80 rounded-full overflow-hidden">
                                                        <motion.div
                                                            initial={{ width: 0 }}
                                                            animate={{ width: `${range.percentage}%` }}
                                                            transition={{ duration: 0.8, delay: 0.7 + idx * 0.05 }}
                                                            className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 rounded-full"
                                                        />
                                                    </div>
                                                    <div className="w-24 text-right">
                                                        <span className="text-white font-bold text-sm">{range.count}</span>
                                                        <span className="text-gray-500 text-xs ml-1">(%{range.percentage})</span>
                                                    </div>
                                                </motion.div>
                                            ))}
                                        </div>
                                    </div>
                                </motion.div>
                            ) : null}
                        </SpotlightCard>
                    </motion.div>
                </motion.div>
            )}
        </div>
    );
}
