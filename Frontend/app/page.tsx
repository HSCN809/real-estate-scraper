'use client';

import CountUp from '@/components/ui/CountUp';
import { ResultsBackground } from '@/components/ui/ResultsBackground';
import { motion } from 'motion/react';
import {
  Search, Database, TrendingUp, Clock, Zap,
  Activity, BarChart3, Rocket, Eye
} from 'lucide-react';
import Link from 'next/link';
import { useState, useMemo } from 'react';
import type { ResultsOverview } from '@/types';
import { useAuth } from '@/contexts/AuthContext';
import { useScraping } from '@/contexts/ScrapingContext';
import { useResults, useResultsOverview, useStats } from '@/lib/api-hooks';
import {
  formatTimeAgo,
  getIstanbulHour,
  istanbulDayStart,
  formatIstanbulDate,
} from '@/lib/datetime';

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

function getGreeting(): string {
  const hour = getIstanbulHour();
  if (hour < 6) return 'İyi Geceler';
  if (hour < 12) return 'Günaydın';
  if (hour < 18) return 'İyi Günler';
  return 'İyi Akşamlar';
}


interface ChartDay { label: string; count: number; }

function getChartData(history: ResultsOverview['history']): ChartDay[] {
  const counts = new Map(history.map(({ date, count }) => [date, count]));
  const todayStart = istanbulDayStart(new Date());
  const days: ChartDay[] = [];

  for (let i = 6; i >= 0; i--) {
    const dayStart = new Date(todayStart.getTime() - i * 24 * 60 * 60 * 1000);
    const dayLabel = dayStart.toLocaleDateString('tr-TR', {
      weekday: 'short',
      timeZone: 'Europe/Istanbul',
    });
    const dayCount = counts.get(formatIstanbulDate(dayStart)) ?? 0;

    days.push({ label: dayLabel, count: dayCount });
  }

  return days;
}

