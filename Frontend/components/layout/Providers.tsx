'use client';

import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { ReactNode } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';
import { ScrapingProvider } from '@/contexts/ScrapingContext';
import { ToastProvider } from '@/components/ui/Toast';

interface ProvidersProps {
    children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
    return (
        <NextThemesProvider attribute="class" defaultTheme="system" enableSystem>
            <ToastProvider>
                <AuthProvider>
                    <ScrapingProvider>
                        {children}
                    </ScrapingProvider>
                </AuthProvider>
            </ToastProvider>
        </NextThemesProvider>
    );
}
