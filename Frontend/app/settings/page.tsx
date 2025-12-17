'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { useState, useEffect } from 'react';
import { healthCheck } from '@/lib/api';

export default function SettingsPage() {
    const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');

    useEffect(() => {
        const checkApi = async () => {
            const isOnline = await healthCheck();
            setApiStatus(isOnline ? 'online' : 'offline');
        };
        checkApi();
    }, []);

    return (
        <div className="space-y-6 max-w-2xl">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                    Ayarlar
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                    Uygulama ayarlarını yapılandırın
                </p>
            </div>

            {/* API Status */}
            <Card>
                <CardHeader>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                        API Durumu
                    </h2>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-3">
                        <div
                            className={`w-3 h-3 rounded-full ${apiStatus === 'checking'
                                    ? 'bg-yellow-500 animate-pulse'
                                    : apiStatus === 'online'
                                        ? 'bg-green-500'
                                        : 'bg-red-500'
                                }`}
                        />
                        <span className="text-gray-700 dark:text-gray-300">
                            {apiStatus === 'checking'
                                ? 'Kontrol ediliyor...'
                                : apiStatus === 'online'
                                    ? 'API çevrimiçi (localhost:8000)'
                                    : 'API çevrimdışı'}
                        </span>
                        {apiStatus === 'offline' && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                    setApiStatus('checking');
                                    healthCheck().then((isOnline) =>
                                        setApiStatus(isOnline ? 'online' : 'offline')
                                    );
                                }}
                            >
                                Tekrar Dene
                            </Button>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Scraper Settings */}
            <Card>
                <CardHeader>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                        Scraper Ayarları
                    </h2>
                </CardHeader>
                <CardContent className="space-y-4">
                    <Input
                        label="Varsayılan Sayfa Sayısı"
                        type="number"
                        defaultValue={5}
                        min={1}
                        max={50}
                    />
                    <Select
                        label="Çıktı Formatı"
                        options={[
                            { value: 'xlsx', label: 'Excel (.xlsx)' },
                            { value: 'csv', label: 'CSV (.csv)' },
                            { value: 'json', label: 'JSON (.json)' },
                        ]}
                    />
                    <div className="pt-4">
                        <Button disabled>Kaydet (Yakında)</Button>
                    </div>
                </CardContent>
            </Card>

            {/* About */}
            <Card>
                <CardHeader>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                        Hakkında
                    </h2>
                </CardHeader>
                <CardContent>
                    <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                        <p><strong>Versiyon:</strong> 2.0.0</p>
                        <p><strong>Framework:</strong> Next.js + FastAPI</p>
                        <p><strong>Platformlar:</strong> EmlakJet, HepsiEmlak</p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
