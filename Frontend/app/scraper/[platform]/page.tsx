'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { ArtCard } from '@/components/ui/ArtCard';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { Checkbox } from '@/components/ui/Checkbox';
import { CitySelectionModal } from '@/components/ui/CitySelectionModal';
import { ProgressModal } from '@/components/ui/ProgressModal';
import { motion } from 'framer-motion';
import { Play, Loader2, CheckCircle2, XCircle, Sparkles, X, MapPin } from 'lucide-react';
import Link from 'next/link';
import { startScrape } from '@/lib/api';
import { CATEGORIES, type Platform, type ListingType } from '@/types';

export default function PlatformScraperPage() {
    const params = useParams();
    const platform = params.platform as Platform;

    const [listingType, setListingType] = useState<ListingType>('satilik');
    const [category, setCategory] = useState('konut');
    const [selectedCities, setSelectedCities] = useState<string[]>([]);
    const [maxPages, setMaxPages] = useState(1);
    const [scrapeAllPages, setScrapeAllPages] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
    const [isMapModalOpen, setIsMapModalOpen] = useState(false);
    const [isProgressModalOpen, setIsProgressModalOpen] = useState(false);

    const platformName = platform === 'emlakjet' ? 'EmlakJet' : 'HepsiEmlak';
    const platformIcon = platform === 'emlakjet' ? '🔵' : '🟢';
    const platformGradient = platform === 'emlakjet' ? 'gradient-art-blue' : 'gradient-art-pink';
    const platformColor = platform === 'emlakjet' ? 'blue' : 'pink';

    const categories = CATEGORIES[platform]?.[listingType] || [];

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
        setIsProgressModalOpen(true); // Modal'ı hemen aç

        try {
            const response = await startScrape(platform, {
                category,
                listing_type: listingType,
                cities: selectedCities,
                max_pages: scrapeAllPages ? 9999 : (maxPages || 1),
            });

            setResult({ type: 'success', message: response.message });
        } catch (error) {
            setResult({
                type: 'error',
                message: error instanceof Error ? error.message : 'Bilinmeyen hata',
            });
            setIsProgressModalOpen(false); // Hata varsa kapat
        } finally {
            setIsLoading(false);
        }
    };

    const removeCity = (city: string) => {
        setSelectedCities(selectedCities.filter((c) => c !== city));
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
                            options={categories.map((c) => ({ value: c.id, label: `🏠 ${c.name}` }))}
                        />
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
                                {selectedCities.slice(0, 8).map((city) => (
                                    <motion.span
                                        key={city}
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-sm font-medium"
                                    >
                                        {city}
                                        <button
                                            type="button"
                                            onClick={() => removeCity(city)}
                                            className="hover:text-red-400 transition-colors"
                                        >
                                            <X className="w-3 h-3" />
                                        </button>
                                    </motion.span>
                                ))}
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
                    />

                    {/* Progress Modal */}
                    <ProgressModal
                        isOpen={isProgressModalOpen}
                        onClose={() => setIsProgressModalOpen(false)}
                    />

                    {/* Max Pages & Scrape All */}
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
                                        setMaxPages(0); // Geçici olarak 0, submit'te 1 olarak işlenecek
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

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={isLoading}
                        className={`art-button w-full p-4 rounded-xl text-lg font-bold transition-all ${isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'
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
