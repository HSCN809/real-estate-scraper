'use client';

import { ArtCard } from '@/components/ui/ArtCard';
import { ResultsMap } from '@/components/ui/ResultsMap';
import { ResultsCharts } from '@/components/ui/ResultsCharts';
import { motion, AnimatePresence } from 'framer-motion';
import {
    FileText,
    Download,
    Sparkles,
    FileSpreadsheet,
    FileJson,
    Clock,
    RefreshCw,
    Database,
    Search,
    Trash2,
    AlertTriangle,
    MapPin,
    Building2,
    Eye,
    X,
    List,
    Filter,
    Home,
    TrendingUp,
    Calendar,
    Map,
    BarChart3
} from 'lucide-react';
import { useEffect, useState, useRef } from 'react';
import { getResults } from '@/lib/api';
import { ScrapeResult } from '@/types';


// Animation variants
const containerVariants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.08 },
    },
};

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
};

// Extended type for our rich data
interface RichResult extends ScrapeResult {
    city?: string;
    listing_type?: string;
    file_size_mb?: number;
}

export default function ResultsPage() {
    const [results, setResults] = useState<RichResult[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<'table' | 'map' | 'charts'>('map');
    const [clearing, setClearing] = useState(false);
    const [showClearConfirm, setShowClearConfirm] = useState(false);

    // Filters
    const [platformFilter, setPlatformFilter] = useState<string>('all');
    const [categoryFilter, setCategoryFilter] = useState<string>('all');
    const [listingTypeFilter, setListingTypeFilter] = useState<string>('all');
    const [subtypeFilter, setSubtypeFilter] = useState<string>('all');

    // City/District filters for table view
    const [cityFilter, setCityFilter] = useState<string[]>([]);
    const [districtFilter, setDistrictFilter] = useState<string[]>([]);
    const [cityDropdownOpen, setCityDropdownOpen] = useState(false);
    const [districtDropdownOpen, setDistrictDropdownOpen] = useState(false);

    // Refs for click outside detection
    const cityDropdownRef = useRef<HTMLDivElement>(null);
    const districtDropdownRef = useRef<HTMLDivElement>(null);

    // Preview Modal
    const [previewData, setPreviewData] = useState<any>(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [previewFile, setPreviewFile] = useState<string | null>(null);

    // Price data for charts - with filter tracking to prevent stale data rendering
    const [priceData, setPriceData] = useState<{
        prices: any[];
        filters: { platform: string; category: string; listingType: string };
    }>({ prices: [], filters: { platform: 'all', category: 'all', listingType: 'all' } });
    const [priceDataLoading, setPriceDataLoading] = useState(false);

    // Check if current priceData matches current filters
    const isPriceDataValid =
        priceData.filters.platform === platformFilter &&
        priceData.filters.category === categoryFilter &&
        priceData.filters.listingType === listingTypeFilter;

    // Fetch price data with filters
    const fetchPriceData = async () => {
        const currentFilters = {
            platform: platformFilter,
            category: categoryFilter,
            listingType: listingTypeFilter
        };

        setPriceDataLoading(true);
        try {
            const params = new URLSearchParams();
            if (platformFilter !== 'all') params.append('platform', platformFilter);
            if (categoryFilter !== 'all') params.append('category', categoryFilter);
            if (listingTypeFilter !== 'all') params.append('listing_type', listingTypeFilter);

            const url = `http://localhost:8000/api/v1/analytics/prices${params.toString() ? '?' + params.toString() : ''}`;
            const res = await fetch(url);
            const data = await res.json();

            // Store prices with the filters they were fetched for
            setPriceData({
                prices: data.prices || [],
                filters: currentFilters
            });
        } catch (err) {
            console.error('Price data fetch failed:', err);
            setPriceData({ prices: [], filters: currentFilters });
        } finally {
            setPriceDataLoading(false);
        }
    };

    // Auto-refetch price data when filters change and in charts view
    useEffect(() => {
        if (viewMode === 'charts') {
            setPriceDataLoading(true); // Show loading spinner immediately
            fetchPriceData();
        }
    }, [platformFilter, categoryFilter, listingTypeFilter, viewMode]);

    const fetchResults = async () => {
        try {
            setLoading(true);
            const data = await getResults();
            setResults(Array.isArray(data) ? data : []);
            setError(null);
        } catch (err) {
            setError('Veriler alınırken bir hata oluştu');
        } finally {
            setLoading(false);
        }
    };

    const clearResults = async () => {
        try {
            setClearing(true);
            const res = await fetch('http://localhost:8000/api/v1/clear-results', { method: 'DELETE' });
            if (res.ok) {
                setResults([]);
                setShowClearConfirm(false);
            }
        } catch (err) {
            console.error('Clear failed:', err);
        } finally {
            setClearing(false);
        }
    };

    const deleteResult = async (filename: string) => {
        if (!confirm(`"${filename}" dosyasını silmek istediğinize emin misiniz?`)) return;

        try {
            const res = await fetch(`http://localhost:8000/api/v1/results/${encodeURIComponent(filename)}`, { method: 'DELETE' });
            if (res.ok) {
                setResults(results.filter(r => r.files?.[0]?.name !== filename));
            }
        } catch (err) {
            console.error('Delete failed:', err);
        }
    };

    const openPreview = async (filename: string) => {
        setPreviewFile(filename);
        setPreviewLoading(true);
        try {
            const res = await fetch(`http://localhost:8000/api/v1/results/${filename}/preview?limit=20`);
            const data = await res.json();
            setPreviewData(data);
        } catch (err) {
            console.error('Preview failed:', err);
        } finally {
            setPreviewLoading(false);
        }
    };

    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        fetchResults();
    }, []);

    // Click outside to close dropdowns
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (cityDropdownRef.current && !cityDropdownRef.current.contains(event.target as Node)) {
                setCityDropdownOpen(false);
            }
            if (districtDropdownRef.current && !districtDropdownRef.current.contains(event.target as Node)) {
                setDistrictDropdownOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    if (!mounted) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <div className="w-10 h-10 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
            </div>
        );
    }

    // Filtered results
    const filteredResults = results.filter(r => {
        if (platformFilter !== 'all' && r.platform !== platformFilter) return false;
        if (categoryFilter !== 'all' && r.category !== categoryFilter) return false;
        if (listingTypeFilter !== 'all' && r.listing_type !== listingTypeFilter) return false;
        if (subtypeFilter !== 'all' && r.subtype !== subtypeFilter) return false;
        // City/District filters (for table view)
        if (cityFilter.length > 0 && !cityFilter.includes(r.city || '')) return false;
        if (districtFilter.length > 0 && !districtFilter.includes(r.district || '')) return false;
        return true;
    });

    // Stats
    const totalFiles = results.length;
    const totalRecords = results.reduce((acc, curr) => acc + (curr.count || 0), 0);
    const uniqueCities = [...new Set(results.map(r => r.city).filter(Boolean))].length;
    const latestDate = results.length > 0 ? results[0].date : '-';

    // Unique platforms, categories, listing types and subtypes for filters
    const platforms = [...new Set(results.map(r => r.platform))];
    const categories = [...new Set(results.map(r => r.category))];
    const listingTypes = [...new Set(results.map(r => r.listing_type).filter(Boolean))];
    const subtypes = [...new Set(results.map(r => r.subtype).filter(Boolean))];

    // Cities and districts for table view filters
    const cities = [...new Set(results.map(r => r.city).filter(Boolean))].sort() as string[];
    const availableDistricts = results
        .filter(r => cityFilter.length === 0 || cityFilter.includes(r.city || ''))
        .map(r => r.district)
        .filter(Boolean);
    const districts = [...new Set(availableDistricts)].sort() as string[];

    // City filter change handler - clear district filter when city changes
    const handleCityFilterChange = (city: string) => {
        setCityFilter(prev => {
            if (prev.includes(city)) {
                return prev.filter(c => c !== city);
            } else {
                return [...prev, city];
            }
        });
        setDistrictFilter([]); // Clear district filter when city changes
    };

    const handleDistrictFilterChange = (district: string) => {
        setDistrictFilter(prev => {
            if (prev.includes(district)) {
                return prev.filter(d => d !== district);
            } else {
                return [...prev, district];
            }
        });
    };

    const toggleAllCities = () => {
        if (cityFilter.length === cities.length) {
            setCityFilter([]);
        } else {
            setCityFilter([...cities]);
        }
        setDistrictFilter([]);
    };

    const toggleAllDistricts = () => {
        if (districtFilter.length === districts.length) {
            setDistrictFilter([]);
        } else {
            setDistrictFilter([...districts]);
        }
    };

    return (
        <motion.div
            className="space-y-8 relative z-10 p-4 md:p-8 max-w-7xl mx-auto"
            variants={containerVariants}
            initial="hidden"
            animate="show"
        >
            {/* Header */}
            <motion.div variants={itemVariants} className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <h1 className="text-4xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-emerald-400 mb-2">
                        Veri Sonuçları
                    </h1>
                    <p className="text-gray-400 text-lg flex items-center gap-2">
                        Taranan emlak verileri ve raporlar
                        <Sparkles className="w-4 h-4 text-yellow-400" />
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    {/* View Toggle */}
                    <div className="flex rounded-xl overflow-hidden border border-slate-700">
                        <button
                            onClick={() => setViewMode('map')}
                            className={`p-2.5 transition-colors ${viewMode === 'map' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-gray-400 hover:text-white'}`}
                            title="Harita"
                        >
                            <Map className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => setViewMode('table')}
                            className={`p-2.5 transition-colors ${viewMode === 'table' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-gray-400 hover:text-white'}`}
                            title="Tablo"
                        >
                            <List className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => {
                                setPriceDataLoading(true); // Show loading immediately
                                setViewMode('charts');
                            }}
                            className={`p-2.5 transition-colors ${viewMode === 'charts' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-gray-400 hover:text-white'}`}
                            title="Grafikler"
                        >
                            <BarChart3 className="w-4 h-4" />
                        </button>
                    </div>

                    {results.length > 0 && (
                        <button
                            onClick={() => setShowClearConfirm(true)}
                            className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 hover:bg-red-500/20 transition-all"
                            title="Sonuçları Temizle"
                        >
                            <Trash2 className="w-5 h-5 text-red-400" />
                        </button>
                    )}

                    <button
                        onClick={fetchResults}
                        disabled={loading}
                        className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:bg-slate-700/50 transition-all"
                        title="Yenile"
                    >
                        <RefreshCw className={`w-5 h-5 text-gray-300 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </motion.div>

            {/* Dashboard Stats */}
            <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/30 rounded-2xl p-5">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-blue-500/20 rounded-lg">
                            <Database className="w-5 h-5 text-blue-400" />
                        </div>
                        <span className="text-gray-400 text-sm">Toplam İlan</span>
                    </div>
                    <p className="text-3xl font-bold text-white">{totalRecords.toLocaleString()}</p>
                </div>

                <div className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border border-emerald-500/30 rounded-2xl p-5">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-emerald-500/20 rounded-lg">
                            <MapPin className="w-5 h-5 text-emerald-400" />
                        </div>
                        <span className="text-gray-400 text-sm">Şehir</span>
                    </div>
                    <p className="text-3xl font-bold text-white">{uniqueCities}</p>
                </div>

                <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border border-purple-500/30 rounded-2xl p-5">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-purple-500/20 rounded-lg">
                            <FileText className="w-5 h-5 text-purple-400" />
                        </div>
                        <span className="text-gray-400 text-sm">Dosya</span>
                    </div>
                    <p className="text-3xl font-bold text-white">{totalFiles}</p>
                </div>

                <div className="bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/30 rounded-2xl p-5">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-amber-500/20 rounded-lg">
                            <Calendar className="w-5 h-5 text-amber-400" />
                        </div>
                        <span className="text-gray-400 text-sm">Son Tarama</span>
                    </div>
                    <p className="text-lg font-bold text-white truncate">{latestDate}</p>
                </div>
            </motion.div>

            {/* Filters */}
            <motion.div variants={itemVariants} className="flex flex-wrap gap-3">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Filter className="w-4 h-4" />
                    Filtre:
                </div>

                {/* Platform Filter */}
                <div className="flex rounded-lg overflow-hidden border border-slate-700">
                    <button
                        onClick={() => setPlatformFilter('all')}
                        className={`px-3 py-1.5 text-sm transition-colors ${platformFilter === 'all' ? 'bg-slate-700 text-white' : 'bg-slate-800/50 text-gray-400'}`}
                    >
                        Tümü
                    </button>
                    {platforms.map(p => (
                        <button
                            key={p}
                            onClick={() => setPlatformFilter(p)}
                            className={`px-3 py-1.5 text-sm transition-colors ${platformFilter === p ? 'bg-slate-700 text-white' : 'bg-slate-800/50 text-gray-400'}`}
                        >
                            {p}
                        </button>
                    ))}
                </div>

                {/* Category Filter */}
                <div className="flex rounded-lg overflow-hidden border border-slate-700">
                    {categories.map(c => (
                        <button
                            key={c}
                            onClick={() => setCategoryFilter(categoryFilter === c ? 'all' : c)}
                            className={`px-3 py-1.5 text-sm transition-colors ${categoryFilter === c ? 'bg-emerald-600 text-white' : 'bg-slate-800/50 text-gray-400'}`}
                        >
                            {c}
                        </button>
                    ))}
                </div>

                {/* Listing Type Filter (Satılık/Kiralık) */}
                <div className="flex rounded-lg overflow-hidden border border-slate-700">
                    {listingTypes.map(lt => (
                        <button
                            key={lt}
                            onClick={() => setListingTypeFilter(listingTypeFilter === lt ? 'all' : (lt || 'all'))}
                            className={`px-3 py-1.5 text-sm transition-colors ${listingTypeFilter === lt ? 'bg-amber-600 text-white' : 'bg-slate-800/50 text-gray-400'}`}
                        >
                            {lt}
                        </button>
                    ))}
                </div>

                {/* Subtype Filter (Alt Kategori) - Custom Dropdown */}
                {subtypes.length > 0 && (
                    <div className="relative">
                        <select
                            value={subtypeFilter}
                            onChange={(e) => setSubtypeFilter(e.target.value)}
                            className="px-3 py-1.5 text-sm rounded-lg border border-slate-700 bg-slate-800/50 text-gray-300 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent appearance-none pr-8 cursor-pointer"
                        >
                            <option value="all">Alt Kategori: Tümü</option>
                            {subtypes.map(st => (
                                <option key={st} value={st}>{st}</option>
                            ))}
                        </select>
                        <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
                            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </div>
                    </div>
                )}
            </motion.div>

            {/* Content */}
            <motion.div className="min-h-[400px]" variants={containerVariants} initial="show" animate="show">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                        <p className="text-gray-400 animate-pulse">Veriler yükleniyor...</p>
                    </div>
                ) : error ? (
                    <ArtCard glowColor="pink" className="text-center py-16 max-w-lg mx-auto">
                        <div className="flex flex-col items-center gap-6">
                            <div className="w-20 h-20 rounded-full bg-red-500/10 flex items-center justify-center">
                                <FileText className="w-10 h-10 text-red-500" />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-white mb-2">Veri Alınamadı</h3>
                                <p className="text-gray-400">{error}</p>
                            </div>
                            <button onClick={fetchResults} className="px-8 py-3 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
                                Tekrar Dene
                            </button>
                        </div>
                    </ArtCard>
                ) : filteredResults.length === 0 ? (
                    <motion.div variants={itemVariants}>
                        <ArtCard glowColor="blue" className="text-center py-20">
                            <div className="flex flex-col items-center gap-6 max-w-md mx-auto">
                                <div className="w-24 h-24 rounded-full bg-slate-800/50 flex items-center justify-center">
                                    <Search className="w-12 h-12 text-gray-600" />
                                </div>
                                <div>
                                    <h3 className="text-2xl font-bold text-white mb-3">Henüz Sonuç Yok</h3>
                                    <p className="text-gray-400">Yeni bir tarama başlatarak emlak verilerini toplamaya başlayın.</p>
                                </div>
                            </div>
                        </ArtCard>
                    </motion.div>
                ) : viewMode === 'map' ? (
                    /* Map View */
                    <motion.div variants={itemVariants}>
                        <ResultsMap results={filteredResults} onPreview={openPreview} />
                    </motion.div>
                ) : viewMode === 'charts' ? (
                    /* Charts View */
                    <motion.div variants={itemVariants}>
                        {(priceDataLoading || !isPriceDataValid) ? (
                            <div className="flex flex-col items-center justify-center py-20 gap-4">
                                <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                                <p className="text-gray-400 animate-pulse">Fiyat verileri yükleniyor...</p>
                            </div>
                        ) : (
                            <ResultsCharts
                                results={filteredResults}
                                priceData={priceData.prices}
                                categoryFilter={categoryFilter}
                                listingTypeFilter={listingTypeFilter}
                            />
                        )}
                    </motion.div>
                ) : (
                    /* Table View */
                    <motion.div variants={itemVariants} className="space-y-4">
                        {/* City/District Filters */}
                        <div className="flex flex-wrap gap-3 items-center">
                            <span className="text-sm text-gray-400 flex items-center gap-2">
                                <MapPin className="w-4 h-4" />
                                Konum Filtresi:
                            </span>

                            {/* City Dropdown */}
                            <div className="relative" ref={cityDropdownRef}>
                                <button
                                    onClick={() => {
                                        setCityDropdownOpen(!cityDropdownOpen);
                                        setDistrictDropdownOpen(false);
                                    }}
                                    className="px-4 py-2 rounded-lg border border-slate-700 bg-slate-800/50 text-gray-300 hover:bg-slate-700/50 transition-colors flex items-center gap-2 min-w-[160px]"
                                >
                                    <span>
                                        {cityFilter.length === 0 ? 'İl Seçin' :
                                         cityFilter.length === cities.length ? 'Tüm İller' :
                                         `${cityFilter.length} İl Seçili`}
                                    </span>
                                    <svg className={`w-4 h-4 transition-transform ${cityDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </button>

                                {cityDropdownOpen && (
                                    <div className="absolute top-full left-0 mt-1 w-64 max-h-80 overflow-y-auto bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50">
                                        {/* Select All */}
                                        <button
                                            onClick={toggleAllCities}
                                            className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700 border-b border-slate-700 flex items-center gap-2"
                                        >
                                            <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                                                cityFilter.length === cities.length ? 'bg-blue-500 border-blue-500' : 'border-gray-500'
                                            }`}>
                                                {cityFilter.length === cities.length && (
                                                    <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                    </svg>
                                                )}
                                            </div>
                                            <span className="text-white font-medium">Tümünü Seç</span>
                                        </button>

                                        {/* City List */}
                                        {cities.map(city => (
                                            <button
                                                key={city}
                                                onClick={() => handleCityFilterChange(city)}
                                                className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700 flex items-center gap-2"
                                            >
                                                <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                                                    cityFilter.includes(city) ? 'bg-blue-500 border-blue-500' : 'border-gray-500'
                                                }`}>
                                                    {cityFilter.includes(city) && (
                                                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    )}
                                                </div>
                                                <span className="text-gray-300">{city}</span>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* District Dropdown */}
                            <div className="relative" ref={districtDropdownRef}>
                                <button
                                    onClick={() => {
                                        if (cityFilter.length > 0 && districts.length > 0) {
                                            setDistrictDropdownOpen(!districtDropdownOpen);
                                            setCityDropdownOpen(false);
                                        }
                                    }}
                                    disabled={cityFilter.length === 0 || districts.length === 0}
                                    className={`px-4 py-2 rounded-lg border border-slate-700 bg-slate-800/50 text-gray-300 transition-colors flex items-center gap-2 min-w-[160px] ${
                                        cityFilter.length === 0 || districts.length === 0 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-700/50'
                                    }`}
                                >
                                    <span>
                                        {cityFilter.length === 0 ? 'Önce İl Seçin' :
                                         districts.length === 0 ? 'İlçe Yok' :
                                         districtFilter.length === 0 ? 'İlçe Seçin' :
                                         districtFilter.length === districts.length ? 'Tüm İlçeler' :
                                         `${districtFilter.length} İlçe Seçili`}
                                    </span>
                                    <svg className={`w-4 h-4 transition-transform ${districtDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </button>

                                {districtDropdownOpen && districts.length > 0 && (
                                    <div className="absolute top-full left-0 mt-1 w-64 max-h-80 overflow-y-auto bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50">
                                        {/* Select All */}
                                        <button
                                            onClick={toggleAllDistricts}
                                            className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700 border-b border-slate-700 flex items-center gap-2"
                                        >
                                            <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                                                districtFilter.length === districts.length ? 'bg-emerald-500 border-emerald-500' : 'border-gray-500'
                                            }`}>
                                                {districtFilter.length === districts.length && (
                                                    <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                    </svg>
                                                )}
                                            </div>
                                            <span className="text-white font-medium">Tümünü Seç</span>
                                        </button>

                                        {/* District List */}
                                        {districts.map(district => (
                                            <button
                                                key={district}
                                                onClick={() => handleDistrictFilterChange(district)}
                                                className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700 flex items-center gap-2"
                                            >
                                                <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                                                    districtFilter.includes(district) ? 'bg-emerald-500 border-emerald-500' : 'border-gray-500'
                                                }`}>
                                                    {districtFilter.includes(district) && (
                                                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    )}
                                                </div>
                                                <span className="text-gray-300">{district}</span>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Clear Filters Button */}
                            {(cityFilter.length > 0 || districtFilter.length > 0) && (
                                <button
                                    onClick={() => {
                                        setCityFilter([]);
                                        setDistrictFilter([]);
                                    }}
                                    className="px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                                >
                                    Temizle
                                </button>
                            )}
                        </div>

                        {/* Table */}
                        <div className="overflow-x-auto">
                        <table className="w-full border-collapse">
                            <thead>
                                <tr className="border-b border-slate-700">
                                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Şehir</th>
                                    <th className="text-left py-4 px-4 text-gray-400 font-medium">İlçe</th>
                                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Platform</th>
                                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Kategori</th>
                                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Alt Kategori</th>
                                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Tür</th>
                                    <th className="text-right py-4 px-4 text-gray-400 font-medium">İlan</th>
                                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Tarih</th>
                                    <th className="text-right py-4 px-4 text-gray-400 font-medium">İşlem</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredResults.map((result, index) => (
                                    <tr key={result.id || index} className="border-b border-slate-800 hover:bg-slate-800/30 transition-colors">
                                        <td className="py-3 px-4">
                                            <div className="flex items-center gap-2">
                                                <MapPin className="w-4 h-4 text-sky-400" />
                                                <span className="text-white font-medium">{result.city || 'Bilinmiyor'}</span>
                                            </div>
                                        </td>
                                        <td className="py-3 px-4">
                                            {result.district ? (
                                                <span className="text-gray-300 text-sm">{result.district}</span>
                                            ) : (
                                                <span className="text-gray-600 text-xs">-</span>
                                            )}
                                        </td>
                                        <td className="py-3 px-4">
                                            <span className={`px-2 py-0.5 rounded text-xs ${result.platform === 'Emlakjet' ? 'bg-purple-500/20 text-purple-300' : 'bg-blue-500/20 text-blue-300'
                                                }`}>
                                                {result.platform}
                                            </span>
                                        </td>
                                        <td className="py-3 px-4">
                                            <span className={`px-2 py-0.5 rounded text-xs ${result.category === 'Konut' ? 'bg-emerald-500/20 text-emerald-300' :
                                                result.category === 'Arsa' ? 'bg-cyan-500/20 text-cyan-300' :
                                                    'bg-purple-500/20 text-purple-300'
                                                }`}>
                                                {result.category}
                                            </span>
                                        </td>
                                        <td className="py-3 px-4">
                                            {result.subtype ? (
                                                <span className="px-2 py-0.5 rounded text-xs bg-pink-500/20 text-pink-300">
                                                    {result.subtype}
                                                </span>
                                            ) : (
                                                <span className="text-gray-600 text-xs">-</span>
                                            )}
                                        </td>
                                        <td className="py-3 px-4">
                                            <span className={`px-2 py-0.5 rounded text-xs ${result.listing_type === 'Satılık' ? 'bg-amber-500/20 text-amber-300' : 'bg-orange-500/20 text-orange-300'}`}>
                                                {result.listing_type || '-'}
                                            </span>
                                        </td>
                                        <td className="py-3 px-4 text-right text-emerald-400 font-medium">{(result.count || 0).toLocaleString()}</td>
                                        <td className="py-3 px-4 text-gray-500 text-sm">{result.date}</td>
                                        <td className="py-3 px-4 text-right">
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    onClick={() => openPreview(result.files?.[0]?.name || '')}
                                                    className="p-2 rounded-lg hover:bg-slate-700 transition-colors"
                                                >
                                                    <Eye className="w-4 h-4 text-gray-400" />
                                                </button>
                                                <a
                                                    href={`http://localhost:8000/api/v1/download/${result.files?.[0]?.name}`}
                                                    className="p-2 rounded-lg hover:bg-emerald-600/20 transition-colors"
                                                >
                                                    <Download className="w-4 h-4 text-emerald-400" />
                                                </a>
                                                <button
                                                    onClick={() => deleteResult(result.files?.[0]?.name || '')}
                                                    className="p-2 rounded-lg hover:bg-red-600/20 transition-colors"
                                                    title="Sil"
                                                >
                                                    <Trash2 className="w-4 h-4 text-red-400" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        </div>
                    </motion.div>
                )}
            </motion.div>

            {/* Clear Confirm Modal */}
            <AnimatePresence>
                {showClearConfirm && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                    >
                        <motion.div
                            initial={{ scale: 0.9 }}
                            animate={{ scale: 1 }}
                            exit={{ scale: 0.9 }}
                            className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full"
                        >
                            <div className="flex items-center gap-4 mb-4">
                                <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center">
                                    <AlertTriangle className="w-6 h-6 text-red-500" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-white">Sonuçları Temizle</h3>
                                    <p className="text-sm text-gray-400">Bu işlem geri alınamaz!</p>
                                </div>
                            </div>
                            <p className="text-gray-300 mb-6">
                                Tüm tarama sonuçları ({totalFiles} dosya, {totalRecords} ilan) kalıcı olarak silinecek.
                            </p>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowClearConfirm(false)}
                                    className="flex-1 py-3 px-4 rounded-xl bg-slate-800 text-gray-300 hover:bg-slate-700"
                                >
                                    İptal
                                </button>
                                <button
                                    onClick={clearResults}
                                    disabled={clearing}
                                    className="flex-1 py-3 px-4 rounded-xl bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {clearing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                    {clearing ? 'Siliniyor...' : 'Evet, Sil'}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Preview Modal */}
            <AnimatePresence>
                {previewFile && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                        onClick={() => setPreviewFile(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.9, y: 20 }}
                            className="bg-slate-900 border border-slate-700 rounded-2xl max-w-5xl w-full max-h-[80vh] overflow-hidden flex flex-col"
                            onClick={(e) => e.stopPropagation()}
                        >
                            {/* Modal Header */}
                            <div className="flex items-center justify-between p-4 border-b border-slate-700">
                                <div>
                                    <h3 className="text-lg font-bold text-white">Veri Önizleme</h3>
                                    <p className="text-sm text-gray-400">{previewFile}</p>
                                </div>
                                <button
                                    onClick={() => setPreviewFile(null)}
                                    className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
                                >
                                    <X className="w-5 h-5 text-gray-400" />
                                </button>
                            </div>

                            {/* Modal Content */}
                            <div className="flex-1 overflow-auto p-4">
                                {previewLoading ? (
                                    <div className="flex items-center justify-center py-12">
                                        <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                                    </div>
                                ) : previewData?.data?.length > 0 ? (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="border-b border-slate-700">
                                                    {Object.keys(previewData.data[0]).slice(0, 8).map((key) => (
                                                        <th key={key} className="text-left py-2 px-3 text-gray-400 font-medium whitespace-nowrap">
                                                            {key}
                                                        </th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {previewData.data.map((row: any, idx: number) => (
                                                    <tr key={idx} className="border-b border-slate-800">
                                                        {Object.values(row).slice(0, 8).map((val: any, cidx: number) => (
                                                            <td key={cidx} className="py-2 px-3 text-gray-300 max-w-[200px] truncate">
                                                                {String(val || '-')}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                        <p className="text-center text-gray-500 text-sm mt-4">
                                            {previewData.showing} / {previewData.total} kayıt gösteriliyor
                                        </p>
                                    </div>
                                ) : (
                                    <p className="text-center text-gray-400 py-12">Veri bulunamadı</p>
                                )}
                            </div>

                            {/* Modal Footer */}
                            <div className="p-4 border-t border-slate-700 flex justify-end gap-3">
                                <button
                                    onClick={() => setPreviewFile(null)}
                                    className="px-4 py-2 rounded-lg bg-slate-800 text-gray-300 hover:bg-slate-700"
                                >
                                    Kapat
                                </button>
                                <a
                                    href={`http://localhost:8000/api/v1/download/${previewFile}`}
                                    className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 flex items-center gap-2"
                                >
                                    <Download className="w-4 h-4" />
                                    Tümünü İndir
                                </a>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
