import type {
    LoginCredentials,
    RegisterData,
    User,
    ChangePasswordData,
    UpdateProfileData
} from '@/types/auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class AuthError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
        this.name = 'AuthError';
    }
}

function extractErrorMessage(error: any, fallback: string): string {
    const detail = error?.detail;
    if (typeof detail === 'string') return detail;
    // FastAPI 422 validation errors return detail as array
    if (Array.isArray(detail) && detail.length > 0) {
        const firstError = detail[0];
        return firstError?.msg || firstError?.message || fallback;
    }
    return fallback;
}

export async function login(credentials: LoginCredentials): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(credentials),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Giriş başarısız' }));
        throw new AuthError(extractErrorMessage(error, 'Giriş başarısız'), response.status);
    }

    return response.json();
}

export async function register(data: RegisterData): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Kayıt başarısız' }));
        throw new AuthError(extractErrorMessage(error, 'Kayıt başarısız'), response.status);
    }

    return response.json();
}

export async function getCurrentUser(): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
        credentials: 'include',
    });

    if (!response.ok) {
        throw new AuthError('Kullanıcı bilgisi alınamadı', response.status);
    }

    return response.json();
}

export async function updateProfile(data: UpdateProfileData): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Profil güncelleme başarısız' }));
        throw new AuthError(extractErrorMessage(error, 'Profil güncelleme başarısız'), response.status);
    }

    return response.json();
}

export async function changePassword(data: ChangePasswordData): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Şifre değiştirme başarısız' }));
        throw new AuthError(extractErrorMessage(error, 'Şifre değiştirme başarısız'), response.status);
    }
}

export async function logout(): Promise<void> {
    await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
    });
}
