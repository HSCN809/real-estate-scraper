import type {
    LoginCredentials,
    RegisterData,
    LoginResponse,
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

export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Giriş başarısız' }));
        throw new AuthError(error.detail || 'Giriş başarısız', response.status);
    }

    return response.json();
}

export async function register(data: RegisterData): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Kayıt başarısız' }));
        throw new AuthError(error.detail || 'Kayıt başarısız', response.status);
    }

    return response.json();
}

export async function getCurrentUser(token: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!response.ok) {
        throw new AuthError('Kullanıcı bilgisi alınamadı', response.status);
    }

    return response.json();
}

export async function updateProfile(token: string, data: UpdateProfileData): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Profil güncelleme başarısız' }));
        throw new AuthError(error.detail || 'Profil güncelleme başarısız', response.status);
    }

    return response.json();
}

export async function changePassword(token: string, data: ChangePasswordData): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Şifre değiştirme başarısız' }));
        throw new AuthError(error.detail || 'Şifre değiştirme başarısız', response.status);
    }
}
