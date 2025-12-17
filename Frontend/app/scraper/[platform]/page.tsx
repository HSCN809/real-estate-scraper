'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { ArtCard } from '@/components/ui/ArtCard';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { motion } from 'framer-motion';
import { Play, Loader2, CheckCircle2, XCircle, Sparkles, X } from 'lucide-react';
import Link from 'next/link';
import { startScrape } from '@/lib/api';
import { CATEGORIES, TURKISH_CITIES, type Platform, type ListingType } from '@/types';

export default function PlatformScraperPage() {
    const params = useParams();
    const platform = params.platform as Platform;

    const [listingType, setListingType] = useState<ListingType>('satilik');
    const [category, setCategory] = useState('konut');
    const [selectedCities, setSelectedCities] = useState<string[]>([]);
    const [maxPages, setMaxPages] = useState(1);
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

    const platformName = platform === 'emlakjet' ? 'EmlakJet' : 'HepsiEmlak';
    const platformIcon = platform === 'emlakjet' ? '🔵' : '🟢';
    const platformGradient = platform === 'emlakjet' ? 'gradient-art-blue' : 'gradient-art-pink';
    const platformColor = platform === 'emlakjet' ? 'blue' : 'pink';

    const categories = CATEGORIES[platform]?.[listingType] || [];

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setResult(null);

        try {
            const response = await startScrape(platform, {
                category,
                listing_type: listingType,
                cities: selectedCities.length > 0 ? selectedCities : undefined,
                max_pages: maxPages,
            });

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

    const handleCityChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const city = e.target.value;
        if (city && !selectedCities.includes(city)) {
            setSelectedCities([...selectedCities, city]);
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
                        <label className="text-sm font-medium text-gray-300 mb-2 block">
                            🌍 Şehirler
                        </label>
                        <Select
                            value=""
                            onChange={handleCityChange}
                            options={[
                                { value: '', label: 'Şehir ekle...' },
                                ...TURKISH_CITIES.map((city) => ({ value: city, label: city })),
                            ]}
                        />
                        {selectedCities.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-4">
                                {selectedCities.map((city) => (
                                    <motion.span
                                        key={city}
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r ${platform === 'emlakjet' ? 'from-blue-500/20 to-cyan-500/20 border-blue-500/30' : 'from-pink-500/20 to-purple-500/20 border-pink-500/30'
                                            } border text-white font-semibold`}
                                    >
                                        {city}
                                        <button
                                            type="button"
                                            onClick={() => removeCity(city)}
                                            className="hover:scale-125 transition-transform"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </motion.span>
                                ))}
                            </div>
                        )}
                        <p className="text-xs text-gray-500 mt-2">
                            Boş bırakılırsa tüm şehirler taranır
                        </p>
                    </div>

                    {/* Max Pages */}
                    <Input
                        label="📄 Maksimum Sayfa"
                        type="number"
                        min={1}
                        max={50}
                        value={maxPages}
                        onChange={(e) => setMaxPages(parseInt(e.target.value) || 1)}
                    />

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
