'use client';

import { motion } from 'framer-motion';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Home, Database, Map, FileSpreadsheet, Zap } from 'lucide-react';

const Hyperspeed = dynamic(() => import('@/components/ui/Hyperspeed'), { ssr: false });

const features = [
    {
        icon: Database,
        title: 'Çoklu Platform',
        description: 'Emlakjet ve Hepsiemlak verilerini tek yerden toplayın',
    },
    {
        icon: Map,
        title: 'Harita Görünümü',
        description: 'İlçe bazlı interaktif harita ile verileri görselleştirin',
    },
    {
        icon: FileSpreadsheet,
        title: 'Excel Export',
        description: 'Tüm verileri tek tıkla Excel formatında indirin',
    },
    {
        icon: Zap,
        title: 'Hızlı Tarama',
        description: 'Gelişmiş algoritmalarla hızlı ve güvenilir veri toplama',
    },
];

export default function LandingPage() {
    return (
        <div className="relative min-h-screen overflow-hidden bg-black">
            {/* Arka Plan Efekti */}
            <div className="absolute inset-0 z-0">
                <Hyperspeed
                    effectOptions={{
                        onSpeedUp: () => {},
                        onSlowDown: () => {},
                        distortion: 'turbulentDistortion',
                        length: 400,
                        roadWidth: 10,
                        islandWidth: 2,
                        lanesPerRoad: 3,
                        fov: 90,
                        fovSpeedUp: 150,
                        speedUp: 2,
                        carLightsFade: 0.4,
                        totalSideLightSticks: 50,
                        lightPairsPerRoadWay: 70,
                        shoulderLinesWidthPercentage: 0.05,
                        brokenLinesWidthPercentage: 0.1,
                        brokenLinesLengthPercentage: 0.5,
                        lightStickWidth: [0.12, 0.5],
                        lightStickHeight: [1.3, 1.7],
                        movingAwaySpeed: [60, 80],
                        movingCloserSpeed: [-120, -160],
                        carLightsLength: [400 * 0.05, 400 * 0.15],
                        carLightsRadius: [0.05, 0.14],
                        carWidthPercentage: [0.3, 0.5],
                        carShiftX: [-0.2, 0.2],
                        carFloorSeparation: [0.05, 1],
                        colors: {
                            roadColor: 0x080808,
                            islandColor: 0x0a0a0a,
                            background: 0x000000,
                            shoulderLines: 0x131318,
                            brokenLines: 0x131318,
                            leftCars: [0x38bdf8, 0x0ea5e9, 0x0284c7],  // Gök mavisi
                            rightCars: [0x34d399, 0x10b981, 0x059669], // Zümrüt yeşili
                            sticks: 0x38bdf8,
                        }
                    }}
                />
            </div>

            {/* Gradyan Kaplama */}
            <div className="absolute inset-0 z-[1] bg-gradient-to-b from-black/60 via-transparent to-black/80" />

            {/* İçerik */}
            <div className="relative z-10 min-h-screen flex flex-col">
                {/* Üst Menü */}
                <header className="p-6 lg:p-8">
                    <nav className="max-w-7xl mx-auto flex items-center justify-between">
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.5 }}
                            className="flex items-center gap-3"
                        >
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-sky-500/20">
                                <Home className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-xl font-bold text-white">Emlak Scraper</span>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.5 }}
                            className="flex items-center gap-4"
                        >
                            <Link
                                href="/login"
                                className="px-4 py-2 text-gray-300 hover:text-white transition-colors font-medium"
                            >
                                Giriş Yap
                            </Link>
                            <Link
                                href="/register"
                                className="px-5 py-2.5 bg-gradient-to-r from-sky-500 to-emerald-500 hover:from-sky-600 hover:to-emerald-600 text-white font-semibold rounded-lg transition-all shadow-lg shadow-sky-500/25 hover:shadow-sky-500/40"
                            >
                                Kayıt Ol
                            </Link>
                        </motion.div>
                    </nav>
                </header>

                {/* Ana Bölüm */}
                <main className="flex-1 flex items-center justify-center px-6 lg:px-8">
                    <div className="max-w-5xl mx-auto text-center">
                        <motion.div
                            initial={{ opacity: 0, y: 30 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.7, delay: 0.2 }}
                        >
                            <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold mb-6 leading-tight bg-gradient-to-r from-sky-400 via-teal-400 via-emerald-400 to-sky-400 bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient">
                                Emlak Verilerini Hızla Toplayın
                            </h1>
                            <p className="text-lg sm:text-xl text-gray-400 mb-6 max-w-2xl mx-auto leading-relaxed">
                                Türkiye'nin en büyük emlak platformlarından veri toplayın,
                                analiz edin ve Excel'e aktarın. Profesyonel emlak araştırması için tek adres.
                            </p>
                        </motion.div>

                    </div>
                </main>

                {/* Özellikler Bölümü */}
                <section className="px-6 lg:px-8 pb-16 -mt-8">
                    <div className="max-w-6xl mx-auto">
                        <motion.div
                            initial={{ opacity: 0, y: 40 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.7, delay: 0.8 }}
                            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
                        >
                            {features.map((feature, index) => (
                                <motion.div
                                    key={feature.title}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5, delay: 0.9 + index * 0.1 }}
                                    className="group p-6 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-sky-500/30 hover:bg-white/10 transition-all"
                                >
                                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-sky-500/20 to-emerald-500/20 flex items-center justify-center mb-4 group-hover:from-sky-500/30 group-hover:to-emerald-500/30 transition-all">
                                        <feature.icon className="w-6 h-6 text-sky-400" />
                                    </div>
                                    <h3 className="text-lg font-semibold text-white mb-2">
                                        {feature.title}
                                    </h3>
                                    <p className="text-sm text-gray-400">
                                        {feature.description}
                                    </p>
                                </motion.div>
                            ))}
                        </motion.div>
                    </div>
                </section>

                {/* Alt Bilgi */}
                <footer className="px-6 lg:px-8 py-6 border-t border-white/5">
                    <div className="max-w-7xl mx-auto flex items-center justify-between text-sm text-gray-500">
                        <p>© 2026 Emlak Scraper. Tüm hakları saklıdır.</p>
                        <p>v2.0</p>
                    </div>
                </footer>
            </div>
        </div>
    );
}
