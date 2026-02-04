'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import type { User, LoginCredentials, RegisterData, LoginResponse } from '@/types/auth';
import * as authApi from '@/lib/auth-api';

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (credentials: LoginCredentials) => Promise<void>;
    register: (data: RegisterData) => Promise<void>;
    logout: () => void;
    updateUser: (user: User) => void;
    getAccessToken: () => string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    const saveAuth = (response: LoginResponse) => {
        sessionStorage.setItem(TOKEN_KEY, response.access_token);
        sessionStorage.setItem(USER_KEY, JSON.stringify(response.user));
        setUser(response.user);
    };

    const clearAuth = useCallback(() => {
        sessionStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(USER_KEY);
        setUser(null);
    }, []);

    const getAccessToken = useCallback((): string | null => {
        if (typeof window === 'undefined') return null;
        return sessionStorage.getItem(TOKEN_KEY);
    }, []);

    // Initialize auth state on mount
    useEffect(() => {
        const initAuth = async () => {
            const token = sessionStorage.getItem(TOKEN_KEY);
            const storedUser = sessionStorage.getItem(USER_KEY);

            if (token && storedUser) {
                // Önce mevcut kullanıcıyı yükle (hızlı yükleme için)
                try {
                    const parsedUser = JSON.parse(storedUser);
                    setUser(parsedUser);
                } catch {
                    clearAuth();
                    setIsLoading(false);
                    return;
                }

                // Arka planda token'ı doğrula
                try {
                    const freshUser = await authApi.getCurrentUser(token);
                    setUser(freshUser);
                    sessionStorage.setItem(USER_KEY, JSON.stringify(freshUser));
                } catch {
                    // Token geçersizse oturumu temizle
                    clearAuth();
                }
            }
            setIsLoading(false);
        };

        initAuth();
    }, [clearAuth]);

    const login = async (credentials: LoginCredentials) => {
        const response = await authApi.login(credentials);
        saveAuth(response);
        router.push('/');
    };

    const register = async (data: RegisterData) => {
        const response = await authApi.register(data);
        saveAuth(response);
        router.push('/');
    };

    const logout = useCallback(() => {
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
                getAccessToken,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
