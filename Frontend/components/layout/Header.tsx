'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Search, FileText, Settings, User, LogOut, ChevronDown, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import { useScraping } from '@/contexts/ScrapingContext';
import { useState, useRef, useEffect } from 'react';

// Ana navigasyon öğeleri (Profil ve Ayarlar dropdown'a taşındı)
const navItems = [
    { href: '/', label: 'Dashboard', icon: Home },
    { href: '/scraper', label: 'Scraper', icon: Search },
    { href: '/results', label: 'Sonuçlar', icon: FileText },
];

// Dropdown menü öğeleri
const dropdownMenuItems = [
    { href: '/profile', label: 'Profil', icon: User },
    { href: '/settings', label: 'Ayarlar', icon: Settings },
];

export function Header() {
    const pathname = usePathname();
    const { user, logout } = useAuth();
    const { activeTask, isPanelVisible, showPanel } = useScraping();
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const showMiniIndicator = activeTask && !activeTask.isFinished && !isPanelVisible;

    // Dropdown dışına tıklandığında kapat
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsDropdownOpen(false);
            }
        }

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const isDropdownItemActive = dropdownMenuItems.some(item => pathname === item.href);

    return (
        <header className="fixed top-0 left-0 right-0 h-16 z-50 border-b border-slate-700/50 backdrop-blur-xl bg-slate-900/90">
            <div className="h-full max-w-7xl mx-auto px-6 flex items-center">
                {/* Logo */}
                <Link href="/" className="flex items-center gap-3 mr-12">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-sky-500/25">
                        <Home className="w-5 h-5 text-white" />
                    </div>
                    <span className="text-xl font-bold bg-gradient-to-r from-slate-100 to-slate-300 bg-clip-text text-transparent whitespace-nowrap">
                        Emlak Scraper
                    </span>
                </Link>

                {/* Navigasyon */}
                <nav className="flex items-center gap-1 flex-1">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        const Icon = item.icon;

                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    'flex items-center gap-2 px-4 py-2.5 rounded-lg transition-all duration-200 group',
                                    isActive
                                        ? 'bg-sky-500/15 text-sky-400'
                                        : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                                )}
                            >
                                <Icon className={cn(
                                    'w-[18px] h-[18px] flex-shrink-0 transition-colors',
                                    isActive ? 'text-sky-400' : 'text-slate-500 group-hover:text-slate-300'
                                )} />
                                <span className={cn(
                                    'text-sm font-medium whitespace-nowrap',
                                    isActive ? 'text-sky-100' : ''
                                )}>
                                    {item.label}
                                </span>
                            </Link>
                        );
                    })}
                </nav>

                {/* Mini İlerleme Göstergesi */}
                {showMiniIndicator && (
                    <button
                        onClick={showPanel}
                        className="flex items-center gap-2 px-3 py-1.5 mr-3 rounded-lg bg-blue-500/15 border border-blue-500/30 hover:bg-blue-500/25 transition-all text-blue-400 text-sm font-medium"
                        title="Tarama devam ediyor — tıkla görüntüle"
                    >
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="hidden sm:inline">
                            %{Math.round(activeTask.status?.progress || 0)}
                        </span>
                    </button>
                )}

                {/* Kullanıcı Bölümü */}
                {user && (
                    <div className="relative" ref={dropdownRef}>
                        <button
                            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                            className={cn(
                                'flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-200',
                                'hover:bg-slate-800/60',
                                isDropdownOpen && 'bg-slate-800/60',
                                isDropdownItemActive && 'ring-2 ring-sky-500/30'
                            )}
                        >
                            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0 ring-2 ring-white/10">
                                <span className="text-white text-sm font-bold">
                                    {user.username.charAt(0).toUpperCase()}
                                </span>
                            </div>
                            <div className="text-left hidden sm:block">
                                <p className="text-sm font-medium text-slate-200 leading-tight">
                                    {user.username}
                                </p>
                                <p className="text-xs text-slate-500 leading-tight">
                                    {user.is_admin ? 'Admin' : 'Kullanıcı'}
                                </p>
                            </div>
                            <ChevronDown className={cn(
                                'w-4 h-4 text-slate-400 transition-transform duration-200',
                                isDropdownOpen && 'rotate-180'
                            )} />
                        </button>

                        {/* Açılır Menü */}
                        {isDropdownOpen && (
                            <div className="absolute right-0 top-full mt-2 w-72 rounded-xl border border-slate-700/50 backdrop-blur-xl bg-slate-900/95 shadow-2xl shadow-black/30 overflow-hidden">
                                {/* Kullanıcı Bilgileri */}
                                <div className="px-4 py-4 bg-gradient-to-r from-slate-800/50 to-slate-800/30 border-b border-slate-700/50">
                                    <div className="flex items-center gap-3">
                                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0 ring-2 ring-white/10">
                                            <span className="text-white text-lg font-bold">
                                                {user.username.charAt(0).toUpperCase()}
                                            </span>
                                        </div>
                                        <div className="overflow-hidden flex-1">
                                            <p className="text-base font-semibold text-slate-100 truncate">
                                                {user.username}
                                            </p>
                                            <p className="text-sm text-slate-400 truncate">
                                                {user.email}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Menü Öğeleri */}
                                <div className="p-2">
                                    {dropdownMenuItems.map((item) => {
                                        const isActive = pathname === item.href;
                                        const Icon = item.icon;

                                        return (
                                            <Link
                                                key={item.href}
                                                href={item.href}
                                                onClick={() => setIsDropdownOpen(false)}
                                                className={cn(
                                                    'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                                                    isActive
                                                        ? 'bg-sky-500/15 text-sky-400'
                                                        : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/60'
                                                )}
                                            >
                                                <Icon className={cn(
                                                    'w-5 h-5 flex-shrink-0',
                                                    isActive ? 'text-sky-400' : 'text-slate-500'
                                                )} />
                                                <span className="text-sm font-medium">{item.label}</span>
                                            </Link>
                                        );
                                    })}
                                </div>

                                {/* Ayırıcı */}
                                <div className="border-t border-slate-700/50 mx-2" />

                                {/* Çıkış Butonu */}
                                <div className="p-2">
                                    <button
                                        onClick={() => {
                                            setIsDropdownOpen(false);
                                            logout();
                                        }}
                                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                                    >
                                        <LogOut className="w-5 h-5 flex-shrink-0" />
                                        <span className="text-sm font-medium">Çıkış Yap</span>
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </header>
    );
}
