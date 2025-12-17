'use client';

import { ArtCard } from '@/components/ui/ArtCard';
import { motion } from 'framer-motion';
import { FileText, Download, Eye, Sparkles, FileSpreadsheet, FileJson, Clock, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getResults } from '@/lib/api';
import { ScrapeResult } from '@/types';

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

export default function ResultsPage() {
    const [results, setResults] = useState<ScrapeResult[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchResults = async () => {
        try {
            setLoading(true);
            const data = await getResults();
            setResults(data);
            setError(null);
        } catch (err) {
            setError('Veriler alınırken bir hata oluştu');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchResults();
    }, []);

    return (
        <motion.div
            className="space-y-8 relative z-10"
            variants={container}
            initial="hidden"
            animate="show"
        >
            {/* Header */}
            <motion.div variants={item} className="flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-4 mb-3">
                        <FileText className="w-12 h-12 text-pink-500" />
                        <h1 className="art-title gradient-art-pink">
                            Sonuçlar
                        </h1>
                    </div>
                    <p className="text-xl text-gray-300 flex items-center gap-2">
                        Toplanan verileriniz burada listelenir <Sparkles className="w-5 h-5 text-yellow-500" />
                    </p>
                </div>

                <button
                    onClick={fetchResults}
                    disabled={loading}
                    className="p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all disabled:opacity-50"
                >
                    <RefreshCw className={`w-6 h-6 text-white ${loading ? 'animate-spin' : ''}`} />
                </button>
            </motion.div>

            {/* Loading State */}
            {loading && (
                <div className="flex items-center justify-center py-20">
                    <div className="w-10 h-10 border-4 border-pink-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
            )}

            {/* Error State */}
            {error && !loading && (
                <ArtCard glowColor="pink" className="text-center py-12">
                    <div className="flex flex-col items-center gap-4">
                        <div className="w-20 h-20 rounded-full bg-red-500/10 flex items-center justify-center">
                            <FileText className="w-10 h-10 text-red-500" />
                        </div>
                        <h3 className="text-xl font-bold text-white">Bir Hata Oluştu</h3>
                        <p className="text-red-400">{error}</p>
                        <button
                            onClick={fetchResults}
                            className="px-6 py-2 rounded-lg bg-red-500 text-white font-bold hover:bg-red-600 transition-colors"
                        >
                            Tekrar Dene
                        </button>
                    </div>
                </ArtCard>
            )}

            {/* Results Grid */}
            {!loading && !error && (
                <div className="grid grid-cols-1 gap-6">
                    {results.map((result, index) => (
                        <motion.div key={result.id} variants={item}>
                            <ArtCard
                                glowColor={index % 2 === 0 ? 'blue' : 'purple'}
                                className="group"
                            >
                                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">

                                    {/* Info Section */}
                                    <div className="flex-1">
                                        <div className="flex items-center gap-3 mb-2">
                                            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${result.platform === 'Emlakjet'
                                                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                                                    : 'bg-green-500/20 text-green-300 border border-green-500/30'
                                                }`}>
                                                {result.platform}
                                            </span>
                                            <span className="px-3 py-1 rounded-full bg-white/5 text-gray-300 border border-white/10 text-xs font-bold">
                                                {result.category}
                                            </span>
                                            <span className="flex items-center gap-1 text-xs text-gray-400">
                                                <Clock className="w-3 h-3" />
                                                {result.date}
                                            </span>
                                        </div>

                                        <h3 className="text-2xl font-bold text-white mb-2 group-hover:gradient-art-blue transition-all">
                                            {result.files[0].name.split('.')[0].toUpperCase()}
                                        </h3>

                                        {/* Count is mostly 0 for now until we read file content, hiding if 0 */}
                                        {result.count > 0 && (
                                            <p className="text-gray-400">
                                                Toplam <span className="text-white font-bold">{result.count}</span> ilan bulundu
                                            </p>
                                        )}
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-3 w-full md:w-auto">
                                        {result.files.map((file) => (
                                            <button
                                                key={file.name}
                                                className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-white/10 hover:border-white/30 transition-all hover:scale-105 ${file.type === 'excel'
                                                        ? 'bg-green-500/10 hover:bg-green-500/20 text-green-400'
                                                        : 'bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400'
                                                    }`}
                                                onClick={() => {
                                                    // TODO: Implement download logic
                                                    alert('İndirme başlatılıyor: ' + file.name);
                                                }}
                                            >
                                                {file.type === 'excel' ? (
                                                    <FileSpreadsheet className="w-5 h-5" />
                                                ) : (
                                                    <FileJson className="w-5 h-5" />
                                                )}
                                                <span className="font-bold text-sm uppercase">{file.type}</span>
                                                <Download className="w-4 h-4 ml-1 opacity-50" />
                                            </button>
                                        ))}

                                        <button className="p-3 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/30 hover:bg-blue-500/20 hover:scale-105 transition-all">
                                            <Eye className="w-5 h-5" />
                                        </button>
                                    </div>

                                </div>
                            </ArtCard>
                        </motion.div>
                    ))}

                    {/* Empty State */}
                    {results.length === 0 && (
                        <ArtCard glowColor="pink" className="text-center py-12">
                            <div className="flex flex-col items-center gap-4">
                                <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center">
                                    <FileText className="w-10 h-10 text-gray-600" />
                                </div>
                                <h3 className="text-xl font-bold text-white">Henüz Sonuç Yok</h3>
                                <p className="text-gray-400">Yeni bir tarama başlatarak veri toplamaya başlayın.</p>
                            </div>
                        </ArtCard>
                    )}
                </div>
            )}
        </motion.div>
    );
}
