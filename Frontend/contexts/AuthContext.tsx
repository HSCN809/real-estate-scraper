'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import type { User, LoginCredentials, RegisterData } from '@/types/auth';
import * as authApi from '@/lib/auth-api';

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (credentials: LoginCredentials) => Promise<void>;
    register: (data: RegisterData) => Promise<void>;
    logout: () => Promise<void>;
    updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const USER_KEY = 'auth_user';
const PUBLIC_ROUTES = new Set(['/login', '/register', '/homepage']);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();
    const verifiedSessionRef = useRef(false);

    const saveUser = useCallback((nextUser: User) => {
        sessionStorage.setItem(USER_KEY, JSON.stringify(nextUser));
        verifiedSessionRef.current = true;
        setUser(nextUser);
    }, []);

    const clearAuth = useCallback(() => {
        sessionStorage.removeItem(USER_KEY);
        verifiedSessionRef.current = false;
        setUser(null);
    }, []);

    // Bileşen yüklendiğinde auth durumunu başlat
    useEffect(() => {
        let cancelled = false;
        const initAuth = async () => {
            if (verifiedSessionRef.current) {
                setIsLoading(false);
                return;
            }

            const storedUser = sessionStorage.getItem(USER_KEY);
            const isPublic = PUBLIC_ROUTES.has(pathname);

            // Anonim public sayfa açılışında gereksiz /auth/me isteğini atla
            if (isPublic && !storedUser) {
                setIsLoading(false);
                return;
            }

            // 1. Katman: sessionStorage'dan hızlı geri yükleme
            if (storedUser) {
                try {
                    const parsedUser = JSON.parse(storedUser);
                    setUser(parsedUser);
                } catch {
                    clearAuth();
                    setIsLoading(false);
                    return;
                }
            }

            // 2. Katman: Backend ile doğrulama (cookie otomatik gönderilir)
            try {
                const freshUser = await authApi.getCurrentUser();
                if (!cancelled) {
                    saveUser(freshUser);
                }
            } catch {
                // Cookie geçersiz veya yok
                if (!cancelled) {
                    clearAuth();
                }
            }

            if (!cancelled) {
                setIsLoading(false);
            }
        };

        initAuth();
        return () => {
            cancelled = true;
        };
    }, [clearAuth, pathname, saveUser]);

    const login = async (credentials: LoginCredentials) => {
        const user = await authApi.login(credentials);
        saveUser(user);
        router.push('/');
    };

    const register = async (data: RegisterData) => {
        const user = await authApi.register(data);
        saveUser(user);
        router.push('/');
    };

    const logout = useCallback(async () => {
        try {
            await authApi.logout();
        } catch {
            // API çağrısı başarısız olsa bile yerel durumu temizle
        }
        clearAuth();
        router.push('/login');
    }, [clearAuth, router]);

    const updateUser = (updatedUser: User) => {
        setUser(updatedUser);
        sessionStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                isLoading,
                isAuthenticated: !!user,
                login,
                register,
                logout,
                updateUser,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth AuthProvider içinde kullanılmalıdır');
    }
    return context;
}
