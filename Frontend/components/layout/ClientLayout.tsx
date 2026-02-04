'use client';

import { SidebarProvider, useSidebar } from '@/components/layout/SidebarContext';
import { Sidebar } from '@/components/layout/Sidebar';
import { ParticleBackground } from '@/components/ui/ParticleBackground';
import Aurora from '@/components/ui/Aurora';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { cn } from '@/lib/utils';
import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';

// Public sayfalar - sidebar olmadan tam ekran gösterilecek
const publicRoutes = ['/login', '/register', '/homepage'];

function MainContent({ children }: { children: ReactNode }) {
    const { isCollapsed } = useSidebar();

    return (
        <div
            className={cn(
                'transition-all duration-300 min-h-screen relative z-10',
                isCollapsed ? 'lg:pl-20' : 'lg:pl-64'
            )}
        >
            <main className="p-4 lg:p-6 pt-8">
                {children}
            </main>
        </div>
    );
}

export function ClientLayout({ children }: { children: ReactNode }) {
    const pathname = usePathname();
    const isPublicPage = publicRoutes.includes(pathname);

    // Homepage için AuthGuard olmadan tam ekran
    if (pathname === '/homepage') {
        return <>{children}</>;
    }

    // Auth sayfaları için AuthGuard ile tam ekran (sidebar yok)
    if (isPublicPage) {
        return <AuthGuard>{children}</AuthGuard>;
    }

    // Normal sayfalar için tam layout
    return (
        <AuthGuard>
            <SidebarProvider>
                {/* Particle Background - Fixed at bottom layer */}
                <div className="fixed inset-0" style={{ zIndex: 0 }}>
                    <ParticleBackground />
                </div>

                {/* Aurora Background - Layer 0.5 */}
                <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
                    <Aurora
                        colorStops={['#38bdf8', '#818cf8', '#34d399']}
                        amplitude={0.8}
                        blend={0.6}
                        speed={0.5}
                    />
                </div>

                {/* Abstract Decorations - Layer 1 */}
                <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
                    <div className="abstract-circle" style={{
                        background: 'radial-gradient(circle, #38bdf8, transparent)', // Sky Blue
                        top: '10%',
                        right: '10%',
                        opacity: 0.05
                    }} />
                    <div className="abstract-circle" style={{
                        background: 'radial-gradient(circle, #34d399, transparent)', // Emerald Green
                        bottom: '20%',
                        left: '15%',
                        opacity: 0.05
                    }} />
                    {/* Square removed consistent with corporate theme */}
                </div>

                {/* Layout Container */}
                <div className="relative isolate">
                    {/* Sidebar Component - Internally uses fixed positioning for desktop */}
                    <Sidebar />

                    {/* Main Content Area */}
                    <MainContent>
                        {children}
                    </MainContent>
                </div>
            </SidebarProvider>
        </AuthGuard>
    );
}