export default function Dashboard() {
  const { user } = useAuth();
  const RECENT_ROW_HEIGHT = 74;
  const RECENT_VIEWPORT_HEIGHT = 320;
  const RECENT_OVERSCAN = 4;

  const stats = useStats().data ?? {
    total_scrapes: 0, total_listings: 0, this_week: 0, this_month: 0, last_scrape: '-',
  };
  const results = useResults({ limit: 50 }).data?.items ?? [];
  const overview = useResultsOverview().data;
  const [recentScrollTop, setRecentScrollTop] = useState(0);
  const { activeTasks, startTracking, showPanel } = useScraping();

  const chartData = useMemo(() => getChartData(overview?.history ?? []), [overview]);
  const maxChart = useMemo(() => Math.max(...chartData.map((d) => d.count), 1), [chartData]);
  const recentTotalHeight = results.length * RECENT_ROW_HEIGHT;
  const scrollOffset = Math.min(recentScrollTop, Math.max(0, recentTotalHeight - RECENT_VIEWPORT_HEIGHT));
  const recentStartIndex = Math.max(0, Math.floor(scrollOffset / RECENT_ROW_HEIGHT) - RECENT_OVERSCAN);
  const recentEndIndex = Math.min(
    results.length,
    Math.ceil((scrollOffset + RECENT_VIEWPORT_HEIGHT) / RECENT_ROW_HEIGHT) + RECENT_OVERSCAN
  );
  const visibleRecentResults = results.slice(recentStartIndex, recentEndIndex);

  return (
    <div className="relative min-h-screen bg-black -mt-16 pt-16">
      <ResultsBackground />

      {/* Koyu Kaplama */}
      <div className="fixed inset-0 z-[1] bg-gradient-to-b from-black/70 via-black/50 to-black/85 pointer-events-none" />

      {/* İçerik */}
      <div className="relative z-10 px-6 lg:px-8 py-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Hero - sayfa açılınca hemen görünür */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col md:flex-row md:items-end md:justify-between gap-6"
          >
            <div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight bg-gradient-to-r from-sky-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent">
                {user ? `${getGreeting()} ${user.username}` : getGreeting()}
              </h1>
              <p className="text-gray-400 mt-2">Veri toplama sürecinizi takip edin ve analiz edin.</p>
            </div>
            <div className="flex gap-3 shrink-0">
              <Link
                href="/scraper"
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-sky-500 to-emerald-500 hover:from-sky-600 hover:to-emerald-600 text-white font-semibold rounded-lg transition-all shadow-lg shadow-sky-500/25 hover:shadow-sky-500/40"
              >
                <Rocket className="w-4 h-4" />
                Taramaya Başla
              </Link>
              <Link
                href="/results"
                className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white font-medium rounded-lg border border-white/10 hover:border-sky-500/30 transition-all"
              >
                <Eye className="w-4 h-4" />
                Sonuçlar
              </Link>
            </div>
          </motion.div>

          {/* İstatistikler */}
          <motion.div
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
            variants={container}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.2 }}
          >
            {[
              { label: 'Toplam Tarama', value: stats.total_scrapes, icon: Search, borderHover: 'hover:border-sky-500/30', iconColor: 'text-sky-400' },
              { label: 'Toplam İlan', value: stats.total_listings, icon: Database, borderHover: 'hover:border-emerald-500/30', iconColor: 'text-emerald-400' },
              { label: 'Bu Ay', value: stats.this_month, icon: TrendingUp, borderHover: 'hover:border-sky-500/30', iconColor: 'text-sky-400' },
            ].map((stat, i) => (
              <motion.div key={stat.label} variants={item}>
                <div className={`group p-5 rounded-2xl bg-black/40 backdrop-blur-xl border border-white/10 ${stat.borderHover} hover:bg-black/50 transition-all`}>
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500/20 to-emerald-500/20 flex items-center justify-center mb-3 group-hover:from-sky-500/30 group-hover:to-emerald-500/30 transition-all">
                    <stat.icon className={`w-5 h-5 ${stat.iconColor}`} />
                  </div>
                  <p className="text-xs text-gray-500 mb-1">{stat.label}</p>
                  <div className="text-2xl font-bold text-white">
                    <CountUp to={stat.value} duration={2} separator="." delay={i * 0.15} />
                  </div>
                </div>
              </motion.div>
            ))}
            <motion.div variants={item}>
              <div className="group p-5 rounded-2xl bg-black/40 backdrop-blur-xl border border-white/10 hover:border-sky-500/30 hover:bg-black/50 transition-all">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500/20 to-emerald-500/20 flex items-center justify-center mb-3 group-hover:from-sky-500/30 group-hover:to-emerald-500/30 transition-all">
                  <Clock className="w-5 h-5 text-sky-400" />
                </div>
                <p className="text-xs text-gray-500 mb-1">Son Tarama</p>
                <time className="text-lg font-semibold text-white">{stats.last_scrape}</time>
              </div>
            </motion.div>
          </motion.div>

          {/* Grafik + Aktivite */}
          <motion.div
            className="grid grid-cols-1 lg:grid-cols-2 gap-4"
            variants={container}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.2 }}
          >
            {/* Grafik */}
            <motion.div variants={item}>
              <div className="h-full p-5 rounded-2xl bg-black/40 backdrop-blur-xl border border-white/10 hover:border-sky-500/30 transition-all">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500/20 to-emerald-500/20 flex items-center justify-center">
                    <BarChart3 className="w-4 h-4 text-sky-400" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-white">Tarama Aktivitesi</h2>
                    <p className="text-[10px] text-gray-500">Son 7 Gün</p>
                  </div>
                </div>
                <div className="flex items-end gap-2 h-40">
                  {chartData.map((day, i) => {
                    const heightPct = maxChart > 0 ? (day.count / maxChart) * 100 : 0;
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1.5">
                        <span className="text-[10px] text-gray-500 font-medium">
                          {day.count > 0 ? day.count.toLocaleString('tr-TR') : ''}
                        </span>
                        <motion.div
                          className="w-full rounded-lg bg-gradient-to-t from-sky-500 to-emerald-400 min-h-[4px]"
                          initial={{ height: 0 }}
                          whileInView={{ height: `${Math.max(heightPct, 3)}%` }}
                          viewport={{ once: true }}
                          transition={{ duration: 0.8, delay: 0.1 * i, ease: 'easeOut' }}
                        />
                        <span className="text-[10px] text-gray-600">{day.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </motion.div>

            {/* Son Aktiviteler */}
            <motion.div variants={item}>
              <div className="h-full p-5 rounded-2xl bg-black/40 backdrop-blur-xl border border-white/10 hover:border-sky-500/30 transition-all overflow-hidden">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500/20 to-emerald-500/20 flex items-center justify-center">
                    <Activity className="w-4 h-4 text-sky-400" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-white">Son Taramalar</h2>
                    <p className="text-[10px] text-gray-500">Son yapılan işlemler</p>
                  </div>
                </div>
                {results.length > 0 ? (
                  <div
                    className="h-[320px] overflow-y-auto pr-1"
                    onScroll={(e) => setRecentScrollTop(e.currentTarget.scrollTop)}
                  >
                    <div className="relative" style={{ height: `${recentTotalHeight}px` }}>
                      {visibleRecentResults.map((r, index) => {
                        const rowIndex = recentStartIndex + index;
                        const isSky = r.platform === 'emlakjet';

                        return (
                          <div
                            key={`${r.id}-${rowIndex}`}
                            className="absolute left-0 right-0"
                            style={{ top: `${rowIndex * RECENT_ROW_HEIGHT}px`, height: `${RECENT_ROW_HEIGHT - 10}px` }}
                          >
                            <div className="h-full flex items-center gap-3 px-3 rounded-xl bg-black/30 border border-white/5 hover:border-sky-500/20 transition-all">
                              <div className={`shrink-0 px-2.5 py-1 rounded-full text-[10px] font-bold ${isSky ? 'bg-sky-500/20 text-sky-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                                {isSky ? 'EmlakJet' : 'HepsiEmlak'}
                              </div>
                              <div className="flex-1 min-w-0 truncate">
                                <span className="text-sm text-gray-300">{r.category || '-'}</span>
                                {r.listing_type && <span className="text-sm text-gray-500"> · {r.listing_type}</span>}
                              </div>
                              <span className={`shrink-0 text-xs font-bold ${isSky ? 'text-sky-400' : 'text-emerald-400'}`}>
                                {(r.count || 0).toLocaleString('tr-TR')}
                              </span>
                              <span className="shrink-0 text-[10px] text-gray-600">{formatTimeAgo(r.date_iso || r.date)}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-14 text-gray-600">
                    <Activity className="w-10 h-10 mb-2 opacity-30" />
                    <p className="text-sm">Henüz tarama yapılmamış</p>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>

          {/* Aktif Görevler */}
          {activeTasks.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5 }}
            >
              <div className="p-5 rounded-2xl bg-black/40 backdrop-blur-xl border border-sky-500/20">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500/20 to-emerald-500/20 flex items-center justify-center">
                    <Zap className="w-4 h-4 text-sky-400 animate-pulse" />
                  </div>
                  <h2 className="text-sm font-semibold text-white">
                    Aktif Taramalar
                    <span className="ml-2 px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-400 text-xs font-bold">
                      {activeTasks.length}
                    </span>
                  </h2>
                </div>
                <div className="space-y-3">
                  {activeTasks.map((task, i) => (
                    <button
                      type="button"
                      key={task.task_id || i}
                      onClick={() => {
                        if (task.task_id) {
                          startTracking(task.task_id, task.platform);
                          showPanel();
                        }
                      }}
                      className="w-full text-left p-3 rounded-xl bg-black/30 border border-white/5 hover:border-sky-500/30 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-300">{task.message || 'Tarama devam ediyor...'}</span>
                        <span className="text-xs text-sky-400 font-bold">
                          {task.status === 'queued' ? 'Sırada' : task.progress > 0 ? `%${Math.round(task.progress)}` : 'Başlatılıyor...'}
                        </span>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
                        <motion.div
                          className="h-full rounded-full bg-gradient-to-r from-sky-500 to-emerald-500"
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.max(task.progress || 0, 2)}%` }}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                      {task.details && <p className="text-[10px] text-gray-600 mt-1.5">{task.details}</p>}
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
