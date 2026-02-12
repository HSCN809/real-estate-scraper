'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/Toast';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import dynamic from 'next/dynamic';
import { UserPlus, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';

const Hyperspeed = dynamic(() => import('@/components/ui/Hyperspeed'), { ssr: false });

export default function RegisterPage() {
    const { register } = useAuth();
    const toast = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Şifrelerin eşleştiğini kontrol et
        if (formData.password !== formData.confirmPassword) {
            toast.error('Şifreler eşleşmiyor');
            return;
        }

        // Şifre gücünü kontrol et
        if (formData.password.length < 8) {
            toast.error('Şifre en az 8 karakter olmalıdır');
            return;
        }
        if (!/[A-Z]/.test(formData.password)) {
            toast.error('Şifre en az bir büyük harf içermelidir');
            return;
        }
        if (!/[a-z]/.test(formData.password)) {
            toast.error('Şifre en az bir küçük harf içermelidir');
            return;
        }
        if (!/\d/.test(formData.password)) {
            toast.error('Şifre en az bir rakam içermelidir');
            return;
        }

        setIsLoading(true);

        try {
            await register({
                username: formData.username,
                email: formData.email,
                password: formData.password,
            });
            toast.success('Hesap başarıyla oluşturuldu!');
        } catch (err: any) {
            toast.error(err.message || 'Kayıt başarısız');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen overflow-hidden bg-black">
            {/* Arka Plan Efekti */}
            <div className="absolute inset-0 z-0">
                <Hyperspeed
                    effectOptions={{
                        onSpeedUp: () => {},
                        onSlowDown: () => {},
                        distortion: 'mountainDistortion',
                        length: 400,
                        roadWidth: 9,
                        islandWidth: 2,
                        lanesPerRoad: 3,
                        fov: 90,
                        fovSpeedUp: 150,
                        speedUp: 2,
                        carLightsFade: 0.4,
                        totalSideLightSticks: 50,
                        lightPairsPerRoadWay: 50,
                        shoulderLinesWidthPercentage: 0.05,
                        brokenLinesWidthPercentage: 0.1,
                        brokenLinesLengthPercentage: 0.5,
                        lightStickWidth: [0.12, 0.5],
                        lightStickHeight: [1.3, 1.7],
                        movingAwaySpeed: [60, 80],
                        movingCloserSpeed: [-120, -160],
                        carLightsLength: [400 * 0.05, 400 * 0.15],
                        carLightsRadius: [0.05, 0.14],
                        carWidthPercentage: [0.3, 0.5],
                        carShiftX: [-0.2, 0.2],
                        carFloorSeparation: [0.05, 1],
                        colors: {
                            roadColor: 0x080808,
                            islandColor: 0x0a0a0a,
                            background: 0x000000,
                            shoulderLines: 0x131318,
                            brokenLines: 0x131318,
                            leftCars: [0x34d399, 0x10b981, 0x059669],  // Zümrüt yeşili
                            rightCars: [0x38bdf8, 0x0ea5e9, 0x0284c7], // Gök mavisi
                            sticks: 0x34d399, // Zümrüt
                        }
                    }}
                />
            </div>

            {/* Kayıt Formu */}
            <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="w-full max-w-md"
                >
                    <div className="backdrop-blur-xl bg-black/40 rounded-2xl p-8 border border-white/10 shadow-2xl">
                        {/* Başlık */}
                        <div className="text-center mb-8">
                            <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ delay: 0.2, type: 'spring' }}
                                className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-emerald-500 to-sky-500 flex items-center justify-center"
                            >
                                <UserPlus className="w-8 h-8 text-white" />
                            </motion.div>
                            <h1 className="text-3xl font-bold text-white mb-2">
                                Hesap Oluştur
                            </h1>
                            <p className="text-gray-400">
                                Emlak Scraper'a katılın
                            </p>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-5">
                            <div>
                                <Input
                                    label="Kullanıcı Adı"
                                    type="text"
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                    placeholder="kullanici_adi"
                                    required
                                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500"
                                />
                            </div>

                            <div>
                                <Input
                                    label="E-posta"
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    placeholder="ornek@email.com"
                                    required
                                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500"
                                />
                            </div>

                            <div className="relative">
                                <Input
                                    label="Şifre"
                                    type={showPassword ? 'text' : 'password'}
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    placeholder="********"
                                    required
                                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 pr-12"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-9 text-gray-400 hover:text-white transition-colors"
                                >
                                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>

                            <div className="relative">
                                <Input
                                    label="Şifre Tekrar"
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    value={formData.confirmPassword}
                                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                                    placeholder="********"
                                    required
                                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 pr-12"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    className="absolute right-3 top-9 text-gray-400 hover:text-white transition-colors"
                                >
                                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>

                            <div className="text-xs text-gray-400 space-y-1">
                                <p>Şifre gereksinimleri:</p>
                                <ul className="list-disc list-inside space-y-0.5">
                                    <li>En az 8 karakter</li>
                                    <li>En az bir büyük harf</li>
                                    <li>En az bir küçük harf</li>
                                    <li>En az bir rakam</li>
                                </ul>
                            </div>

                            <Button
                                type="submit"
                                disabled={isLoading}
                                className="w-full bg-gradient-to-r from-emerald-500 to-sky-500 hover:from-emerald-600 hover:to-sky-600 text-white font-bold py-3"
                            >
                                {isLoading ? (
                                    <span className="flex items-center gap-2">
                                        <span className="animate-spin rounded-full h-4 w-4 border-t-2 border-white" />
                                        Kayıt yapılıyor...
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-2">
                                        <UserPlus className="w-5 h-5" />
                                        Kayıt Ol
                                    </span>
                                )}
                            </Button>
                        </form>

                        {/* Giriş Linki */}
                        <div className="mt-6 text-center">
                            <p className="text-gray-400">
                                Zaten hesabınız var mı?{' '}
                                <Link
                                    href="/login"
                                    className="text-emerald-400 hover:text-emerald-300 font-medium transition-colors"
                                >
                                    Giriş Yap
                                </Link>
                            </p>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
