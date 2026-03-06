'use client';

import { ArtCard } from '@/components/ui/ArtCard';
import { motion } from 'framer-motion';
import { Sparkles, Zap } from 'lucide-react';
import Link from 'next/link';
import dynamic from 'next/dynamic';

const FloatingLines = dynamic(() => import('@/components/ui/FloatingLines'), { ssr: false });

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
                <div className="max-w-7xl mx-auto">
                    <motion.section
                        className="space-y-8"
                        variants={container}
                        initial="hidden"
                        animate="show"
                        aria-labelledby="scraper-title"
                    >
                        {/* Başlık */}
                        <motion.header variants={item}>
                            <h1 id="scraper-title" className="text-4xl sm:text-5xl font-bold mb-3 bg-gradient-to-r from-sky-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent">
                                Platform Seçimi
                            </h1>
                            <p className="text-xl text-gray-400">
                                Veri toplamak istediğiniz platformu seçin ⚡
                            </p>
                        </motion.header>

                        {/* Platform Kartları */}
                        <nav className="grid grid-cols-1 gap-8" aria-label="Platform seçimi">
                            {platforms.map((platform, index) => (
                                <motion.article key={platform.id} variants={item}>
                                    <Link href={`/scraper/${platform.id}`} aria-label={`${platform.name} platformunda taramaya başla`}>
                                        <div className="backdrop-blur-xl bg-black/40 rounded-2xl p-6 border border-white/10 hover:border-sky-500/30 hover:bg-black/50 transition-all group cursor-pointer relative overflow-visible">
                                            {/* Dekoratif yüzen eleman */}
                                            <div className={`absolute -z-10 -inset-4 bg-gradient-to-r ${platform.gradient} opacity-0 group-hover:opacity-20 blur-3xl transition-opacity duration-500 rounded-3xl`} aria-hidden="true" />

                                            <div className="flex flex-col md:flex-row items-start md:items-center gap-8">
                                                {/* İkon Bölümü */}
                                                <figure className="relative" aria-hidden="true">
                                                    <span className="text-8xl md:text-9xl group-hover:scale-110 transition-transform duration-300 block">
                                                        {platform.icon}
                                                    </span>
                                                    <platform.Icon className={`absolute -top-4 -right-4 w-12 h-12 ${index === 0 ? 'text-blue-400' : 'text-pink-400'
                                                        } group-hover:rotate-12 transition-transform`} />
                                                </figure>

                                                {/* İçerik */}
                                                <div className="flex-1">
                                                    <h2 className={`text-5xl md:text-6xl font-black mb-3 ${index === 0 ? 'gradient-art-blue' : 'gradient-art-pink'
                                                        }`}>
                                                        {platform.name}
                                                    </h2>
                                                    <p className="text-lg text-gray-400 mb-6">
                                                        {platform.tagline}
                                                    </p>

                                                    {/* Özellik Listesi */}
                                                    <ul className="grid grid-cols-2 md:grid-cols-4 gap-3" aria-label={`${platform.name} desteklenen kategoriler`}>
                                                        {platform.features.map((feature) => (
                                                            <li
                                                                key={feature}
                                                                className="p-3 rounded-xl bg-black/30 border border-white/10 hover:border-sky-500/30 text-center transition-transform hover:scale-105"
                                                            >
                                                                <span className="font-bold text-sm text-gray-300">
                                                                    {feature}
                                                                </span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>

                                                {/* Ok İşareti */}
                                                <span className="text-6xl opacity-50 group-hover:opacity-100 group-hover:translate-x-4 transition-all duration-300" aria-hidden="true">
                                                    →
                                                </span>
                                            </div>
                                        </div>
                                    </Link>
                                </motion.article>
                            ))}
                        </nav>

                        {/* Bilgi Kartı */}
                        <motion.aside variants={item} aria-label="İpucu">
                            <div className="backdrop-blur-xl bg-black/40 rounded-2xl p-6 border border-white/10 hover:border-sky-500/30 hover:bg-black/50 transition-all">
                                <div className="flex items-start gap-4">
                                    <Sparkles className="w-8 h-8 text-sky-400 flex-shrink-0" aria-hidden="true" />
                                    <div>
                                        <h3 className="text-xl font-bold text-white mb-2">💡 İpucu</h3>
                                        <p className="text-gray-300">
                                            Her platform için özelleştirilmiş filtreler mevcut. Şehir, kategori ve sayfa sayısını kolayca ayarlayabilirsiniz.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </motion.aside>
                    </motion.section>
                </div>
            </div>
        </div>
    );
}
