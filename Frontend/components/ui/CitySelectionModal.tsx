'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import TurkeyMap from 'turkey-map-react';
import { geoMercator, geoPath } from 'd3-geo';
import { X, MapPin, Check, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Feature, FeatureCollection, Geometry } from 'geojson';

// District index type
interface DistrictIndex {
    [province: string]: {
        file: string;
        count: number;
        districts: string[];
    };
}

interface DistrictProperties {
    feature_name: string;
    feature_id?: number;
    il_feature_name?: string;
    province?: string;
}

// Region definitions
const REGIONS: Record<string, string[]> = {
    'Marmara': ['İstanbul', 'Bursa', 'Kocaeli', 'Balıkesir', 'Tekirdağ', 'Sakarya', 'Edirne', 'Kırklareli', 'Çanakkale', 'Yalova', 'Bilecik'],
    'Ege': ['İzmir', 'Aydın', 'Denizli', 'Muğla', 'Manisa', 'Kütahya', 'Afyonkarahisar', 'Uşak'],
    'Akdeniz': ['Antalya', 'Adana', 'Mersin', 'Hatay', 'Kahramanmaraş', 'Osmaniye', 'Isparta', 'Burdur'],
    'İç Anadolu': ['Ankara', 'Konya', 'Kayseri', 'Eskişehir', 'Sivas', 'Yozgat', 'Aksaray', 'Niğde', 'Nevşehir', 'Kırşehir', 'Kırıkkale', 'Karaman', 'Çankırı'],
    'Karadeniz': ['Samsun', 'Trabzon', 'Ordu', 'Zonguldak', 'Tokat', 'Çorum', 'Amasya', 'Giresun', 'Rize', 'Artvin', 'Sinop', 'Kastamonu', 'Bartın', 'Karabük', 'Düzce', 'Bolu', 'Gümüşhane', 'Bayburt'],
    'Doğu Anadolu': ['Erzurum', 'Malatya', 'Elazığ', 'Van', 'Ağrı', 'Erzincan', 'Kars', 'Iğdır', 'Muş', 'Bitlis', 'Bingöl', 'Tunceli', 'Hakkari', 'Ardahan'],
    'Güneydoğu Anadolu': ['Gaziantep', 'Şanlıurfa', 'Diyarbakır', 'Mardin', 'Batman', 'Siirt', 'Şırnak', 'Adıyaman', 'Kilis'],
};

// City name mapping
const CITY_NAMES: Record<string, string> = {
    'Adana': 'Adana', 'Adiyaman': 'Adıyaman', 'Afyon': 'Afyonkarahisar', 'Agri': 'Ağrı',
    'Aksaray': 'Aksaray', 'Amasya': 'Amasya', 'Ankara': 'Ankara', 'Antalya': 'Antalya',
    'Artvin': 'Artvin', 'Aydin': 'Aydın', 'Balikesir': 'Balıkesir', 'Bartin': 'Bartın',
    'Batman': 'Batman', 'Bayburt': 'Bayburt', 'Bilecik': 'Bilecik', 'Bingol': 'Bingöl',
    'Bitlis': 'Bitlis', 'Bolu': 'Bolu', 'Burdur': 'Burdur', 'Bursa': 'Bursa',
    'Canakkale': 'Çanakkale', 'Cankiri': 'Çankırı', 'Corum': 'Çorum', 'Denizli': 'Denizli',
    'Diyarbakir': 'Diyarbakır', 'Duzce': 'Düzce', 'Edirne': 'Edirne', 'Elazig': 'Elazığ',
    'Erzincan': 'Erzincan', 'Erzurum': 'Erzurum', 'Eskisehir': 'Eskişehir', 'Gaziantep': 'Gaziantep',
    'Giresun': 'Giresun', 'Gumushane': 'Gümüşhane', 'Hakkari': 'Hakkari', 'Hakkâri': 'Hakkari', 'Hatay': 'Hatay',
    'Igdir': 'Iğdır', 'Isparta': 'Isparta', 'Istanbul': 'İstanbul', 'Izmir': 'İzmir',
    'Kahramanmaras': 'Kahramanmaraş', 'Karabuk': 'Karabük', 'Karaman': 'Karaman', 'Kars': 'Kars',
    'Kastamonu': 'Kastamonu', 'Kayseri': 'Kayseri', 'Kirikkale': 'Kırıkkale', 'Kirklareli': 'Kırklareli',
    'Kirsehir': 'Kırşehir', 'Kilis': 'Kilis', 'Kocaeli': 'Kocaeli', 'Konya': 'Konya',
    'Kutahya': 'Kütahya', 'Malatya': 'Malatya', 'Manisa': 'Manisa', 'Mardin': 'Mardin',
    'Mersin': 'Mersin', 'Mugla': 'Muğla', 'Mus': 'Muş', 'Nevsehir': 'Nevşehir',
    'Nigde': 'Niğde', 'Ordu': 'Ordu', 'Osmaniye': 'Osmaniye', 'Rize': 'Rize',
    'Sakarya': 'Sakarya', 'Samsun': 'Samsun', 'Siirt': 'Siirt', 'Sinop': 'Sinop',
    'Sivas': 'Sivas', 'Sanliurfa': 'Şanlıurfa', 'Sirnak': 'Şırnak', 'Tekirdag': 'Tekirdağ',
    'Tokat': 'Tokat', 'Trabzon': 'Trabzon', 'Tunceli': 'Tunceli', 'Usak': 'Uşak',
    'Van': 'Van', 'Yalova': 'Yalova', 'Yozgat': 'Yozgat', 'Zonguldak': 'Zonguldak',
    'Ardahan': 'Ardahan',
};

