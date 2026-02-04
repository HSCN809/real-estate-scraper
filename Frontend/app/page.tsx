'use client';

import { ArtCard } from '@/components/ui/ArtCard';
import BlurText from '@/components/ui/BlurText';
import CountUp from '@/components/ui/CountUp';
import SpotlightCard from '@/components/ui/SpotlightCard';
import { motion } from 'framer-motion';
import { Search, Database, TrendingUp, Clock, Sparkles, Zap, Activity } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0 },
};

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_scrapes: 0,
    total_listings: 0,
    this_week: 0,
    this_month: 0,
    last_scrape: '-'
  });

  useEffect(() => {
    import('@/lib/api').then(({ getStats }) => {
      getStats().then(setStats).catch(console.error);
    });
  }, []);

  return (
    <motion.section
      className="space-y-8 relative z-10"
      variants={container}
      initial="hidden"
      animate="show"
      aria-labelledby="dashboard-title"
    >
      {/* Artistic Header */}
      <motion.header variants={item}>
        <h1 id="dashboard-title" className="art-title gradient-art-pink mb-3">
          Dashboard
        </h1>
        <p className="text-xl text-gray-300">
          Veri toplama sürecinizi takip edin ve analiz edin.
        </p>
      </motion.header>

      {/* Stats Grid - Bold Artistic Layout */}
      <motion.section
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        variants={container}
        aria-label="İstatistikler"
      >
        {/* Large Featured Stat */}
        <motion.article variants={item} className="lg:col-span-2 lg:row-span-2">
          <ArtCard glowColor="pink" className="h-full">
            <div className="flex flex-col h-full justify-between">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-4 rounded-2xl bg-gradient-to-br from-pink-500/20 to-purple-500/20">
                      <Search className="w-10 h-10 text-pink-400" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-400 uppercase tracking-wider">
                        Toplam Tarama
                      </p>
                      <div className="text-7xl font-black gradient-art-pink mt-2" aria-label={`Toplam tarama sayısı: ${stats.total_scrapes}`}>
                        <CountUp to={stats.total_scrapes} duration={2} separator="." />
                      </div>
                    </div>
                  </div>
                </div>
                <Sparkles className="w-8 h-8 text-pink-400" aria-hidden="true" />
              </div>

              {/* Mini Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-gradient-to-br from-pink-500/10 to-transparent border border-pink-500/20">
                  <p className="text-xs text-gray-400 mb-1">Bu Ay</p>
                  <div className="text-2xl font-bold text-pink-400">
                    <CountUp to={stats.this_month} duration={1.5} delay={0.3} />
                  </div>
                </div>
                <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-transparent border border-purple-500/20">
                  <p className="text-xs text-gray-400 mb-1">Son 7 Gün</p>
                  <div className="text-2xl font-bold text-purple-400">
                    <CountUp to={stats.this_week} duration={1.5} delay={0.4} />
                  </div>
                </div>
              </div>
            </div>
          </ArtCard>
        </motion.article>

        {/* Small Stats with SpotlightCard */}
        <motion.article variants={item}>
          <SpotlightCard className="h-full" spotlightColor="rgba(56, 189, 248, 0.15)">
            <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 w-fit mb-4">
              <Database className="w-8 h-8 text-blue-400" aria-hidden="true" />
            </div>
            <p className="text-sm text-gray-400 mb-2">Toplam İlan</p>
            <div className="text-5xl font-black gradient-art-blue">
              <CountUp to={stats.total_listings} duration={2} separator="." delay={0.2} />
            </div>
          </SpotlightCard>
        </motion.article>

        <motion.article variants={item}>
          <SpotlightCard className="h-full" spotlightColor="rgba(168, 85, 247, 0.15)">
            <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 w-fit mb-4">
              <TrendingUp className="w-8 h-8 text-purple-400" aria-hidden="true" />
            </div>
            <p className="text-sm text-gray-400 mb-2">Bu Hafta</p>
            <div className="text-5xl font-black text-purple-400">
              <CountUp to={stats.this_week} duration={1.5} delay={0.3} />
            </div>
          </SpotlightCard>
        </motion.article>

        <motion.article variants={item} className="lg:col-span-2">
          <ArtCard glowColor="blue" className="h-full">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-gradient-to-br from-orange-500/20 to-yellow-500/20">
                  <Clock className="w-8 h-8 text-orange-400" aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm text-gray-400 mb-1">Son Tarama</p>
                  <time className="text-3xl font-bold gradient-art-warm">{stats.last_scrape}</time>
                </div>
              </div>
              <Activity className="w-16 h-16 text-gray-800" aria-hidden="true" />
            </div>
          </ArtCard>
        </motion.article>
      </motion.section>

      {/* Platform Cards - Creative Layout */}
      <motion.section variants={item} aria-labelledby="platform-section-title">
        <h2 id="platform-section-title" className="text-3xl font-black gradient-art-blue mb-6">
          Platform Seçimi
        </h2>
      </motion.section>

      <motion.nav
        className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        variants={container}
        aria-label="Platform seçimi"
      >
        {/* EmlakJet */}
        <motion.article variants={item}>
          <Link href="/scraper/emlakjet" aria-label="EmlakJet platformunda taramaya başla">
            <ArtCard glowColor="blue" className="group cursor-pointer">
              <div className="relative">
                {/* Decorative Element */}
                <div className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500" aria-hidden="true" />

                <div className="relative">
                  <header className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-4">
                      <span className="text-6xl" aria-hidden="true">🔵</span>
                      <div>
                        <h3 className="text-4xl font-black gradient-art-blue">
                          EmlakJet
                        </h3>
                        <p className="text-gray-400 mt-1">
                          Profesyonel veri toplama
                        </p>
                      </div>
                    </div>
                    <Sparkles className="w-8 h-8 text-blue-400 group-hover:rotate-12 transition-transform" aria-hidden="true" />
                  </header>

                  {/* Features */}
                  <ul className="flex flex-wrap gap-2 mb-4" aria-label="Desteklenen kategoriler">
                    {['Konut', 'Arsa', 'İşyeri', 'Turistik'].map((feature) => (
                      <li
                        key={feature}
                        className="px-4 py-2 rounded-full bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/30 text-sm font-semibold text-blue-300"
                      >
                        {feature}
                      </li>
                    ))}
                  </ul>

                  <footer className="flex items-center justify-between pt-4 border-t border-blue-500/20">
                    <span className="text-sm text-gray-400">Taramaya başla</span>
                    <span className="text-2xl group-hover:translate-x-2 transition-transform" aria-hidden="true">→</span>
                  </footer>
                </div>
              </div>
            </ArtCard>
          </Link>
        </motion.article>

        {/* HepsiEmlak */}
        <motion.article variants={item}>
          <Link href="/scraper/hepsiemlak" aria-label="HepsiEmlak platformunda taramaya başla">
            <ArtCard glowColor="pink" className="group cursor-pointer">
              <div className="relative">
                {/* Decorative Element */}
                <div className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-pink-500/20 to-purple-500/20 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500" aria-hidden="true" />

                <div className="relative">
                  <header className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-4">
                      <span className="text-6xl" aria-hidden="true">🟢</span>
                      <div>
                        <h3 className="text-4xl font-black gradient-art-pink">
                          HepsiEmlak
                        </h3>
                        <p className="text-gray-400 mt-1">
                          Kapsamlı veri analizi
                        </p>
                      </div>
                    </div>
                    <Zap className="w-8 h-8 text-pink-400 group-hover:rotate-12 transition-transform" aria-hidden="true" />
                  </header>

                  {/* Features */}
                  <ul className="flex flex-wrap gap-2 mb-4" aria-label="Desteklenen kategoriler">
                    {['Konut', 'Arsa', 'İşyeri', 'Devremülk'].map((feature) => (
                      <li
                        key={feature}
                        className="px-4 py-2 rounded-full bg-gradient-to-r from-pink-500/20 to-purple-500/20 border border-pink-500/30 text-sm font-semibold text-pink-300"
                      >
                        {feature}
                      </li>
                    ))}
                  </ul>

                  <footer className="flex items-center justify-between pt-4 border-t border-pink-500/20">
                    <span className="text-sm text-gray-400">Taramaya başla</span>
                    <span className="text-2xl group-hover:translate-x-2 transition-transform" aria-hidden="true">→</span>
                  </footer>
                </div>
              </div>
            </ArtCard>
          </Link>
        </motion.article>
      </motion.nav>
    </motion.section>
  );
}
