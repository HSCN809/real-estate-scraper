'use client';

import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { ReactNode } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';

interface ProvidersProps {
    children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
    return (
        <NextThemesProvider attribute="class" defaultTheme="system" enableSystem>
            <AuthProvider>
                {children}
            </AuthProvider>
        </NextThemesProvider>
    );
}
