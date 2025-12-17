'use client';

import { GlassCard } from '@/components/ui/GlassCard';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, Zap, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';

const container = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.15,
        },
    },
};

const item = {
    hidden: { opacity: 0, scale: 0.9 },
    show: { opacity: 1, scale: 1 },
};

const platforms = [
    {
        id: 'emlakjet',
        name: 'EmlakJet',
        description: 'Türkiye\'nin önde gelen emlak platformu',
        features: ['Konut', 'Arsa', 'İşyeri', 'Turistik Tesis'],
        gradient: 'from-blue-500 to-cyan-500',
        neon: 'blue' as const,
        icon: '🔵',
    },
    {
        id: 'hepsiemlak',
        name: 'HepsiEmlak',
        description: 'Kapsamlı emlak ilan veritabanı',
        features: ['Konut', 'Arsa', 'İşyeri', 'Devremülk'],
        gradient: 'from-green-500 to-emerald-500',
        neon: 'purple' as const,
        icon: '🟢',
    },
];

export default function ScraperPage() {
    return (
        <motion.div
            className="space-y-6"
            variants={container}
            initial="hidden"
            animate="show"
        >
            {/* Header */}
            <motion.div variants={item} className="mb-8">
                <Link href="/">
                    <Button variant="ghost" className="mb-4 text-gray-300 hover:text-white">
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Dashboard
                    </Button>
                </Link>
                <h1 className="text-4xl font-bold gradient-text-neon mb-2">
                    Scraper
                </h1>
                <p className="text-gray-300 text-lg">
                    ⚡ Veri toplamak istediğiniz platformu seçin
                </p>
            </motion.div>

            {/* Platform Cards - Bento Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {platforms.map((platform, index) => (
                    <motion.div key={platform.id} variants={item}>
                        <Link href={`/scraper/${platform.id}`}>
                            <GlassCard
                                variant="strong"
                                neonBorder={platform.neon}
                                glow
                                className="h-full group relative overflow-hidden min-h-[300px]"
                            >
                                {/* Gradient overlay */}
                                <div className={`absolute inset-0 bg-gradient-to-br ${platform.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-500`} />

                                {/* Floating bg decoration */}
                                <div className={`absolute -right-10 -top-10 w-40 h-40 bg-gradient-to-br ${platform.gradient} rounded-full opacity-20 blur-3xl group-hover:scale-150 transition-transform duration-700`} />

                                <div className="relative h-full flex flex-col">
                                    {/* Header */}
                                    <div className="flex items-start justify-between mb-6">
                                        <div className="flex items-center gap-4">
                                            <div className="text-6xl group-hover:scale-110 transition-transform">
                                                {platform.icon}
                                            </div>
                                            <div>
                                                <h2 className="text-3xl font-bold text-white mb-1 group-hover:gradient-text-neon transition-all">
                                                    {platform.name}
                                                </h2>
                                                <p className="text-gray-400 text-sm">
                                                    {platform.description}
                                                </p>
                                            </div>
                                        </div>

                                        {index === 0 ? (
                                            <Sparkles className="w-6 h-6 text-blue-400 group-hover:rotate-12 transition-transform" />
                                        ) : (
                                            <Zap className="w-6 h-6 text-emerald-400 group-hover:rotate-12 transition-transform" />
                                        )}
                                    </div>

                                    {/* Features */}
                                    <div className="flex-1 mb-6">
                                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                                            Desteklenen Kategoriler
                                        </p>
                                        <div className="grid grid-cols-2 gap-2">
                                            {platform.features.map((feature) => (
                                                <div
                                                    key={feature}
                                                    className="px-3 py-2 rounded-lg glass-dark text-sm text-gray-300 hover:text-white transition-colors"
                                                >
                                                    {feature}
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Action */}
                                    <div className="flex items-center justify-between p-4 glass-dark rounded-xl">
                                        <span className="text-gray-400 text-sm">
                                            Taramaya Başla
                                        </span>
                                        <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-white group-hover:translate-x-2 transition-all" />
                                    </div>
                                </div>
                            </GlassCard>
                        </Link>
                    </motion.div>
                ))}
            </div>

            {/* Info Card */}
            <motion.div variants={item}>
                <GlassCard variant="dark" className="border-2 border-purple-500/30">
                    <div className="flex items-center gap-4">
                        <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                            <Sparkles className="w-6 h-6 text-purple-400" />
                        </div>
                        <div>
                            <p className="text-gray-300">
                                <span className="font-semibold text-white">Pro Tip:</span> Her platform için özel filtreler ve ayarlar mevcut. Şehir, kategori ve sayfa sayısını özelleştirin.
                            </p>
                        </div>
                    </div>
                </GlassCard>
            </motion.div>
        </motion.div>
    );
}
