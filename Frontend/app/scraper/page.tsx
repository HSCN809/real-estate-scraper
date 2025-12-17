'use client';

import { ArtCard } from '@/components/ui/ArtCard';
import { motion } from 'framer-motion';
import { Sparkles, Zap } from 'lucide-react';
import Link from 'next/link';

const container = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.2 },
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
        icon: '🔵',
        gradient: 'from-blue-500 to-cyan-500',
        glowColor: 'blue' as const,
        features: ['Konut', 'Arsa', 'İşyeri', 'Turistik Tesis'],
        tagline: 'Profesyonel veri toplama aracı',
        Icon: Sparkles,
    },
    {
        id: 'hepsiemlak',
        name: 'HepsiEmlak',
        icon: '🟢',
        gradient: 'from-pink-500 to-purple-500',
        glowColor: 'pink' as const,
        features: ['Konut', 'Arsa', 'İşyeri', 'Devremülk'],
        tagline: 'Profesyonel Veri Toplama Aracı',
        Icon: Zap,
    },
];

export default function ScraperPage() {
    return (
        <motion.div
            className="space-y-8 relative z-10"
            variants={container}
            initial="hidden"
            animate="show"
        >
            {/* Header */}
            <motion.div variants={item}>
                <h1 className="art-title gradient-art-blue mb-3">
                    Platform Seçimi
                </h1>
                <p className="text-xl text-gray-300">
                    Veri toplamak istediğiniz platformu seçin ⚡
                </p>
            </motion.div>

            {/* Platform Cards */}
            <div className="grid grid-cols-1 gap-8">
                {platforms.map((platform, index) => (
                    <motion.div key={platform.id} variants={item}>
                        <Link href={`/scraper/${platform.id}`}>
                            <ArtCard glowColor={platform.glowColor} className="group cursor-pointer relative overflow-visible">
                                {/* Decorative floating element */}
                                <div className={`absolute -z-10 -inset-4 bg-gradient-to-r ${platform.gradient} opacity-0 group-hover:opacity-20 blur-3xl transition-opacity duration-500 rounded-3xl`} />

                                <div className="flex flex-col md:flex-row items-start md:items-center gap-8">
                                    {/* Icon Section */}
                                    <div className="relative">
                                        <div className="text-8xl md:text-9xl group-hover:scale-110 transition-transform duration-300">
                                            {platform.icon}
                                        </div>
                                        <platform.Icon className={`absolute -top-4 -right-4 w-12 h-12 ${index === 0 ? 'text-blue-400' : 'text-pink-400'
                                            } group-hover:rotate-12 transition-transform`} />
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1">
                                        <h2 className={`text-5xl md:text-6xl font-black mb-3 ${index === 0 ? 'gradient-art-blue' : 'gradient-art-pink'
                                            }`}>
                                            {platform.name}
                                        </h2>
                                        <p className="text-lg text-gray-400 mb-6">
                                            {platform.tagline}
                                        </p>

                                        {/* Features Grid */}
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                            {platform.features.map((feature, idx) => (
                                                <div
                                                    key={feature}
                                                    className={`p-3 rounded-xl bg-gradient-to-br ${platform.gradient} bg-opacity-10 border ${index === 0 ? 'border-blue-500/30' : 'border-pink-500/30'
                                                        } text-center transition-transform hover:scale-105`}
                                                >
                                                    <span className={`font-bold text-sm ${index === 0 ? 'text-blue-300' : 'text-pink-300'
                                                        }`}>
                                                        {feature}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Arrow */}
                                    <div className="text-6xl opacity-50 group-hover:opacity-100 group-hover:translate-x-4 transition-all duration-300">
                                        →
                                    </div>
                                </div>
                            </ArtCard>
                        </Link>
                    </motion.div>
                ))}
            </div>

            {/* Info Card */}
            <motion.div variants={item}>
                <ArtCard glowColor="purple">
                    <div className="flex items-start gap-4">
                        <Sparkles className="w-8 h-8 text-purple-400 flex-shrink-0" />
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">💡 İpucu</h3>
                            <p className="text-gray-300">
                                Her platform için özelleştirilmiş filtreler mevcut. Şehir, kategori ve sayfa sayısını kolayca ayarlayabilirsiniz.
                            </p>
                        </div>
                    </div>
                </ArtCard>
            </motion.div>
        </motion.div>
    );
}
