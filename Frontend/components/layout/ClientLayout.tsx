'use client';

import { SidebarProvider, useSidebar } from '@/components/layout/SidebarContext';
import { Sidebar } from '@/components/layout/Sidebar';
import { ParticleBackground } from '@/components/ui/ParticleBackground';
import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

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
    return (
        <SidebarProvider>
            {/* Particle Background - Fixed at bottom layer */}
            <div className="fixed inset-0" style={{ zIndex: 0 }}>
                <ParticleBackground />
            </div>

            {/* Abstract Decorations - Layer 1 */}
            <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
                <div className="abstract-circle" style={{
                    background: 'radial-gradient(circle, #ff006e, transparent)',
                    top: '10%',
                    right: '10%'
                }} />
                <div className="abstract-circle" style={{
                    background: 'radial-gradient(circle, #8338ec, transparent)',
                    bottom: '20%',
                    left: '15%'
                }} />
                <div className="abstract-square" style={{
                    background: 'linear-gradient(45deg, #3a86ff, #06ffa5)',
                    top: '40%',
                    right: '30%'
                }} />
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
    );
}
