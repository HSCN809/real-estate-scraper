'use client';

import { ArtCard } from '@/components/ui/ArtCard';
import { motion } from 'framer-motion';
import { Settings, Server, Database, Save, RotateCcw, Volume2, Moon } from 'lucide-react';
import { useState, useEffect } from 'react';
import { healthCheck } from '@/lib/api';

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

export default function SettingsPage() {
    const [apiStatus, setApiStatus] = useState<'online' | 'offline'>('offline');
    const [isChecking, setIsChecking] = useState(false);
    const [soundEnabled, setSoundEnabled] = useState(true);
    const [autoDownload, setAutoDownload] = useState(true);

    const checkStatus = async () => {
        setIsChecking(true);
        try {
            const isHealthy = await healthCheck();
            setApiStatus(isHealthy ? 'online' : 'offline');
        } catch {
            setApiStatus('offline');
        } finally {
            setIsChecking(false);
        }
    };

    useEffect(() => {
        checkStatus();
    }, []);

    return (
        <motion.div
            className="space-y-8 relative z-10"
            variants={container}
            initial="hidden"
            animate="show"
        >
            {/* Header */}
            <motion.div variants={item}>
                <div className="flex items-center gap-4 mb-3">
                    <Settings className="w-12 h-12 text-purple-500 animate-spin-slow" />
                    <h1 className="art-title gradient-art-pink">
                        Ayarlar
                    </h1>
                </div>
                <p className="text-xl text-gray-300">
                    Sistem yapılandırması ve tercihler ⚙️
                </p>
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* System Status */}
                <motion.div variants={item}>
                    <ArtCard glowColor="blue" className="h-full">
                        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                            <Server className="w-6 h-6 text-blue-400" />
                            Sistem Durumu
                        </h2>

                        <div className="space-y-4">
                            <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className={`w-3 h-3 rounded-full ${apiStatus === 'online' ? 'bg-green-500 shadow-[0_0_10px_#22c55e]' : 'bg-red-500'}`} />
                                    <span className="font-medium text-gray-200">API Bağlantısı</span>
                                </div>
                                <span className={`text-sm font-bold ${apiStatus === 'online' ? 'text-green-400' : 'text-red-400'}`}>
                                    {isChecking ? 'KONTROL EDİLİYOR...' : (apiStatus === 'online' ? 'ONLINE' : 'OFFLINE')}
                                </span>
                            </div>

                            <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Database className="w-5 h-5 text-purple-400" />
                                    <span className="font-medium text-gray-200">Veritabanı</span>
                                </div>
                                <span className="text-sm font-bold text-green-400">BAĞLI</span>
                            </div>

                            <div className="mt-6 pt-6 border-t border-white/10">
                                <button
                                    onClick={checkStatus}
                                    disabled={isChecking}
                                    className="w-full py-3 rounded-xl bg-blue-500/20 text-blue-300 border border-blue-500/30 hover:bg-blue-500/30 font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    <RotateCcw className={`w-4 h-4 ${isChecking ? 'animate-spin' : ''}`} />
                                    Bağlantıyı Yenile
                                </button>
                            </div>
                        </div>
                    </ArtCard>
                </motion.div>

                {/* Preferences */}
                <motion.div variants={item}>
                    <ArtCard glowColor="purple" className="h-full">
                        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                            <Settings className="w-6 h-6 text-purple-400" />
                            Tercihler
                        </h2>

                        <div className="space-y-6">
                            {/* Sound Toggle */}
                            <div className="flex items-center justify-between p-2">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 rounded-lg bg-pink-500/20">
                                        <Volume2 className="w-6 h-6 text-pink-400" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-white">Bildirim Sesleri</h3>
                                        <p className="text-sm text-gray-400">İşlem tamamlandığında ses çal</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setSoundEnabled(!soundEnabled)}
                                    className={`w-14 h-8 rounded-full transition-all relative ${soundEnabled ? 'bg-purple-600 shadow-[0_0_15px_rgba(147,51,234,0.5)]' : 'bg-gray-700'
                                        }`}
                                >
                                    <div className={`absolute top-1 w-6 h-6 rounded-full bg-white transition-all ${soundEnabled ? 'left-7' : 'left-1'
                                        }`} />
                                </button>
                            </div>

                            {/* Auto Download Toggle */}
                            <div className="flex items-center justify-between p-2">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 rounded-lg bg-orange-500/20">
                                        <Database className="w-6 h-6 text-orange-400" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-white">Otomatik İndirme</h3>
                                        <p className="text-sm text-gray-400">Tarama bitince Excel'i indir</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setAutoDownload(!autoDownload)}
                                    className={`w-14 h-8 rounded-full transition-all relative ${autoDownload ? 'bg-orange-600 shadow-[0_0_15px_rgba(234,88,12,0.5)]' : 'bg-gray-700'
                                        }`}
                                >
                                    <div className={`absolute top-1 w-6 h-6 rounded-full bg-white transition-all ${autoDownload ? 'left-7' : 'left-1'
                                        }`} />
                                </button>
                            </div>

                            <div className="mt-8 pt-6 border-t border-white/10 flex justify-end">
                                <button className="px-8 py-3 rounded-xl bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold shadow-lg hover:shadow-pink-500/25 hover:scale-105 transition-all flex items-center gap-2">
                                    <Save className="w-5 h-5" />
                                    Kaydet
                                </button>
                            </div>
                        </div>
                    </ArtCard>
                </motion.div>
            </div>
        </motion.div>
    );
}
