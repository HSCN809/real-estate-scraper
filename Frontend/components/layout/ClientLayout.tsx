'use client';

import { Header } from '@/components/layout/Header';
import { ParticleBackground } from '@/components/ui/ParticleBackground';
import Aurora from '@/components/ui/Aurora';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { ProgressPanel } from '@/components/ui/ProgressModal';
import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';

// Public sayfalar - header olmadan tam ekran gösterilecek
const publicRoutes = ['/login', '/register', '/homepage'];

export function ClientLayout({ children }: { children: ReactNode }) {
    const pathname = usePathname();
    const isPublicPage = publicRoutes.includes(pathname);
    const isDashboard = pathname === '/';

    // Homepage için AuthGuard olmadan tam ekran
    if (pathname === '/homepage') {
        return <>{children}</>;
    }

    // Auth sayfaları için AuthGuard ile tam ekran (header yok)
    if (isPublicPage) {
        return <AuthGuard>{children}</AuthGuard>;
    }

    // Normal sayfalar için tam layout
    return (
        <AuthGuard>
            {/* Arka plan efektleri - Dashboard kendi arka planını kullanıyor */}
            {!isDashboard && (
                <>
                    {/* Parçacık Arka Planı */}
                    <div className="fixed inset-0" style={{ zIndex: 0 }}>
                        <ParticleBackground />
                    </div>

                    {/* Aurora Arka Planı */}
                    <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
                        <Aurora
                            colorStops={['#38bdf8', '#818cf8', '#34d399']}
                            amplitude={0.8}
                            blend={0.6}
                            speed={0.5}
                        />
                    </div>

                    {/* Soyut Dekorasyonlar */}
                    <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
                        <div className="abstract-circle" style={{
                            background: 'radial-gradient(circle, #38bdf8, transparent)',
                            top: '10%',
                            right: '10%',
                            opacity: 0.05
                        }} />
                        <div className="abstract-circle" style={{
                            background: 'radial-gradient(circle, #34d399, transparent)',
                            bottom: '20%',
                            left: '15%',
                            opacity: 0.05
                        }} />
                    </div>
                </>
            )}

            {/* Sayfa Konteyneri */}
            <div className="relative isolate">
                {/* Üst Menü */}
                <Header />

                {/* Ana İçerik Alanı */}
                <div className="min-h-screen relative z-10 pt-16">
                    <main className={isDashboard ? '' : 'p-4 lg:p-6 pt-8'}>
                        {children}
                    </main>
                </div>
            </div>
            {/* Global İlerleme Paneli */}
            <ProgressPanel />
        </AuthGuard>
    );
}
