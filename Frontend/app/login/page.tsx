'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/Toast';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { LogIn, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
    const { login } = useAuth();
    const toast = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [formData, setFormData] = useState({
        username: '',
        password: '',
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            await login(formData);
            toast.success('Giriş başarılı!');
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Giriş başarısız');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen overflow-hidden bg-black">
            <div className="absolute inset-0 z-0 bg-[radial-gradient(ellipse_at_top,_#0ea5e933,_transparent_55%),radial-gradient(ellipse_at_bottom,_#10b98122,_#000)]" />

            {/* Giriş Formu */}
            <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
                <div className="w-full max-w-md">
                    <div className="bg-black/60 rounded-2xl p-8 border border-white/10 shadow-2xl">
                        <div className="text-center mb-8">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-sky-500 to-emerald-500 flex items-center justify-center">
                                <LogIn className="w-8 h-8 text-white" />
                            </div>
                            <h1 className="text-3xl font-bold text-white mb-2">
                                Hoş Geldiniz
                            </h1>
                            <p className="text-gray-400">
                                Emlak Scraper&apos;a giriş yapın
                            </p>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div>
                                <Input
                                    label="Kullanıcı Adı veya E-posta"
                                    type="text"
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                    placeholder="kullanıcı_adı"
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
                                    aria-label={showPassword ? 'Şifreyi gizle' : 'Şifreyi göster'}
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-9 text-gray-400 hover:text-white transition-colors"
                                >
                                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>

                            <Button
                                type="submit"
                                disabled={isLoading}
                                className="w-full bg-gradient-to-r from-sky-500 to-emerald-500 hover:from-sky-600 hover:to-emerald-600 text-white font-bold py-3"
                            >
                                {isLoading ? (
                                    <span className="flex items-center gap-2">
                                        <span className="animate-spin rounded-full h-4 w-4 border-t-2 border-white" />
                                        Giriş yapılıyor...
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-2">
                                        <LogIn className="w-5 h-5" />
                                        Giriş Yap
                                    </span>
                                )}
                            </Button>
                        </form>

                        {/* Kayıt Linki */}
                        <div className="mt-6 text-center">
                            <p className="text-gray-400">
                                Hesabınız yok mu?{' '}
                                <Link
                                    href="/register"
                                    className="text-sky-400 hover:text-sky-300 font-medium transition-colors"
                                >
                                    Kayıt Ol
                                </Link>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
