'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

const publicRoutes = ['/login', '/register', '/homepage'];

interface AuthGuardProps {
    children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
    const { isAuthenticated, isLoading } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        if (!isLoading) {
            const isPublicRoute = publicRoutes.includes(pathname);

            if (!isAuthenticated && !isPublicRoute) {
                // Giriş yapılmamış ve korumalı sayfaya erişmeye çalışıyor
                router.push('/homepage');
            } else if (isAuthenticated && (pathname === '/login' || pathname === '/register' || pathname === '/homepage')) {
                // Giriş yapılmış ve auth/homepage sayfasına erişmeye çalışıyor
                router.push('/');
            }
        }
    }, [isAuthenticated, isLoading, pathname, router]);

    // Auth kontrol edilirken yükleniyor
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-900">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500" />
            </div>
        );
    }

    // Public sayfalar her zaman gösterilir
    if (publicRoutes.includes(pathname)) {
        return <>{children}</>;
    }

    // Korumalı sayfalar sadece giriş yapılmışsa gösterilir
    if (!isAuthenticated) {
        return null; // useEffect'te yönlendirilecek
    }

    return <>{children}</>;
}
