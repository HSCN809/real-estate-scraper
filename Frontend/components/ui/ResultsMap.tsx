'use client';

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { Download, Eye, X, Building2 } from 'lucide-react';
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
    if (price >= 1000000) return `${(price / 1000000).toFixed(1)}M`;
    if (price >= 1000) return `${(price / 1000).toFixed(0)}K`;
    return price.toString();
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

interface ResultsMapProps {
    results: ScrapeResult[];
    onPreview: (filename: string) => void;
}

export function ResultsMap({ results, onPreview }: ResultsMapProps) {
    const [selectedCity, setSelectedCity] = useState<ScrapeResult | null>(null);
    const [hoveredCity, setHoveredCity] = useState<string | null>(null);
    const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
    const [geoData, setGeoData] = useState<GeoFeature[]>([]);

    // GeoJSON yükle
    useEffect(() => {
        fetch(GEOJSON_URL)
            .then(res => res.json())
            .then(data => setGeoData(data.features || []))
            .catch(err => console.error('GeoJSON yüklenemedi:', err));
    }, []);

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
        if (result) setSelectedCity(result);
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
                        // GeoJSON adını veri kaynağı adına çevir (mapping varsa)
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

            {selectedCity && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setSelectedCity(null)}>
                    <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full shadow-2xl" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-emerald-500/20 rounded-lg"><Building2 className="w-6 h-6 text-emerald-400" /></div>
                                <div>
                                    <h3 className="text-xl font-bold text-white">{selectedCity.city}</h3>
                                    <p className="text-sm text-gray-400">{selectedCity.platform} • {selectedCity.category}</p>
                                </div>
                            </div>
                            <button onClick={() => setSelectedCity(null)} className="p-2 hover:bg-slate-800 rounded-lg"><X className="w-5 h-5 text-gray-400" /></button>
                        </div>
                        <div className="grid grid-cols-2 gap-4 mb-6">
                            <div className="bg-slate-800/50 rounded-xl p-4">
                                <p className="text-gray-400 text-sm mb-1">Toplam İlan</p>
                                <p className="text-2xl font-bold text-emerald-400">{(selectedCity.count || 0).toLocaleString()}</p>
                            </div>
                            {selectedCity.avg_price && (
                                <div className="bg-slate-800/50 rounded-xl p-4">
                                    <p className="text-gray-400 text-sm mb-1">Ortalama Fiyat</p>
                                    <p className="text-2xl font-bold text-blue-400">{formatPrice(selectedCity.avg_price)} ₺</p>
                                </div>
                            )}
                        </div>
                        {selectedCity.files?.length > 0 && (
                            <div className="flex gap-3">
                                <button onClick={() => onPreview(selectedCity.files[0].name)} className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-slate-800 hover:bg-slate-700 rounded-xl text-gray-300">
                                    <Eye className="w-4 h-4" /> Önizle
                                </button>
                                <a href={`http://localhost:8000/api/v1/download/${selectedCity.files[0].name}`} className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-emerald-600 hover:bg-emerald-700 rounded-xl text-white">
                                    <Download className="w-4 h-4" /> İndir
                                </a>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
