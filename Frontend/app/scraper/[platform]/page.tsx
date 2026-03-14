'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { Checkbox } from '@/components/ui/Checkbox';
import { CitySelectionModal } from '@/components/ui/CitySelectionModal';
import { useScraping } from '@/contexts/ScrapingContext';
import { motion } from 'framer-motion';
import { Play, Loader2, XCircle, Sparkles, X, MapPin } from 'lucide-react';
import Link from 'next/link';
import { startScrape, getCategories, getSubtypes } from '@/lib/api';
import type { Platform, ListingType, Category, HepsiemlakScrapingMethod } from '@/types';
import type { Subtype } from '@/lib/api';
import dynamic from 'next/dynamic';

const FloatingLines = dynamic(() => import('@/components/ui/FloatingLines'), { ssr: false });

export default function PlatformScraperPage() {
    const params = useParams();
    const platform = params.platform as Platform;

    const [listingType, setListingType] = useState<ListingType>('satilik');
    const [category, setCategory] = useState('konut');
    const [selectedCities, setSelectedCities] = useState<string[]>([]);
    const [selectedDistricts, setSelectedDistricts] = useState<Record<string, string[]>>({});
    const minPages = Number(process.env.NEXT_PUBLIC_HEPSIEMLAK_MIN_PAGES) || 1;
    const defaultMaxPages = Number(process.env.NEXT_PUBLIC_HEPSIEMLAK_MAX_PAGES) || 1;
    const minListings = Number(process.env.NEXT_PUBLIC_EMLAKJET_MIN_LISTINGS) || 100;
    const defaultMaxListings = Number(process.env.NEXT_PUBLIC_EMLAKJET_MAX_LISTINGS) || 1000;

    const [maxPages, setMaxPages] = useState(defaultMaxPages);
    const [scrapeAllPages, setScrapeAllPages] = useState(false);
    const [maxListings, setMaxListings] = useState(defaultMaxListings);
    const [scrapeAllListings, setScrapeAllListings] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
    const [isMapModalOpen, setIsMapModalOpen] = useState(false);
    const { startTracking, activeTask } = useScraping();

    // API'den dinamik kategoriler
    const [categories, setCategories] = useState<Category[]>([]);
    const [categoriesLoading, setCategoriesLoading] = useState(true);

    // API'den alt kategoriler
    const [subtypes, setSubtypes] = useState<Subtype[]>([]);
    const [selectedSubtype, setSelectedSubtype] = useState<Subtype | null>(null);
    const [subtypesLoading, setSubtypesLoading] = useState(false);
    const [scrapingMethod, setScrapingMethod] = useState<HepsiemlakScrapingMethod>('selenium');
    const [proxyEnabled, setProxyEnabled] = useState(false);

    const platformName = platform === 'emlakjet' ? 'EmlakJet' : 'HepsiEmlak';
    const scrapingMethodOptions = [
        { value: 'selenium', label: 'Selenium' },
        { value: 'scrapling_stealth_session', label: 'Scrapling StealthSession' },
        { value: 'scrapling_fetcher_session', label: 'Scrapling FetcherSession' },
        { value: 'scrapling_dynamic_session', label: 'Scrapling DynamicSession' },
        { value: 'scrapling_spider_fetcher_session', label: 'Scrapling Spider + FetcherSession' },
        { value: 'scrapling_spider_dynamic_session', label: 'Scrapling Spider + AsyncDynamicSession' },
        { value: 'scrapling_spider_stealth_session', label: 'Scrapling Spider + AsyncStealthySession' },
    ];

    // Platform/ilan tipi değiştiğinde API'den kategorileri çek
    useEffect(() => {
        const fetchCategories = async () => {
            setCategoriesLoading(true);
            try {
                const response = await getCategories();
                const platformCategories = response[platform]?.[listingType] || [];
                setCategories(platformCategories);

                // Mevcut kategori listede yoksa sıfırla
                if (platformCategories.length > 0) {
                    const currentCategoryExists = platformCategories.some(c => c.id === category);
                    if (!currentCategoryExists) {
                        setCategory(platformCategories[0].id);
                    }
                }
            } catch (error) {
                console.error('Kategoriler alınamadı:', error);
                setCategories([]);
            } finally {
                setCategoriesLoading(false);
            }
        };

        fetchCategories();
    }, [platform, listingType]);

    // Kategori değiştiğinde alt kategorileri çek
    useEffect(() => {
        const fetchSubtypesData = async () => {
            setSubtypesLoading(true);
            setSelectedSubtype(null);

            try {
                const response = await getSubtypes(listingType, category, platform);
                setSubtypes(response.subtypes || []);
            } catch (error) {
                console.error('Alt kategoriler alınamadı:', error);
                setSubtypes([]);
            } finally {
                setSubtypesLoading(false);
            }
        };

        fetchSubtypesData();
    }, [platform, listingType, category]);


    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Şehir seçimi zorunlu
        if (selectedCities.length === 0) {
            setResult({
                type: 'error',
                message: 'Lütfen en az bir şehir seçin. Haritadan şehir seçmek için butona tıklayın.',
            });
            return;
        }

        const isMethodValid = scrapingMethodOptions.some(
            (option) => option.value === scrapingMethod
        );
        if (!isMethodValid) {
            setResult({
                type: 'error',
                message: 'Geçersiz scraping yöntemi seçimi. Lütfen sayfayı yenileyip tekrar deneyin.',
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
                scraping_method: scrapingMethod,
                proxy_enabled: Boolean(proxyEnabled),
                cities: selectedCities,
                districts: selectedDistricts,
                ...(platform === 'emlakjet'
                    ? scrapeAllListings ? {} : { max_listings: maxListings || defaultMaxListings }
                    : scrapeAllPages ? {} : { max_pages: maxPages || defaultMaxPages }
                ),
            });

            // Global context'te takip başlat
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
        <div className="relative min-h-screen bg-black">
            {/* Floating Lines Background */}
            <div className="fixed inset-0 z-0">
                <FloatingLines
                    linesGradient={['#38bdf8', '#0ea5e9', '#34d399', '#818cf8']}
                    enabledWaves={['top', 'middle', 'bottom']}
                    lineCount={5}
                    lineDistance={5}
                    bendRadius={5}
                    bendStrength={-0.5}
                    interactive
                    parallax
                />
            </div>

            {/* Dark Gradient Overlay */}
            <div className="fixed inset-0 z-[1] bg-gradient-to-b from-black/70 via-black/50 to-black/85 pointer-events-none" />

            {/* Content */}
            <div className="relative z-10 px-6 lg:px-8 py-8">
                <div className="max-w-4xl mx-auto space-y-8">
                    {/* Yapılandırma Formu */}
                    <div className="backdrop-blur-xl bg-black/40 rounded-2xl p-6 border border-white/10 hover:border-sky-500/30 hover:bg-black/50 transition-all relative">
                        {/* Geri Dön Butonu - Sağ Üst Köşe */}
                        <div className="absolute top-6 right-6">
                            <Link href="/scraper">
                                <div className="text-gray-400 hover:text-white inline-flex items-center gap-2 transition-colors">
                                    ← Geri Dön
                                </div>
                            </Link>
                        </div>

                        {/* Başlık */}
                        <div className="mb-6">
                            <h1 className="text-4xl font-bold bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-transparent mb-3 flex items-center gap-3">
                                <Sparkles className="w-8 h-8 text-sky-400" />
                                {platformName}
                            </h1>
                            <p className="text-xl text-gray-400">
                                🎯 Tarama parametrelerini ayarlayın
                            </p>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-6">
                    {/* İlan Tipi ve Kategori */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Select
                            label="İlan Tipi"
                            value={listingType}
                            onChange={(e) => setListingType(e.target.value as ListingType)}
                            options={[
                                { value: 'satilik', label: '💰 Satılık' },
                                { value: 'kiralik', label: '🔑 Kiralık' },
                            ]}
                            className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-sky-500/50 focus:ring-sky-500/20"
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
                            className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-sky-500/50 focus:ring-sky-500/20"
                        />
                    </div>

                    <div className="flex flex-col md:flex-row md:items-end gap-4 md:gap-6">
                        <div className="flex-1">
                            <Select
                                label="Scraping Yontemi"
                                value={scrapingMethod}
                                onChange={(e) => setScrapingMethod(e.target.value as HepsiemlakScrapingMethod)}
                                options={scrapingMethodOptions}
                                className="w-full bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-sky-500/50 focus:ring-sky-500/20"
                            />
                        </div>
                        <div className="pb-3 md:ml-auto md:shrink-0">
                            <Checkbox
                                label="Proxy Kullan"
                                checked={proxyEnabled}
                                onChange={setProxyEnabled}
                            />
                        </div>
                    </div>

                    {/* Alt Kategori */}
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
                            className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-sky-500/50 focus:ring-sky-500/20"
                        />
                        {subtypesLoading && (
                            <p className="text-xs text-amber-400 mt-1 flex items-center gap-1">
                                <Loader2 className="w-3 h-3 animate-spin" />
                                Alt kategoriler alınıyor...
                            </p>
                        )}
                    </div>

                    {/* Şehirler */}
                    <div>
                        <label className="text-sm font-medium text-gray-300 mb-2 block">
                            🌍 Şehirler
                        </label>
                        <button
                            type="button"
                            onClick={() => setIsMapModalOpen(true)}
                            className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-sky-500/30 transition-all text-gray-200 font-medium"
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

                    {/* Şehir Seçim Modalı */}
                    <CitySelectionModal
                        isOpen={isMapModalOpen}
                        onClose={() => setIsMapModalOpen(false)}
                        selectedCities={selectedCities}
                        onCitiesChange={setSelectedCities}
                        selectedDistricts={selectedDistricts}
                        onDistrictsChange={setSelectedDistricts}
                    />

                    {/* Limit Ayarları */}
                    {platform === 'emlakjet' ? (
                        <div className="flex items-end gap-4">
                            <div className="flex-1">
                                <Input
                                    label="📊 Maksimum İlan Sayısı"
                                    type="number"
                                    min={minListings}
                                    max={defaultMaxListings}
                                    step={1}
                                    value={maxListings || ''}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        if (val === '') {
                                            setMaxListings(0);
                                        } else {
                                            const num = parseInt(val);
                                            setMaxListings(Math.min(defaultMaxListings, Math.max(minListings, num || defaultMaxListings)));
                                        }
                                    }}
                                    onBlur={() => {
                                        if (maxListings < minListings) setMaxListings(minListings);
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
                                    min={minPages}
                                    max={defaultMaxPages}
                                    step={1}
                                    value={maxPages || ''}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        if (val === '') {
                                            setMaxPages(0);
                                        } else {
                                            const num = parseInt(val);
                                            setMaxPages(Math.min(defaultMaxPages, Math.max(minPages, num || defaultMaxPages)));
                                        }
                                    }}
                                    onBlur={() => {
                                        if (maxPages < minPages) setMaxPages(minPages);
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

                    {/* Gönder Butonu */}
                    <button
                        type="submit"
                        disabled={isLoading || (activeTask?.isFinished === false)}
                        className={`w-full bg-gradient-to-r from-sky-500 to-emerald-500 hover:from-sky-600 hover:to-emerald-600 text-white font-bold py-4 rounded-xl shadow-lg shadow-sky-500/25 hover:shadow-sky-500/40 transition-all ${isLoading || (activeTask?.isFinished === false) ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'
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

                    {/* Sonuç (sadece hata göster) */}
                    {result?.type === 'error' && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                        >
                            <div className="backdrop-blur-xl bg-black/40 rounded-2xl p-6 border-2 border-red-500/30 bg-red-500/10">
                                <div className="flex items-start gap-4">
                                    <XCircle className="w-8 h-8 text-red-400 flex-shrink-0" />
                                    <div>
                                        <p className="font-bold text-lg text-red-300">❌ Hata!</p>
                                        <p className="text-gray-300 mt-1">{result.message}</p>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </form>
            </div>
        </div>
            </div>
        </div>
    );
}
