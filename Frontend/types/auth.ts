export interface User {
    id: number;
    username: string;
    email: string;
    is_active: boolean;
    is_admin: boolean;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
    user: User;
}

export interface LoginCredentials {
    username: string;
    password: string;
}

export interface RegisterData {
    username: string;
    email: string;
    password: string;
}

export interface ChangePasswordData {
    current_password: string;
    new_password: string;
}

export interface UpdateProfileData {
    username?: string;
    email?: string;
}
