'use client';

import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { motion } from 'framer-motion';
import {
  Search,
  Database,
  TrendingUp,
  Clock,
  ArrowRight,
  Sparkles,
  Zap,
  Activity
} from 'lucide-react';
import Link from 'next/link';

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
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function Dashboard() {
  return (
    <motion.div
      className="space-y-6"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {/* Header */}
      <motion.div variants={item} className="mb-8">
        <h1 className="text-4xl font-bold gradient-text-neon mb-2">
          Dashboard
        </h1>
        <p className="text-gray-300 text-lg">
          ✨ Emlak verisi toplama merkezinize hoş geldiniz
        </p>
      </motion.div>

      {/* Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 auto-rows-[180px]">
        {/* Large Stat Card - Toplam Tarama */}
        <motion.div variants={item} className="lg:col-span-2 lg:row-span-2">
          <GlassCard
            variant="strong"
            neonBorder="purple"
            glow
            className="h-full group relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

            <div className="relative h-full flex flex-col">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 neon-border-purple">
                  <Search className="w-8 h-8 text-purple-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-400 uppercase tracking-wide">
                    Toplam Tarama
                  </p>
                  <h2 className="text-5xl font-bold gradient-text">0</h2>
                </div>
              </div>

              <div className="flex-1 flex items-end">
                <div className="w-full bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-lg p-4 backdrop-blur-sm">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-300">Bu Ay</span>
                    <span className="text-purple-400 font-semibold">0</span>
                  </div>
                  <div className="flex items-center justify-between text-sm mt-2">
                    <span className="text-gray-300">Son 7 Gün</span>
                    <span className="text-pink-400 font-semibold">0</span>
                  </div>
                </div>
              </div>
            </div>
          </GlassCard>
        </motion.div>

        {/* Small Stat - Bulunan İlan */}
        <motion.div variants={item}>
          <GlassCard
            variant="default"
            neonBorder="blue"
            className="h-full"
          >
            <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 w-fit mb-3">
              <Database className="w-6 h-6 text-blue-400" />
            </div>
            <p className="text-sm text-gray-400 mb-1">Bulunan İlan</p>
            <h3 className="text-3xl font-bold text-white">0</h3>
          </GlassCard>
        </motion.div>

        {/* Small Stat - Bu Hafta */}
        <motion.div variants={item}>
          <GlassCard
            variant="default"
            neonBorder="pink"
            className="h-full relative overflow-hidden float-animation"
          >
            <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-pink-500/20 to-purple-500/20 rounded-full blur-2xl" />

            <div className="relative">
              <div className="p-2 rounded-xl bg-gradient-to-br from-pink-500/20 to-purple-500/20 w-fit mb-3">
                <TrendingUp className="w-6 h-6 text-pink-400" />
              </div>
              <p className="text-sm text-gray-400 mb-1">Bu Hafta</p>
              <h3 className="text-3xl font-bold text-white">0</h3>
            </div>
          </GlassCard>
        </motion.div>

        {/* Medium - Son Tarama */}
        <motion.div variants={item} className="lg:col-span-2">
          <GlassCard
            variant="dark"
            className="h-full flex items-center justify-between"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-gradient-to-br from-orange-500/20 to-yellow-500/20">
                <Clock className="w-7 h-7 text-orange-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">Son Tarama</p>
                <p className="text-2xl font-semibold text-white">-</p>
              </div>
            </div>
            <Activity className="w-12 h-12 text-gray-700" />
          </GlassCard>
        </motion.div>

        {/* Platform Cards - EmlakJet */}
        <motion.div variants={item} className="lg:col-span-2 lg:row-span-1">
          <Link href="/scraper/emlakjet">
            <GlassCard
              variant="strong"
              neonBorder="blue"
              className="h-full group relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/0 to-blue-500/10 group-hover:from-blue-500/10 group-hover:to-blue-500/20 transition-all duration-500" />

              <div className="relative flex items-center justify-between h-full">
                <div className="flex items-center gap-4">
                  <div className="text-5xl">🔵</div>
                  <div>
                    <h3 className="text-2xl font-bold text-white mb-1">
                      EmlakJet
                    </h3>
                    <p className="text-sm text-gray-400">
                      Emlak ilanları toplayın
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-blue-400 group-hover:translate-x-2 transition-transform">
                  <Sparkles className="w-5 h-5" />
                  <ArrowRight className="w-6 h-6" />
                </div>
              </div>
            </GlassCard>
          </Link>
        </motion.div>

        {/* Platform Cards - HepsiEmlak */}
        <motion.div variants={item} className="lg:col-span-2 lg:row-span-1">
          <Link href="/scraper/hepsiemlak">
            <GlassCard
              variant="strong"
              neonBorder="purple"
              className="h-full group relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-green-500/0 to-emerald-500/10 group-hover:from-green-500/10 group-hover:to-emerald-500/20 transition-all duration-500" />

              <div className="relative flex items-center justify-between h-full">
                <div className="flex items-center gap-4">
                  <div className="text-5xl">🟢</div>
                  <div>
                    <h3 className="text-2xl font-bold text-white mb-1">
                      HepsiEmlak
                    </h3>
                    <p className="text-sm text-gray-400">
                      Kapsamlı ilan veritabanı
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-emerald-400 group-hover:translate-x-2 transition-transform">
                  <Zap className="w-5 h-5" />
                  <ArrowRight className="w-6 h-6" />
                </div>
              </div>
            </GlassCard>
          </Link>
        </motion.div>
      </div>

      {/* Info Banner */}
      <motion.div variants={item}>
        <GlassCard variant="dark" className="border-2 border-cyan-500/30">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
              <Sparkles className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white mb-1">
                Yeni Tasarım! 🎨
              </h3>
              <p className="text-gray-400 text-sm">
                Bento Grid + Glassmorphism tasarımı ile modern ve şık bir deneyim.
              </p>
            </div>
          </div>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
