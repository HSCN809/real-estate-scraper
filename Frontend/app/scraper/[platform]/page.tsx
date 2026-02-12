'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { ArtCard } from '@/components/ui/ArtCard';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { Checkbox } from '@/components/ui/Checkbox';
import { CitySelectionModal } from '@/components/ui/CitySelectionModal';
import { useScraping } from '@/contexts/ScrapingContext';
import { motion } from 'framer-motion';
import { Play, Loader2, CheckCircle2, XCircle, Sparkles, X, MapPin } from 'lucide-react';
import Link from 'next/link';
import { startScrape, getCategories, getSubtypes } from '@/lib/api';
import type { Platform, ListingType, Category } from '@/types';
import type { Subtype } from '@/lib/api';

export default function PlatformScraperPage() {
    const params = useParams();
    const platform = params.platform as Platform;

    const [listingType, setListingType] = useState<ListingType>('satilik');
    const [category, setCategory] = useState('konut');
    const [selectedCities, setSelectedCities] = useState<string[]>([]);
    const [selectedDistricts, setSelectedDistricts] = useState<Record<string, string[]>>({});
    const [maxPages, setMaxPages] = useState(1);
    const [scrapeAllPages, setScrapeAllPages] = useState(false);
    const [maxListings, setMaxListings] = useState(1000);
    const [scrapeAllListings, setScrapeAllListings] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
    const [isMapModalOpen, setIsMapModalOpen] = useState(false);
    const { startTracking, activeTask } = useScraping();

    // Dynamic categories from API
    const [categories, setCategories] = useState<Category[]>([]);
    const [categoriesLoading, setCategoriesLoading] = useState(true);

    // Dynamic subtypes from API (HepsiEmlak only)
    const [subtypes, setSubtypes] = useState<Subtype[]>([]);
    const [selectedSubtype, setSelectedSubtype] = useState<Subtype | null>(null);
    const [subtypesLoading, setSubtypesLoading] = useState(false);

    const platformName = platform === 'emlakjet' ? 'EmlakJet' : 'HepsiEmlak';
    const platformIcon = platform === 'emlakjet' ? '🔵' : '🟢';
    const platformGradient = platform === 'emlakjet' ? 'gradient-art-blue' : 'gradient-art-pink';
    const platformColor = platform === 'emlakjet' ? 'blue' : 'pink';

    // Fetch categories from API on mount and when platform/listingType changes
    useEffect(() => {
        const fetchCategories = async () => {
            setCategoriesLoading(true);
            try {
                const response = await getCategories();
                const platformCategories = response[platform]?.[listingType] || [];
                setCategories(platformCategories);

                // Reset category selection if current category not in new list
                if (platformCategories.length > 0) {
                    const currentCategoryExists = platformCategories.some(c => c.id === category);
                    if (!currentCategoryExists) {
                        setCategory(platformCategories[0].id);
                    }
                }
            } catch (error) {
                console.error('Failed to fetch categories:', error);
                setCategories([]);
            } finally {
                setCategoriesLoading(false);
            }
        };

        fetchCategories();
    }, [platform, listingType]);

    // Fetch subtypes when category changes (Both HepsiEmlak and EmlakJet)
    useEffect(() => {
        const fetchSubtypesData = async () => {
            setSubtypesLoading(true);
            setSelectedSubtype(null);

            try {
                const response = await getSubtypes(listingType, category, platform);
                setSubtypes(response.subtypes || []);
            } catch (error) {
                console.error('Failed to fetch subtypes:', error);
                setSubtypes([]);
            } finally {
                setSubtypesLoading(false);
            }
        };

        fetchSubtypesData();
    }, [platform, listingType, category]);


    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Require city selection
        if (selectedCities.length === 0) {
            setResult({
                type: 'error',
                message: 'Lütfen en az bir şehir seçin. Haritadan şehir seçmek için butona tıklayın.',
            });
            return;
        }

        setIsLoading(true);
        setResult(null);

        try {
            const response = await startScrape(platform, {
                category,
                listing_type: listingType,
                subtype: selectedSubtype?.id,
                subtype_path: selectedSubtype?.path,
                cities: selectedCities,
                districts: selectedDistricts,
                ...(platform === 'emlakjet'
                    ? { max_listings: scrapeAllListings ? 0 : (maxListings || 1000) }
                    : { max_pages: scrapeAllPages ? 9999 : (maxPages || 1) }
                ),
            });

            // Start tracking in global context
            if (response.task_id) {
                startTracking(response.task_id, platform);
            }

            setResult({ type: 'success', message: response.message });
        } catch (error) {
            setResult({
                type: 'error',
                message: error instanceof Error ? error.message : 'Bilinmeyen hata',
            });
        } finally {
            setIsLoading(false);
        }
    };

    const removeCity = (city: string) => {
        setSelectedCities(selectedCities.filter((c) => c !== city));
        // İlgili ilçeleri de temizle
        const { [city]: _, ...restDistricts } = selectedDistricts;
        setSelectedDistricts(restDistricts);
    };

    return (
        <div className="space-y-8 max-w-4xl relative z-10">
            {/* Header */}
            <div>
                <Link href="/scraper">
                    <div className="text-gray-400 hover:text-white mb-4 inline-flex items-center gap-2 transition-colors">
                        ← Geri Dön
                    </div>
                </Link>
                <div className="flex items-center gap-4 mb-3">
                    <span className="text-7xl">{platformIcon}</span>
                    <h1 className={`art-title ${platformGradient}`}>
                        {platformName}
                    </h1>
                </div>
                <p className="text-xl text-gray-300">
                    🎯 Tarama parametrelerini ayarlayın
                </p>
            </div>

            {/* Configuration Form */}
            <ArtCard glowColor={platformColor}>
                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                    <Sparkles className="w-6 h-6" />
                    Konfigürasyon
                </h2>

                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Listing Type & Category */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Select
                            label="İlan Tipi"
                            value={listingType}
                            onChange={(e) => setListingType(e.target.value as ListingType)}
                            options={[
                                { value: 'satilik', label: '💰 Satılık' },
                                { value: 'kiralik', label: '🔑 Kiralık' },
                            ]}
                        />

                        <Select
                            label="Kategori"
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            options={categoriesLoading
                                ? [{ value: '', label: '⏳ Yükleniyor...' }]
                                : categories.map((c) => ({ value: c.id, label: `🏠 ${c.name}` }))
                            }
                            disabled={categoriesLoading}
                        />
                    </div>

                    {/* Subcategory - For both HepsiEmlak and EmlakJet */}
                    <div>
                        <Select
                            label="📋 Alt Kategori (Opsiyonel)"
                            value={selectedSubtype?.id || ''}
                            onChange={(e) => {
                                const selected = subtypes.find(s => s.id === e.target.value);
                                setSelectedSubtype(selected || null);
                            }}
                            options={[
                                {
                                    value: '',
                                    label: subtypesLoading
                                        ? '⏳ Alt kategoriler yükleniyor...'
                                        : subtypes.length === 0
                                            ? '🔄 Alt kategori bulunamadı'
                                            : '🔄 Tümü (Alt kategori seçme)'
                                },
                                ...subtypes.map((s) => ({ value: s.id, label: `📋 ${s.name}` }))
                            ]}
                            disabled={subtypesLoading || subtypes.length === 0}
                        />
                        {subtypesLoading && (
                            <p className="text-xs text-amber-400 mt-1 flex items-center gap-1">
                                <Loader2 className="w-3 h-3 animate-spin" />
                                Alt kategoriler alınıyor...
                            </p>
                        )}
                    </div>

                    {/* Cities */}
                    <div>
                        <label className="text-sm font-medium text-slate-300 mb-2 block">
                            🌍 Şehirler
                        </label>
                        <button
                            type="button"
                            onClick={() => setIsMapModalOpen(true)}
                            className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl bg-slate-800/50 border border-slate-600 hover:bg-slate-700/50 hover:border-sky-500/50 transition-all text-slate-200 font-medium"
                        >
                            <MapPin className="w-5 h-5 text-sky-400" />
                            {selectedCities.length > 0 ? `${selectedCities.length} Şehir Seçildi` : 'Haritadan Şehir Seç'}
                        </button>
                        {selectedCities.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-4">
                                {selectedCities.slice(0, 8).map((city) => {
                                    const cityDistricts = selectedDistricts[city] || [];
                                    const hasDistricts = cityDistricts.length > 0;

                                    return (
                                        <motion.div
                                            key={city}
                                            initial={{ scale: 0 }}
                                            animate={{ scale: 1 }}
                                            className="inline-flex flex-col gap-1"
                                        >
                                            {/* Şehir Badge */}
                                            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-sm font-medium">
                                                <span className="font-semibold">{city}</span>
                                                {hasDistricts && (
                                                    <span className="text-xs bg-emerald-500/30 px-1.5 py-0.5 rounded-full">
                                                        {cityDistricts.length}
                                                    </span>
                                                )}
                                                <button
                                                    type="button"
                                                    onClick={() => removeCity(city)}
                                                    className="hover:text-red-400 transition-colors"
                                                >
                                                    <X className="w-3 h-3" />
                                                </button>
                                            </div>

                                            {/* İlçeler */}
                                            {hasDistricts && (
                                                <div className="flex flex-wrap gap-1 ml-2">
                                                    {cityDistricts.slice(0, 3).map((district) => (
                                                        <span
                                                            key={district}
                                                            className="text-xs px-2 py-0.5 rounded bg-sky-500/20 border border-sky-500/30 text-sky-300"
                                                        >
                                                            {district}
                                                        </span>
                                                    ))}
                                                    {cityDistricts.length > 3 && (
                                                        <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-400">
                                                            +{cityDistricts.length - 3}
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                        </motion.div>
                                    );
                                })}
                                {selectedCities.length > 8 && (
                                    <span className="px-3 py-1.5 rounded-full bg-slate-700 text-slate-300 text-sm">
                                        +{selectedCities.length - 8} daha
                                    </span>
                                )}
                            </div>
                        )}
                        <p className="text-xs text-slate-500 mt-2">
                            Boş bırakılırsa tüm şehirler taranır
                        </p>
                    </div>

                    {/* City Selection Modal */}
                    <CitySelectionModal
                        isOpen={isMapModalOpen}
                        onClose={() => setIsMapModalOpen(false)}
                        selectedCities={selectedCities}
                        onCitiesChange={setSelectedCities}
                        selectedDistricts={selectedDistricts}
                        onDistrictsChange={setSelectedDistricts}
                    />

                    {/* Limit Section - Platform'a göre farklı */}
                    {platform === 'emlakjet' ? (
                        <div className="flex items-end gap-4">
                            <div className="flex-1">
                                <Input
                                    label="📊 Maksimum İlan Sayısı"
                                    type="number"
                                    min={100}
                                    max={50000}
                                    step={100}
                                    value={maxListings || ''}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        if (val === '') {
                                            setMaxListings(0);
                                        } else {
                                            const num = parseInt(val);
                                            setMaxListings(Math.min(50000, Math.max(100, num || 1000)));
                                        }
                                    }}
                                    onBlur={() => {
                                        if (maxListings < 100) setMaxListings(100);
                                    }}
                                    disabled={scrapeAllListings}
                                    className={scrapeAllListings ? 'opacity-50 cursor-not-allowed' : ''}
                                />
                            </div>
                            <div className="pb-3">
                                <Checkbox
                                    label="Tümünü Tara (Limit Yok)"
                                    checked={scrapeAllListings}
                                    onChange={setScrapeAllListings}
                                />
                            </div>
                        </div>
                    ) : (
                        <div className="flex items-end gap-4">
                            <div className="flex-1">
                                <Input
                                    label="📄 Maksimum Sayfa"
                                    type="number"
                                    min={1}
                                    max={50}
                                    value={maxPages || ''}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        if (val === '') {
                                            setMaxPages(0);
                                        } else {
                                            const num = parseInt(val);
                                            setMaxPages(Math.min(50, Math.max(1, num || 1)));
                                        }
                                    }}
                                    onBlur={() => {
                                        if (maxPages < 1) setMaxPages(1);
                                    }}
                                    disabled={scrapeAllPages}
                                    className={scrapeAllPages ? 'opacity-50 cursor-not-allowed' : ''}
                                />
                            </div>
                            <div className="pb-3">
                                <Checkbox
                                    label="Tüm Sayfaları Tara"
                                    checked={scrapeAllPages}
                                    onChange={setScrapeAllPages}
                                />
                            </div>
                        </div>
                    )}

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={isLoading || (activeTask && !activeTask.isFinished)}
                        className={`art-button w-full p-4 rounded-xl text-lg font-bold transition-all ${isLoading || (activeTask && !activeTask.isFinished) ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'
                            }`}
                    >
                        {isLoading ? (
                            <span className="flex items-center justify-center gap-3">
                                <Loader2 className="w-6 h-6 animate-spin" />
                                Tarama Başlatılıyor...
                            </span>
                        ) : (
                            <span className="flex items-center justify-center gap-3">
                                <Play className="w-6 h-6" />
                                Taramayı Başlat
                            </span>
                        )}
                    </button>

                    {/* Result */}
                    {result && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                        >
                            <ArtCard
                                glowColor={result.type === 'success' ? 'blue' : 'pink'}
                                className={`border-2 ${result.type === 'success'
                                    ? 'border-green-500/50 bg-green-500/10'
                                    : 'border-red-500/50 bg-red-500/10'
                                    }`}
                            >
                                <div className="flex items-start gap-4">
                                    {result.type === 'success' ? (
                                        <CheckCircle2 className="w-8 h-8 text-green-400 flex-shrink-0" />
                                    ) : (
                                        <XCircle className="w-8 h-8 text-red-400 flex-shrink-0" />
                                    )}
                                    <div>
                                        <p className={`font-bold text-lg ${result.type === 'success' ? 'text-green-300' : 'text-red-300'}`}>
                                            {result.type === 'success' ? '✅ Başarılı!' : '❌ Hata!'}
                                        </p>
                                        <p className="text-gray-300 mt-1">{result.message}</p>
                                    </div>
                                </div>
                            </ArtCard>
                        </motion.div>
                    )}
                </form>
            </ArtCard>
        </div>
    );
}