interface CitySelectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    selectedCities: string[];
    onCitiesChange: (cities: string[]) => void;
    selectedDistricts?: Record<string, string[]>;
    onDistrictsChange?: (districts: Record<string, string[]>) => void;
}

export function CitySelectionModal({
    isOpen,
    onClose,
    selectedCities,
    onCitiesChange,
    selectedDistricts = {},
    onDistrictsChange,
}: CitySelectionModalProps) {
    const [mounted, setMounted] = useState(false);
    const [districtIndex, setDistrictIndex] = useState<DistrictIndex | null>(null);
    const [activeProvince, setActiveProvince] = useState<string | null>(null);
    const [districtGeoData, setDistrictGeoData] = useState<FeatureCollection<Geometry, DistrictProperties> | null>(null);
    const [loadingDistricts, setLoadingDistricts] = useState(false);
    const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);
    const [hoveredCity, setHoveredCity] = useState<string | null>(null);
    const [mousePosition, setMousePosition] = useState<{ x: number; y: number } | null>(null);
    const [cityMousePosition, setCityMousePosition] = useState<{ x: number; y: number } | null>(null);
    const [zoomLevel, setZoomLevel] = useState(1);

    // Geçici seçimler - Modal içinde kullanılır, onaylanınca parent'a gönderilir
    const [tempSelectedCities, setTempSelectedCities] = useState<string[]>([]);
    const [tempSelectedDistricts, setTempSelectedDistricts] = useState<Record<string, string[]>>({});

    useEffect(() => {
        setMounted(true);
        return () => setMounted(false);
    }, []);

    // Modal açıldığında mevcut seçimleri kopyala
    useEffect(() => {
        if (isOpen) {
            setTempSelectedCities([...selectedCities]);
            setTempSelectedDistricts({ ...selectedDistricts });
            setActiveProvince(null);
        }
    }, [isOpen, selectedCities, selectedDistricts]);

    // Onaylama - Seçimleri parent'a gönder
    const handleConfirm = () => {
        onCitiesChange(tempSelectedCities);
        onDistrictsChange?.(tempSelectedDistricts);
        onClose();
    };

    // İptal - Geçici seçimleri at, modal'ı kapat
    const handleCancel = () => {
        setTempSelectedCities([...selectedCities]);
        setTempSelectedDistricts({ ...selectedDistricts });
        onClose();
    };

    // Load district index
    useEffect(() => {
        const loadDistrictIndex = async () => {
            try {
                const response = await fetch('/districts/index.json');
                if (response.ok) {
                    const data = await response.json();
                    setDistrictIndex(data);
                }
            } catch (err) {
                console.error('İlçe index yüklenemedi:', err);
            }
        };
        loadDistrictIndex();
    }, []);

    // Load district GeoJSON when province selected
    useEffect(() => {
        if (!activeProvince || !districtIndex) {
            setDistrictGeoData(null);
            return;
        }

        const loadDistrictGeoJSON = async () => {
            setLoadingDistricts(true);
            try {
                const fileName = districtIndex[activeProvince]?.file;
                if (fileName) {
                    const response = await fetch(`/districts/${fileName}`);
                    if (response.ok) {
                        const data = await response.json();
                        setDistrictGeoData(data);
                    }
                }
            } catch (err) {
                console.error('İlçe GeoJSON yüklenemedi:', err);
            } finally {
                setLoadingDistricts(false);
            }
        };

        loadDistrictGeoJSON();
    }, [activeProvince, districtIndex]);

    const handleCityClick = (cityData: { name: string }) => {
        const turkishName = CITY_NAMES[cityData.name] || cityData.name;

        if (districtIndex && districtIndex[turkishName]) {
            setActiveProvince(turkishName);
            setZoomLevel(1); // Reset zoom when entering district view
            if (!tempSelectedCities.includes(turkishName)) {
                setTempSelectedCities([...tempSelectedCities, turkishName]);
            }
        } else {
            if (tempSelectedCities.includes(turkishName)) {
                setTempSelectedCities(tempSelectedCities.filter(c => c !== turkishName));
                // İlgili ilçeleri de temizle
                if (tempSelectedDistricts[turkishName]) {
                    const { [turkishName]: _, ...restDistricts } = tempSelectedDistricts;
                    setTempSelectedDistricts(restDistricts);
                }
            } else {
                setTempSelectedCities([...tempSelectedCities, turkishName]);
            }
        }
    };

    const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 0.2, 3));
    const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 0.2, 0.5));
    const handleZoomReset = () => setZoomLevel(1);

    const handleRegionSelect = (region: string) => {
        const regionCities = REGIONS[region] || [];
        const allSelected = regionCities.every(city => tempSelectedCities.includes(city));
        if (allSelected) {
            setTempSelectedCities(tempSelectedCities.filter(city => !regionCities.includes(city)));
            // Kaldırılan şehirlerin ilçelerini de temizle
            const newDistricts = { ...tempSelectedDistricts };
            regionCities.forEach(city => delete newDistricts[city]);
            setTempSelectedDistricts(newDistricts);
        } else {
            setTempSelectedCities([...new Set([...tempSelectedCities, ...regionCities])]);
        }
    };

    const handleSelectAll = () => setTempSelectedCities(Object.values(CITY_NAMES));
    const handleClearAll = () => { setTempSelectedCities([]); setTempSelectedDistricts({}); };

    const handleDistrictToggle = (districtName: string) => {
        if (!activeProvince) return;
        const current = tempSelectedDistricts[activeProvince] || [];
        const newDistricts = current.includes(districtName)
            ? current.filter(d => d !== districtName)
            : [...current, districtName];
        setTempSelectedDistricts({ ...tempSelectedDistricts, [activeProvince]: newDistricts });

        // ŞEHRİ OTOMATİK SEÇ - İlçe seçildiğinde şehir de seçilsin
        if (newDistricts.length > 0 && !tempSelectedCities.includes(activeProvince)) {
            setTempSelectedCities([...tempSelectedCities, activeProvince]);
        }
    };

    const handleSelectAllDistricts = () => {
        if (!activeProvince || !districtIndex) return;
        setTempSelectedDistricts({ ...tempSelectedDistricts, [activeProvince]: districtIndex[activeProvince]?.districts || [] });
    };

    const handleDeselectAllDistricts = () => {
        if (!activeProvince) return;
        setTempSelectedDistricts({ ...tempSelectedDistricts, [activeProvince]: [] });
    };

    const isRegionFullySelected = (region: string) => (REGIONS[region] || []).every(city => tempSelectedCities.includes(city));
    const isRegionPartiallySelected = (region: string) => (REGIONS[region] || []).some(city => tempSelectedCities.includes(city)) && !isRegionFullySelected(region);

    const cityWrapper = (cityComponent: React.ReactElement, cityData: { name: string }) => {
        const turkishName = CITY_NAMES[cityData.name] || cityData.name;
        const isSelected = tempSelectedCities.includes(turkishName);
        const districtsSelected = (tempSelectedDistricts[turkishName] || []).length;
        if (isSelected) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const props = cityComponent.props as any;
            return React.cloneElement(cityComponent as React.ReactElement<any>, {
                style: { ...props.style, fill: districtsSelected > 0 ? 'rgba(16, 185, 129, 0.8)' : 'rgba(16, 185, 129, 0.6)', stroke: '#10b981', strokeWidth: '2px' }
            });
        }
        return cityComponent;
    };

    // District map projection
    const { pathGenerator, bounds } = useMemo(() => {
        if (!districtGeoData?.features.length) return { pathGenerator: null, bounds: null };
        const width = 491, height = 351, padding = 58;
        let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;

        districtGeoData.features.forEach(feature => {
            const processCoords = (coords: number[]) => {
                minLon = Math.min(minLon, coords[0]); maxLon = Math.max(maxLon, coords[0]);
                minLat = Math.min(minLat, coords[1]); maxLat = Math.max(maxLat, coords[1]);
            };
            if (feature.geometry.type === 'Polygon') feature.geometry.coordinates[0].forEach(processCoords);
            else if (feature.geometry.type === 'MultiPolygon') feature.geometry.coordinates.forEach(p => p[0].forEach(processCoords));
        });

        const scale = Math.min((width - padding * 2) / (maxLon - minLon), (height - padding * 2) / (maxLat - minLat)) * 58.5;
        const projection = geoMercator().center([(minLon + maxLon) / 2, (minLat + maxLat) / 2]).scale(scale).translate([width / 2, height / 2]);
        return { pathGenerator: geoPath().projection(projection), bounds: { width, height } };
    }, [districtGeoData]);

    const districtList = useMemo(() => {
        if (!districtGeoData) return [];
        return districtGeoData.features.map(f => f.properties.feature_name).filter((n): n is string => !!n).sort((a, b) => a.localeCompare(b, 'tr'));
    }, [districtGeoData]);

    const totalDistrictsSelected = Object.values(tempSelectedDistricts).reduce((sum, d) => sum + d.length, 0);
    const currentProvinceDistricts = activeProvince ? (tempSelectedDistricts[activeProvince] || []) : [];

    if (!mounted) return null;

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50" />
                    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
                        <div className="w-full max-w-6xl h-[90vh] bg-slate-900 border border-slate-700/50 rounded-2xl shadow-2xl flex flex-col overflow-hidden">

                            {/* Header - Sabit, değişmiyor */}
                            <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
                                <div className="flex items-center gap-3">
                                    <MapPin className="w-6 h-6 text-sky-400" />
                                    <h2 className="text-xl font-bold text-white">{activeProvince ? 'İlçe Seçimi' : 'Şehir Seçimi'}</h2>
                                    <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-sm font-medium">
                                        {tempSelectedCities.length} şehir{totalDistrictsSelected > 0 && `, ${totalDistrictsSelected} ilçe`}
                                    </span>
                                </div>
                                <button onClick={handleCancel} className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {/* Quick Select - Only show when not in district view */}
                            {!activeProvince && (
                                <div className="p-4 border-b border-slate-700/50">
                                    <div className="flex flex-wrap gap-2">
                                        <button onClick={handleSelectAll} className="px-4 py-2 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-500/30 hover:bg-sky-500/30 text-sm font-medium flex items-center gap-2">
                                            <Check className="w-4 h-4" /> Tümünü Seç
                                        </button>
                                        <button onClick={handleClearAll} className="px-4 py-2 rounded-lg bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30 text-sm font-medium flex items-center gap-2">
                                            <Trash2 className="w-4 h-4" /> Temizle
                                        </button>
                                        <div className="w-px bg-slate-700 mx-2" />
                                        {Object.keys(REGIONS).map(region => (
                                            <button key={region} onClick={() => handleRegionSelect(region)} className={cn(
                                                'px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
                                                isRegionFullySelected(region) ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                                    : isRegionPartiallySelected(region) ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                                                        : 'bg-slate-800 text-slate-300 border-slate-600 hover:bg-slate-700'
                                            )}>{region}</button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Map Container - Tek alan, içerik animasyonla değişiyor */}
                            <div className="flex-1 relative overflow-hidden">
                                <AnimatePresence mode="wait">
                                    {!activeProvince ? (
                                        // TÜRKIYE HARITASI
                                        <motion.div
                                            key="turkey"
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0, scale: 2 }}
                                            transition={{ duration: 0.4 }}
                                            className="absolute inset-0 flex items-center justify-center p-4"
                                            onMouseMove={(e) => {
                                                setCityMousePosition({ x: e.clientX, y: e.clientY });
                                            }}
                                            onMouseLeave={() => {
                                                setHoveredCity(null);
                                                setCityMousePosition(null);
                                            }}
                                        >
                                            <div className="w-full max-w-4xl">
                                                <TurkeyMap
                                                    hoverable
                                                    customStyle={{ idleColor: '#334155', hoverColor: '#0ea5e9' }}
                                                    onClick={handleCityClick}
                                                    showTooltip={false}
                                                    onHover={(cityData: { name: string }) => {
                                                        const turkishName = CITY_NAMES[cityData.name] || cityData.name;
                                                        setHoveredCity(turkishName);
                                                    }}
                                                    cityWrapper={cityWrapper}
                                                />
                                            </div>

                                            {/* City Tooltip */}
                                            {hoveredCity && cityMousePosition && (
                                                <div
                                                    className="fixed pointer-events-none z-50 px-2 py-1 rounded bg-slate-900/95 border border-sky-500/50 shadow-lg"
                                                    style={{
                                                        left: `${cityMousePosition.x + 10}px`,
                                                        top: `${cityMousePosition.y + 10}px`
                                                    }}
                                                >
                                                    <span className="text-xs text-sky-300 font-semibold whitespace-nowrap">
                                                        {hoveredCity}
                                                    </span>
                                                </div>
                                            )}
                                        </motion.div>
                                    ) : (
                                        // İLÇE HARITASI
                                        <motion.div
                                            key="district"
                                            initial={{ opacity: 0, scale: 0.5 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            exit={{ opacity: 0, scale: 0.5 }}
                                            transition={{ duration: 0.4 }}
                                            className="absolute inset-0 flex gap-4 p-4"
                                        >
                                            {/* Geri butonu ve il adı */}
                                            <motion.button
                                                initial={{ opacity: 0, x: -20 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                onClick={() => setActiveProvince(null)}
                                                className="absolute top-6 left-6 z-10 px-4 py-2 rounded-lg bg-slate-800/90 text-white flex items-center gap-2 hover:bg-slate-700 transition-colors border border-slate-600"
                                            >
                                                ← Türkiye&apos;ye Dön
                                            </motion.button>

                                            <motion.div
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                                className="absolute bottom-6 left-6 z-10 px-4 py-2 rounded-lg bg-sky-500/20 text-sky-300 font-semibold border border-sky-500/30"
                                            >
                                                {activeProvince}
                                            </motion.div>

                                            {/* Harita */}
                                            <div className="flex-1 flex items-center justify-center">
                                                {loadingDistricts ? (
                                                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-sky-500" />
                                                ) : districtGeoData && pathGenerator && bounds ? (
                                                    <div className="relative w-full h-full flex items-center justify-center">
                                                        <svg
                                                            viewBox={`0 0 ${bounds.width} ${bounds.height}`}
                                                            className="w-full h-full max-h-[60vh]"
                                                            preserveAspectRatio="xMidYMid meet"
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
                                                                {districtGeoData.features.map((feature, idx) => {
                                                                    const name = feature.properties.feature_name || `d-${idx}`;
                                                                    const isSelected = currentProvinceDistricts.includes(name);
                                                                    const isHovered = hoveredDistrict === name;
                                                                    return (
                                                                        <motion.path
                                                                            key={name}
                                                                            d={pathGenerator(feature as Feature<Geometry>) || ''}
                                                                            initial={{ opacity: 0 }}
                                                                            animate={{ opacity: 1, fill: isSelected ? 'rgba(16, 185, 129, 0.6)' : isHovered ? 'rgba(14, 165, 233, 0.4)' : 'rgba(51, 65, 85, 0.8)' }}
                                                                            transition={{ delay: idx * 0.015 }}
                                                                            stroke={isSelected ? '#10b981' : isHovered ? '#0ea5e9' : '#475569'}
                                                                            strokeWidth={isSelected || isHovered ? 2 / zoomLevel : 1 / zoomLevel}
                                                                            className="cursor-pointer"
                                                                            onClick={() => handleDistrictToggle(name)}
                                                                            onMouseEnter={() => setHoveredDistrict(name)}
                                                                            onMouseLeave={() => setHoveredDistrict(null)}
                                                                        />
                                                                    );
                                                                })}
                                                            </g>
                                                        </svg>

                                                        {/* Tooltip - İmleç bitişik */}
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

                                                        {/* Zoom Controls */}
                                                        <div className="absolute top-4 right-4 flex flex-row gap-2 bg-slate-800/90 rounded-lg p-2 border border-slate-600">
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
                                                    </div>
                                                ) : null}
                                            </div>

                                            {/* İlçe Listesi */}
                                            <motion.div initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="w-72 bg-slate-800/50 rounded-lg p-4 flex flex-col">
                                                <div className="flex items-center justify-between mb-3">
                                                    <h3 className="text-sm font-semibold text-slate-300">İlçeler ({districtList.length})</h3>
                                                    <div className="flex gap-2">
                                                        <button onClick={handleSelectAllDistricts} className="text-xs px-2 py-1 rounded bg-sky-500/20 text-sky-300 hover:bg-sky-500/30">Tümü</button>
                                                        <button onClick={handleDeselectAllDistricts} className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-300 hover:bg-red-500/30">Temizle</button>
                                                    </div>
                                                </div>
                                                <div className="flex-1 overflow-y-auto space-y-1">
                                                    {districtList.map(district => (
                                                        <label key={district} className={cn("flex items-center gap-2 p-2 rounded cursor-pointer transition-colors", currentProvinceDistricts.includes(district) ? 'bg-emerald-500/20 text-emerald-300' : 'hover:bg-slate-700/50 text-slate-300')}>
                                                            <input type="checkbox" checked={currentProvinceDistricts.includes(district)} onChange={() => handleDistrictToggle(district)} className="rounded border-slate-600 bg-slate-700 text-emerald-500" />
                                                            <span className="text-sm truncate">{district}</span>
                                                        </label>
                                                    ))}
                                                </div>
                                                {currentProvinceDistricts.length > 0 && <div className="mt-3 pt-3 border-t border-slate-700 text-sm text-emerald-400">{currentProvinceDistricts.length} ilçe seçili</div>}
                                            </motion.div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>

                                {/* Hover tooltip */}
                                {hoveredDistrict && activeProvince && (
                                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg bg-slate-800/90 text-white text-sm border border-slate-600">
                                        {hoveredDistrict}
                                    </motion.div>
                                )}
                            </div>

                            {/* Footer */}
                            <div className="p-4 border-t border-slate-700/50 flex justify-end gap-3">
                                <button onClick={handleCancel} className="px-6 py-2 rounded-lg bg-slate-800 text-slate-300 border border-slate-600 hover:bg-slate-700 font-medium">İptal</button>
                                <button onClick={handleConfirm} className="px-6 py-2 rounded-lg bg-sky-500 text-white hover:bg-sky-600 font-medium">Seçimi Onayla</button>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>,
        document.body
    );
}
