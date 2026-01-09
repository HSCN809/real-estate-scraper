'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { geoMercator, geoPath } from 'd3-geo';
import type { Feature, FeatureCollection, Geometry } from 'geojson';

interface DistrictProperties {
    feature_name: string;
    feature_id?: number;
    il_feature_name?: string;
    il_feature_id?: number;
    province?: string;
}

interface DistrictMapProps {
    provinceName: string;
    provinceFileName: string;
    selectedDistricts: string[];
    onDistrictToggle: (districtName: string) => void;
    onSelectAll: () => void;
    onDeselectAll: () => void;
}

export function DistrictMap({
    provinceName,
    provinceFileName,
    selectedDistricts,
    onDistrictToggle,
    onSelectAll,
    onDeselectAll
}: DistrictMapProps) {
    const [geoData, setGeoData] = useState<FeatureCollection<Geometry, DistrictProperties> | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);
    const [mousePosition, setMousePosition] = useState<{ x: number; y: number } | null>(null);
    const [zoomLevel, setZoomLevel] = useState(1);

    const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 0.2, 3));
    const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 0.2, 0.5));
    const handleZoomReset = () => setZoomLevel(1);

    // GeoJSON dosyasını yükle
    useEffect(() => {
        const loadGeoJSON = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await fetch(`/districts/${provinceFileName}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setGeoData(data);
            } catch (err) {
                setError(`${provinceName} haritası yüklenemedi`);
                console.error('GeoJSON yükleme hatası:', err);
            } finally {
                setLoading(false);
            }
        };

        loadGeoJSON();
    }, [provinceFileName, provinceName]);

    // Projeksiyon ve path generator hesapla
    const { pathGenerator, bounds } = useMemo(() => {
        if (!geoData || !geoData.features.length) {
            return { pathGenerator: null, bounds: null };
        }

        const width = 351;
        const height = 281;
        const padding = 37;

        // Tüm features için boundary hesapla
        let minLon = Infinity, maxLon = -Infinity;
        let minLat = Infinity, maxLat = -Infinity;

        geoData.features.forEach(feature => {
            if (feature.geometry.type === 'Polygon') {
                feature.geometry.coordinates[0].forEach(coord => {
                    minLon = Math.min(minLon, coord[0]);
                    maxLon = Math.max(maxLon, coord[0]);
                    minLat = Math.min(minLat, coord[1]);
                    maxLat = Math.max(maxLat, coord[1]);
                });
            } else if (feature.geometry.type === 'MultiPolygon') {
                feature.geometry.coordinates.forEach(polygon => {
                    polygon[0].forEach(coord => {
                        minLon = Math.min(minLon, coord[0]);
                        maxLon = Math.max(maxLon, coord[0]);
                        minLat = Math.min(minLat, coord[1]);
                        maxLat = Math.max(maxLat, coord[1]);
                    });
                });
            }
        });

        const centerLon = (minLon + maxLon) / 2;
        const centerLat = (minLat + maxLat) / 2;

        // Scale hesapla
        const lonRange = maxLon - minLon;
        const latRange = maxLat - minLat;
        const scale = Math.min(
            (width - padding * 2) / lonRange,
            (height - padding * 2) / latRange
        ) * 70.2;

        const projection = geoMercator()
            .center([centerLon, centerLat])
            .scale(scale)
            .translate([width / 2, height / 2]);

        const generator = geoPath().projection(projection);

        return {
            pathGenerator: generator,
            bounds: { width, height }
        };
    }, [geoData]);

    // İlçe listesi
    const districtList = useMemo(() => {
        if (!geoData) return [];
        return geoData.features
            .map(f => f.properties.feature_name)
            .filter((name): name is string => !!name)
            .sort((a, b) => a.localeCompare(b, 'tr'));
    }, [geoData]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-sky-500"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center text-red-400 p-8">
                <p>{error}</p>
            </div>
        );
    }

    if (!geoData || !pathGenerator || !bounds) {
        return (
            <div className="text-center text-slate-400 p-8">
                <p>Harita verisi bulunamadı</p>
            </div>
        );
    }

    const allSelected = districtList.length > 0 && districtList.every(d => selectedDistricts.includes(d));
    const someSelected = selectedDistricts.length > 0 && !allSelected;

    return (
        <div className="flex flex-col lg:flex-row gap-4">
            {/* Harita */}
            <div className="flex-1 bg-slate-800/50 rounded-lg p-4 relative">
                <svg
                    viewBox={`0 0 ${bounds.width} ${bounds.height}`}
                    className="w-full h-auto max-h-[400px]"
                    onMouseMove={(e) => {
                        const rect = e.currentTarget.getBoundingClientRect();
                        setMousePosition({
                            x: e.clientX - rect.left,
                            y: e.clientY - rect.top
                        });
                    }}
                    onMouseLeave={() => {
                        setHoveredDistrict(null);
                        setMousePosition(null);
                    }}
                >
                    <g transform={`scale(${zoomLevel})`} style={{ transformOrigin: 'center' }}>
                        {geoData.features.map((feature, index) => {
                            const districtName = feature.properties.feature_name || `district-${index}`;
                            const isSelected = selectedDistricts.includes(districtName);
                            const isHovered = hoveredDistrict === districtName;
                            const pathD = pathGenerator(feature as Feature<Geometry>);

                            return (
                                <path
                                    key={`${districtName}-${index}`}
                                    d={pathD || ''}
                                    fill={isSelected ? 'rgba(16, 185, 129, 0.6)' : isHovered ? 'rgba(14, 165, 233, 0.4)' : 'rgba(51, 65, 85, 0.8)'}
                                    stroke={isSelected ? '#10b981' : isHovered ? '#0ea5e9' : '#475569'}
                                    strokeWidth={isSelected || isHovered ? 2 / zoomLevel : 1 / zoomLevel}
                                    className="cursor-pointer transition-all duration-150"
                                    onClick={() => onDistrictToggle(districtName)}
                                    onMouseEnter={() => setHoveredDistrict(districtName)}
                                    onMouseLeave={() => setHoveredDistrict(null)}
                                />
                            );
                        })}
                    </g>
                </svg>

                {/* Zoom Controls */}
                <div className="absolute top-6 right-6 flex flex-row gap-2 bg-slate-800/90 rounded-lg p-2 border border-slate-600">
                    <button
                        onClick={handleZoomOut}
                        disabled={zoomLevel <= 0.5}
                        className="w-8 h-8 flex items-center justify-center rounded hover:bg-slate-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        title="Uzaklaştır"
                    >
                        −
                    </button>
                    <button
                        onClick={handleZoomReset}
                        className="w-8 h-8 flex items-center justify-center rounded hover:bg-slate-700 text-white text-xs transition-colors"
                        title="Sıfırla"
                    >
                        1:1
                    </button>
                    <button
                        onClick={handleZoomIn}
                        disabled={zoomLevel >= 3}
                        className="w-8 h-8 flex items-center justify-center rounded hover:bg-slate-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        title="Yakınlaştır"
                    >
                        +
                    </button>
                </div>

                {hoveredDistrict && mousePosition && (
                    <div
                        className="absolute pointer-events-none z-50 px-2 py-1 rounded bg-slate-900/95 border border-sky-500/50 shadow-lg"
                        style={{
                            left: `${mousePosition.x + 10}px`,
                            top: `${mousePosition.y + 10}px`
                        }}
                    >
                        <span className="text-xs text-sky-300 font-semibold whitespace-nowrap">
                            {hoveredDistrict}
                        </span>
                    </div>
                )}
            </div>

            {/* İlçe Listesi */}
            <div className="w-full lg:w-64 bg-slate-800/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-slate-300">
                        İlçeler ({districtList.length})
                    </h3>
                    <div className="flex gap-2">
                        <button
                            onClick={onSelectAll}
                            className="text-xs px-2 py-1 rounded bg-sky-500/20 text-sky-300 hover:bg-sky-500/30 transition-colors"
                        >
                            Tümü
                        </button>
                        <button
                            onClick={onDeselectAll}
                            className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-300 hover:bg-red-500/30 transition-colors"
                        >
                            Temizle
                        </button>
                    </div>
                </div>
                <div className="max-h-64 overflow-y-auto space-y-1">
                    {districtList.map(district => (
                        <label
                            key={district}
                            className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${selectedDistricts.includes(district)
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : 'hover:bg-slate-700/50 text-slate-300'
                                }`}
                        >
                            <input
                                type="checkbox"
                                checked={selectedDistricts.includes(district)}
                                onChange={() => onDistrictToggle(district)}
                                className="rounded border-slate-600 bg-slate-700 text-emerald-500 focus:ring-emerald-500"
                            />
                            <span className="text-sm truncate">{district}</span>
                        </label>
                    ))}
                </div>

                {/* Seçili ilçe sayısı */}
                {selectedDistricts.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-700">
                        <p className="text-sm text-emerald-400">
                            {selectedDistricts.length} ilçe seçili
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
