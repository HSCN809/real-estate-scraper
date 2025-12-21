'use client';

import { ArtCard } from '@/components/ui/ArtCard';
import { motion } from 'framer-motion';
import {
    FileText,
    Download,
    Sparkles,
    FileSpreadsheet,
    FileJson,
    Clock,
    RefreshCw,
    Database,
    Search,
    Filter,
    CheckCircle2
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { getResults } from '@/lib/api';
import { ScrapeResult } from '@/types';

// Animation variants
const containerVariants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.1,
            delayChildren: 0.2
        },
    },
};

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
};

export default function ResultsPage() {
    const [results, setResults] = useState<ScrapeResult[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

    const fetchResults = async () => {
        try {
            setLoading(true);
            const data = await getResults();
            setResults(Array.isArray(data) ? data : []);
            setError(null);
        } catch (err) {
            setError('Veriler alınırken bir hata oluştu');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        fetchResults();
    }, []);

    if (!mounted) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <div className="w-10 h-10 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
            </div>
        );
    }

    // Derived stats
    const totalFiles = results.length;
    const totalRecords = results.reduce((acc, curr) => acc + (curr.count || 0), 0);

    return (
        <motion.div
            className="space-y-8 relative z-10 p-4 md:p-8 max-w-7xl mx-auto"
            variants={containerVariants}
            initial="hidden"
            animate="show"
        >
            {/* Header Section */}
            <motion.div variants={itemVariants} className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <h1 className="text-4xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-emerald-400 mb-2">
                        Veri Sonuçları
                    </h1>
                    <p className="text-gray-400 text-lg flex items-center gap-2">
                        Taranan ilan verileri ve raporlar
                        <Sparkles className="w-4 h-4 text-yellow-400" />
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="hidden md:flex items-center gap-4 mr-4 px-4 py-2 rounded-full bg-slate-800/50 border border-slate-700/50">
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                            <Database className="w-4 h-4 text-emerald-400" />
                            <span>{totalFiles} Dosya</span>
                        </div>
                        <div className="w-px h-4 bg-slate-700"></div>
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                            <FileText className="w-4 h-4 text-blue-400" />
                            <span>{totalRecords} İlan</span>
                        </div>
                    </div>

                    <button
                        onClick={fetchResults}
                        disabled={loading}
                        className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:bg-slate-700/50 hover:border-slate-600 transition-all disabled:opacity-50 group"
                        title="Yenile"
                    >
                        <RefreshCw className={`w-5 h-5 text-gray-300 group-hover:text-white transition-colors ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </motion.div>

            {/* Content Area */}
            <div className="min-h-[400px]">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                        <p className="text-gray-400 animate-pulse">Veriler yükleniyor...</p>
                    </div>
                ) : error ? (
                    <ArtCard glowColor="pink" className="text-center py-16 max-w-lg mx-auto">
                        <div className="flex flex-col items-center gap-6">
                            <div className="w-20 h-20 rounded-full bg-red-500/10 flex items-center justify-center ring-1 ring-red-500/20">
                                <FileText className="w-10 h-10 text-red-500" />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-white mb-2">Veri Alınamadı</h3>
                                <p className="text-gray-400">{error}</p>
                            </div>
                            <button
                                onClick={fetchResults}
                                className="px-8 py-3 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-all font-medium"
                            >
                                Tekrar Dene
                            </button>
                        </div>
                    </ArtCard>
                ) : results.length === 0 ? (
                    <motion.div variants={itemVariants}>
                        <ArtCard glowColor="blue" className="text-center py-20">
                            <div className="flex flex-col items-center gap-6 max-w-md mx-auto">
                                <div className="w-24 h-24 rounded-full bg-slate-800/50 flex items-center justify-center ring-1 ring-slate-700">
                                    <Search className="w-12 h-12 text-gray-600" />
                                </div>
                                <div>
                                    <h3 className="text-2xl font-bold text-white mb-3">Henüz Sonuç Yok</h3>
                                    <p className="text-gray-400 leading-relaxed">
                                        Şuan için listelenecek taranmış veri bulunmuyor. Yeni bir tarama başlatarak emlak verilerini toplamaya başlayabilirsiniz.
                                    </p>
                                </div>
                            </div>
                        </ArtCard>
                    </motion.div>
                ) : (
                    <motion.div
                        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                        variants={containerVariants}
                        initial="hidden"
                        animate="show"
                        key="results-grid"
                    >
                        {results.map((result, index) => (
                            <motion.div
                                key={result.id || index}
                                variants={itemVariants}
                                layout
                            >
                                <ArtCard
                                    glowColor={result.platform === 'Emlakjet' ? 'purple' : 'blue'}
                                    className="h-full flex flex-col hover:-translate-y-1 transition-transform duration-300"
                                >
                                    {/* Card Header */}
                                    <div className="flex items-start justify-between mb-4">
                                        <span className={`px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider border ${result.platform === 'Emlakjet'
                                                ? 'bg-purple-500/10 text-purple-300 border-purple-500/20'
                                                : 'bg-blue-500/10 text-blue-300 border-blue-500/20'
                                            }`}>
                                            {result.platform}
                                        </span>
                                        <div className="flex items-center gap-1.5 text-xs text-gray-500 bg-slate-900/50 px-2 py-1 rounded border border-slate-800">
                                            <Clock className="w-3 h-3" />
                                            {result.date}
                                        </div>
                                    </div>

                                    {/* Card Content */}
                                    <div className="flex-1">
                                        <div className="mb-4">
                                            <h3 className="text-lg font-bold text-white mb-2 line-clamp-2 leading-snug" title={result.files?.[0]?.name}>
                                                {result.files?.[0]?.name?.split('_').slice(0, 3).join(' ') || 'Bilinmeyen Dosya'}
                                            </h3>
                                            <p className="text-sm text-gray-400 flex items-center gap-2">
                                                <span className={`w-2 h-2 rounded-full ${result.status === 'completed' ? 'bg-emerald-500' : 'bg-yellow-500'}`}></span>
                                                {(result.count || 0) > 0 ? `${result.count} İlan Bulundu` : 'Sonuç Yok'}
                                            </p>
                                        </div>

                                        <div className="h-px w-full bg-gradient-to-r from-transparent via-slate-700 to-transparent my-4"></div>

                                        {/* Download Actions */}
                                        <div className="space-y-2">
                                            {result.files?.map((file, fIndex) => (
                                                <button
                                                    key={file.name || fIndex}
                                                    onClick={() => {
                                                        const link = document.createElement('a');
                                                        link.href = `/api/download?file=${file.name}`;
                                                        link.download = file.name;
                                                    }}
                                                    className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg border transition-all group/btn ${file.type === 'excel'
                                                            ? 'bg-emerald-500/5 border-emerald-500/20 hover:bg-emerald-500/10 hover:border-emerald-500/30'
                                                            : 'bg-amber-500/5 border-amber-500/20 hover:bg-amber-500/10 hover:border-amber-500/30'
                                                        }`}
                                                >
                                                    <div className="flex items-center gap-3">
                                                        {file.type === 'excel' ? (
                                                            <FileSpreadsheet className="w-4 h-4 text-emerald-400 group-hover/btn:scale-110 transition-transform" />
                                                        ) : (
                                                            <FileJson className="w-4 h-4 text-amber-400 group-hover/btn:scale-110 transition-transform" />
                                                        )}
                                                        <span className={`text-sm font-medium ${file.type === 'excel' ? 'text-emerald-300' : 'text-amber-300'
                                                            }`}>
                                                            {file.type === 'excel' ? 'Excel Raporu' : 'JSON Verisi'}
                                                        </span>
                                                    </div>
                                                    <Download className="w-4 h-4 text-gray-500 group-hover/btn:text-white transition-colors" />
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </ArtCard>
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </div>
        </motion.div>
    );
}
