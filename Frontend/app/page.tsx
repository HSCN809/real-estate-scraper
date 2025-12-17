'use client';

import { ArtCard } from '@/components/ui/ArtCard';
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
    <motion.div
      className="space-y-8 relative z-10"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {/* Artistic Header */}
      <motion.div variants={item}>
        <h1 className="art-title gradient-art-pink mb-3">
          EMLAK SCRAPER
        </h1>
        <p className="text-xl text-gray-300">
          Veri toplama sürecinizi sanat eserine dönüştürün ✨
        </p>
      </motion.div>

      {/* Stats Grid - Bold Artistic Layout */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        variants={container}
      >
        {/* Large Featured Stat */}
        <motion.div variants={item} className="lg:col-span-2 lg:row-span-2">
          <ArtCard glowColor="pink" className="h-full">
            <div className="flex flex-col h-full justify-between">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-4 rounded-2xl bg-gradient-to-br from-pink-500/20 to-purple-500/20">
                      <Search className="w-10 h-10 text-pink-400" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-400 uppercase tracking-wider">
                        Toplam Tarama
                      </p>
                      <h2 className="text-7xl font-black gradient-art-pink mt-2">{stats.total_scrapes}</h2>
                    </div>
                  </div>
                </div>
                <Sparkles className="w-8 h-8 text-pink-400" />
              </div>

              {/* Mini Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-gradient-to-br from-pink-500/10 to-transparent border border-pink-500/20">
                  <p className="text-xs text-gray-400 mb-1">Bu Ay</p>
                  <p className="text-2xl font-bold text-pink-400">{stats.this_month}</p>
                </div>
                <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-transparent border border-purple-500/20">
                  <p className="text-xs text-gray-400 mb-1">Son 7 Gün</p>
                  <p className="text-2xl font-bold text-purple-400">{stats.this_week}</p>
                </div>
              </div>
            </div>
          </ArtCard>
        </motion.div>

        {/* Small Stats */}
        <motion.div variants={item}>
          <ArtCard glowColor="blue" className="h-full">
            <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 w-fit mb-4">
              <Database className="w-8 h-8 text-blue-400" />
            </div>
            <p className="text-sm text-gray-400 mb-2">Toplam İlan</p>
            <h3 className="text-5xl font-black gradient-art-blue">{stats.total_listings}</h3>
          </ArtCard>
        </motion.div>

        <motion.div variants={item}>
          <ArtCard glowColor="purple" className="h-full">
            <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 w-fit mb-4">
              <TrendingUp className="w-8 h-8 text-purple-400" />
            </div>
            <p className="text-sm text-gray-400 mb-2">Bu Hafta</p>
            <h3 className="text-5xl font-black text-purple-400">{stats.this_week}</h3>
          </ArtCard>
        </motion.div>

        <motion.div variants={item} className="lg:col-span-2">
          <ArtCard glowColor="blue" className="h-full">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-gradient-to-br from-orange-500/20 to-yellow-500/20">
                  <Clock className="w-8 h-8 text-orange-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-400 mb-1">Son Tarama</p>
                  <p className="text-3xl font-bold gradient-art-warm">{stats.last_scrape}</p>
                </div>
              </div>
              <Activity className="w-16 h-16 text-gray-800" />
            </div>
          </ArtCard>
        </motion.div>
      </motion.div>

      {/* Platform Cards - Creative Layout */}
      <motion.div variants={item}>
        <h2 className="text-3xl font-black gradient-art-blue mb-6">
          Platform Seçimi
        </h2>
      </motion.div>

      <motion.div
        className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        variants={container}
      >
        {/* EmlakJet */}
        <motion.div variants={item}>
          <Link href="/scraper/emlakjet">
            <ArtCard glowColor="blue" className="group cursor-pointer">
              <div className="relative">
                {/* Decorative Element */}
                <div className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500" />

                <div className="relative">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-4">
                      <div className="text-6xl">🔵</div>
                      <div>
                        <h3 className="text-4xl font-black gradient-art-blue">
                          EmlakJet
                        </h3>
                        <p className="text-gray-400 mt-1">
                          Profesyonel veri toplama
                        </p>
                      </div>
                    </div>
                    <Sparkles className="w-8 h-8 text-blue-400 group-hover:rotate-12 transition-transform" />
                  </div>

                  {/* Features */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {['Konut', 'Arsa', 'İşyeri', 'Turistik'].map((feature) => (
                      <span
                        key={feature}
                        className="px-4 py-2 rounded-full bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/30 text-sm font-semibold text-blue-300"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-blue-500/20">
                    <span className="text-sm text-gray-400">Taramaya başla</span>
                    <span className="text-2xl group-hover:translate-x-2 transition-transform">→</span>
                  </div>
                </div>
              </div>
            </ArtCard>
          </Link>
        </motion.div>

        {/* HepsiEmlak */}
        <motion.div variants={item}>
          <Link href="/scraper/hepsiemlak">
            <ArtCard glowColor="pink" className="group cursor-pointer">
              <div className="relative">
                {/* Decorative Element */}
                <div className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-pink-500/20 to-purple-500/20 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500" />

                <div className="relative">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-4">
                      <div className="text-6xl">🟢</div>
                      <div>
                        <h3 className="text-4xl font-black gradient-art-pink">
                          HepsiEmlak
                        </h3>
                        <p className="text-gray-400 mt-1">
                          Kapsamlı veri analizi
                        </p>
                      </div>
                    </div>
                    <Zap className="w-8 h-8 text-pink-400 group-hover:rotate-12 transition-transform" />
                  </div>

                  {/* Features */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {['Konut', 'Arsa', 'İşyeri', 'Devremülk'].map((feature) => (
                      <span
                        key={feature}
                        className="px-4 py-2 rounded-full bg-gradient-to-r from-pink-500/20 to-purple-500/20 border border-pink-500/30 text-sm font-semibold text-pink-300"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-pink-500/20">
                    <span className="text-sm text-gray-400">Taramaya başla</span>
                    <span className="text-2xl group-hover:translate-x-2 transition-transform">→</span>
                  </div>
                </div>
              </div>
            </ArtCard>
          </Link>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}
