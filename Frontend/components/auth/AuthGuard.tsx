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
                // Not authenticated and trying to access protected route
                router.push('/homepage');
            } else if (isAuthenticated && (pathname === '/login' || pathname === '/register' || pathname === '/homepage')) {
                // Already authenticated and trying to access auth/homepage route
                router.push('/');
            }
        }
    }, [isAuthenticated, isLoading, pathname, router]);

    // Show loading spinner while checking auth
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-900">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500" />
            </div>
        );
    }

    // For public routes, always render
    if (publicRoutes.includes(pathname)) {
        return <>{children}</>;
    }

    // For protected routes, only render if authenticated
    if (!isAuthenticated) {
        return null; // Will redirect in useEffect
    }

    return <>{children}</>;
}
