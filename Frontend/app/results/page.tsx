'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { FileText, Download, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function ResultsPage() {
    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                    Sonuçlar
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                    Tarama sonuçlarınızı görüntüleyin ve yönetin
                </p>
            </div>

            {/* Results List */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                            Kayıtlı Dosyalar
                        </h2>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                        <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                        <h3 className="text-lg font-medium mb-2">Henüz sonuç yok</h3>
                        <p className="text-sm">
                            Tarama işlemi başlattığınızda sonuçlar burada görüntülenecek
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* Info Card */}
            <Card className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20">
                <CardContent>
                    <div className="flex items-start gap-3">
                        <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-800">
                            <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                            <h3 className="font-medium text-blue-900 dark:text-blue-100">
                                Sonuçlar Hakkında
                            </h3>
                            <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                                Tarama sonuçları <code className="px-1 py-0.5 rounded bg-blue-100 dark:bg-blue-800">Outputs/</code> klasörüne Excel formatında kaydedilir.
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
