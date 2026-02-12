'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '@/contexts/AuthContext';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { ArtCard } from '@/components/ui/ArtCard';
import { User, Lock, Save, AlertCircle, CheckCircle, Eye, EyeOff } from 'lucide-react';
import * as authApi from '@/lib/auth-api';

export default function ProfilePage() {
    const { user, updateUser } = useAuth();
    const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);
    const [isChangingPassword, setIsChangingPassword] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const [profileData, setProfileData] = useState({
        username: user?.username || '',
        email: user?.email || '',
    });

    const [passwordData, setPasswordData] = useState({
        current_password: '',
        new_password: '',
        confirm_password: '',
    });

    const handleProfileUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        setMessage(null);
        setIsUpdatingProfile(true);

        try {
            const updatedUser = await authApi.updateProfile({
                username: profileData.username !== user?.username ? profileData.username : undefined,
                email: profileData.email !== user?.email ? profileData.email : undefined,
            });

            updateUser(updatedUser);
            setMessage({ type: 'success', text: 'Profil başarıyla güncellendi' });
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Profil güncellenirken hata oluştu' });
        } finally {
            setIsUpdatingProfile(false);
        }
    };

    const handlePasswordChange = async (e: React.FormEvent) => {
        e.preventDefault();
        setMessage(null);

        if (passwordData.new_password !== passwordData.confirm_password) {
            setMessage({ type: 'error', text: 'Yeni şifreler eşleşmiyor' });
            return;
        }

        // Validate password strength
        if (passwordData.new_password.length < 8) {
            setMessage({ type: 'error', text: 'Şifre en az 8 karakter olmalıdır' });
            return;
        }
        if (!/[A-Z]/.test(passwordData.new_password)) {
            setMessage({ type: 'error', text: 'Şifre en az bir büyük harf içermelidir' });
            return;
        }
        if (!/[a-z]/.test(passwordData.new_password)) {
            setMessage({ type: 'error', text: 'Şifre en az bir küçük harf içermelidir' });
            return;
        }
        if (!/\d/.test(passwordData.new_password)) {
            setMessage({ type: 'error', text: 'Şifre en az bir rakam içermelidir' });
            return;
        }

        setIsChangingPassword(true);

        try {
            await authApi.changePassword({
                current_password: passwordData.current_password,
                new_password: passwordData.new_password,
            });

            setMessage({ type: 'success', text: 'Şifre başarıyla değiştirildi' });
            setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Şifre değiştirilirken hata oluştu' });
        } finally {
            setIsChangingPassword(false);
        }
    };

    // Animation variants
    const container = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } },
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 },
    };

    return (
        <motion.section
            className="space-y-8 relative z-10"
            variants={container}
            initial="hidden"
            animate="show"
        >
            {/* Header */}
            <motion.header variants={item}>
                <div className="flex items-center gap-4 mb-3">
                    <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                        <User className="w-10 h-10 text-purple-400" />
                    </div>
                    <div>
                        <h1 className="text-4xl font-bold text-white">Profil</h1>
                        <p className="text-gray-400">Hesap bilgilerinizi yönetin</p>
                    </div>
                </div>
            </motion.header>

            {/* Message */}
            {message && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`p-4 rounded-lg flex items-center gap-3 ${
                        message.type === 'success'
                            ? 'bg-green-500/20 border border-green-500/30'
                            : 'bg-red-500/20 border border-red-500/30'
                    }`}
                >
                    {message.type === 'success'
                        ? <CheckCircle className="w-5 h-5 text-green-400" />
                        : <AlertCircle className="w-5 h-5 text-red-400" />
                    }
                    <p className={message.type === 'success' ? 'text-green-300' : 'text-red-300'}>
                        {message.text}
                    </p>
                </motion.div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Profile Information */}
                <motion.div variants={item}>
                    <ArtCard glowColor="purple" className="h-full">
                        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                            <User className="w-6 h-6 text-purple-400" />
                            Profil Bilgileri
                        </h2>

                        <form onSubmit={handleProfileUpdate} className="space-y-6">
                            <Input
                                label="Kullanıcı Adı"
                                type="text"
                                value={profileData.username}
                                onChange={(e) => setProfileData({ ...profileData, username: e.target.value })}
                                className="bg-white/5 border-white/10 text-white"
                            />

                            <Input
                                label="E-posta"
                                type="email"
                                value={profileData.email}
                                onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                                className="bg-white/5 border-white/10 text-white"
                            />

                            <Button
                                type="submit"
                                disabled={isUpdatingProfile}
                                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                            >
                                {isUpdatingProfile ? 'Güncelleniyor...' : (
                                    <span className="flex items-center gap-2">
                                        <Save className="w-5 h-5" />
                                        Profili Güncelle
                                    </span>
                                )}
                            </Button>
                        </form>
                    </ArtCard>
                </motion.div>

                {/* Change Password */}
                <motion.div variants={item}>
                    <ArtCard glowColor="blue" className="h-full">
                        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                            <Lock className="w-6 h-6 text-blue-400" />
                            Şifre Değiştir
                        </h2>

                        <form onSubmit={handlePasswordChange} className="space-y-6">
                            <div className="relative">
                                <Input
                                    label="Mevcut Şifre"
                                    type={showCurrentPassword ? 'text' : 'password'}
                                    value={passwordData.current_password}
                                    onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
                                    className="bg-white/5 border-white/10 text-white pr-12"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                    className="absolute right-3 top-9 text-gray-400 hover:text-white transition-colors"
                                >
                                    {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>

                            <div className="relative">
                                <Input
                                    label="Yeni Şifre"
                                    type={showNewPassword ? 'text' : 'password'}
                                    value={passwordData.new_password}
                                    onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                                    className="bg-white/5 border-white/10 text-white pr-12"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowNewPassword(!showNewPassword)}
                                    className="absolute right-3 top-9 text-gray-400 hover:text-white transition-colors"
                                >
                                    {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>

                            <div className="relative">
                                <Input
                                    label="Yeni Şifre (Tekrar)"
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    value={passwordData.confirm_password}
                                    onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                                    className="bg-white/5 border-white/10 text-white pr-12"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    className="absolute right-3 top-9 text-gray-400 hover:text-white transition-colors"
                                >
                                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>

                            <Button
                                type="submit"
                                disabled={isChangingPassword}
                                className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700"
                            >
                                {isChangingPassword ? 'Değiştiriliyor...' : (
                                    <span className="flex items-center gap-2">
                                        <Lock className="w-5 h-5" />
                                        Şifreyi Değiştir
                                    </span>
                                )}
                            </Button>
                        </form>
                    </ArtCard>
                </motion.div>
            </div>
        </motion.section>
    );
}
