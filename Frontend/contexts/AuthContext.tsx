'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
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

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    const saveUser = (user: User) => {
        sessionStorage.setItem(USER_KEY, JSON.stringify(user));
        setUser(user);
    };

    const clearAuth = useCallback(() => {
        sessionStorage.removeItem(USER_KEY);
        setUser(null);
    }, []);

    // Bileşen yüklendiğinde auth durumunu başlat
    useEffect(() => {
        const initAuth = async () => {
            const storedUser = sessionStorage.getItem(USER_KEY);

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
                saveUser(freshUser);
            } catch {
                // Cookie geçersiz veya yok
                clearAuth();
            }

            setIsLoading(false);
        };

        initAuth();
    }, [clearAuth]);

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
