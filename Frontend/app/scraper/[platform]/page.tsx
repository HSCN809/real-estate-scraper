'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { motion } from 'framer-motion';
import { ArrowLeft, Play, Loader2, CheckCircle2, XCircle, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { startScrape } from '@/lib/api';
import { CATEGORIES, TURKISH_CITIES, type Platform, type ListingType } from '@/types';

const container = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.1 },
    },
};

const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
};

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
    const platformGradient = platform === 'emlakjet' ? 'from-blue-500 to-cyan-500' : 'from-green-500 to-emerald-500';

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
        <motion.div
            className="space-y-6 max-w-3xl"
            variants={container}
            initial="hidden"
            animate="show"
        >
            {/* Header */}
            <motion.div variants={item}>
                <Link href="/scraper">
                    <Button variant="ghost" className="mb-4 text-gray-300 hover:text-white">
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Geri
                    </Button>
                </Link>
                <div className="flex items-center gap-4 mb-2">
                    <span className="text-5xl">{platformIcon}</span>
                    <h1 className="text-4xl font-bold gradient-text-neon">
                        {platformName}
                    </h1>
                </div>
                <p className="text-gray-300 text-lg">
                    🎯 Tarama parametrelerini ayarlayın
                </p>
            </motion.div>

            {/* Form Card */}
            <motion.div variants={item}>
                <GlassCard variant="strong" neonBorder="purple" glow>
                    <div className={`h-1 w-full bg-gradient-to-r ${platformGradient} rounded-t-2xl -mt-6 -mx-6 mb-6`} />

                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* Listing Type & Category */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                        <GlassCard variant="dark" className="p-4">
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
                                <div className="flex flex-wrap gap-2 mt-3">
                                    {selectedCities.map((city) => (
                                        <motion.span
                                            key={city}
                                            initial={{ scale: 0 }}
                                            animate={{ scale: 1 }}
                                            exit={{ scale: 0 }}
                                            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-full glass neon-border-blue text-white"
                                        >
                                            {city}
                                            <button
                                                type="button"
                                                onClick={() => removeCity(city)}
                                                className="ml-1 hover:text-red-400 transition-colors"
                                            >
                                                ×
                                            </button>
                                        </motion.span>
                                    ))}
                                </div>
                            )}
                            <p className="text-xs text-gray-500 mt-2">
                                Boş bırakılırsa tüm şehirler taranır
                            </p>
                        </GlassCard>

                        {/* Max Pages */}
                        <div>
                            <Input
                                label="📄 Maksimum Sayfa"
                                type="number"
                                min={1}
                                max={50}
                                value={maxPages}
                                onChange={(e) => setMaxPages(parseInt(e.target.value) || 1)}
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Sayfa başına ~20 ilan
                            </p>
                        </div>

                        {/* Submit Button */}
                        <Button
                            type="submit"
                            className={`w-full bg-gradient-to-r ${platformGradient} hover:shadow-lg hover:shadow-purple-500/50 transition-all group relative overflow-hidden`}
                            disabled={isLoading}
                        >
                            <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                            <span className="relative flex items-center justify-center">
                                {isLoading ? (
                                    <>
                                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                        Tarama Başlatılıyor...
                                    </>
                                ) : (
                                    <>
                                        <Play className="w-5 h-5 mr-2" />
                                        Taramayı Başlat
                                    </>
                                )}
                            </span>
                        </Button>

                        {/* Result */}
                        {result && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                            >
                                <GlassCard
                                    variant="dark"
                                    className={`border-2 ${result.type === 'success'
                                            ? 'border-green-500/50 bg-green-500/10'
                                            : 'border-red-500/50 bg-red-500/10'
                                        }`}
                                >
                                    <div className="flex items-start gap-3">
                                        {result.type === 'success' ? (
                                            <CheckCircle2 className="w-6 h-6 text-green-400 flex-shrink-0" />
                                        ) : (
                                            <XCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
                                        )}
                                        <div>
                                            <p className={`font-semibold ${result.type === 'success' ? 'text-green-300' : 'text-red-300'}`}>
                                                {result.type === 'success' ? 'Başarılı!' : 'Hata!'}
                                            </p>
                                            <p className="text-sm text-gray-300 mt-1">{result.message}</p>
                                        </div>
                                    </div>
                                </GlassCard>
                            </motion.div>
                        )}
                    </form>
                </GlassCard>
            </motion.div>

            {/* Tip Card */}
            <motion.div variants={item}>
                <GlassCard variant="dark" className="border border-cyan-500/30">
                    <div className="flex items-start gap-3">
                        <Sparkles className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-1" />
                        <p className="text-sm text-gray-300">
                            <span className="font-semibold text-white">İpucu:</span> Tarama arka planda çalışır. Sonuçları <code className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300">outputs/</code> klasöründe bulabilirsiniz.
                        </p>
                    </div>
                </GlassCard>
            </motion.div>
        </motion.div>
    );
}
