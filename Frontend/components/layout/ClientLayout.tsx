'use client';

import Header from '@/components/layout/Header';
import dynamic from 'next/dynamic';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { ProgressPanel } from '@/components/ui/ProgressModal';
import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';

// Lazy load background effects for better initial load performance
const ParticleBackground = dynamic(() => import('@/components/ui/ParticleBackground'), {
    ssr: false
});

const Aurora = dynamic(() => import('@/components/ui/Aurora'), {
    ssr: false
});

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
            {/* Arka planlar kaldırıldı - Sadece FloatingLines kullanılıyor */}
            {/* ParticleBackground, Aurora ve soyut dekorasyonlar silindi */}

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
