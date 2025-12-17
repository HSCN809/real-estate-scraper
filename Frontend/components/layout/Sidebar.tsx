'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Search, FileText, Settings, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from './SidebarContext';

const navItems = [
    { href: '/', label: 'Dashboard', icon: Home },
    { href: '/scraper', label: 'Scraper', icon: Search },
    { href: '/results', label: 'Sonuçlar', icon: FileText },
    { href: '/settings', label: 'Ayarlar', icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();
    const { isCollapsed, setIsCollapsed } = useSidebar();

    return (
        <>
            {/* Desktop Sidebar */}
            <aside
                className={cn(
                    'hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 transition-all duration-300 z-50',
                    // Visual updates: Corporate Glass - Clean Slate borders
                    'border-r border-slate-700/50 backdrop-blur-xl bg-slate-900/80',
                    isCollapsed ? 'lg:w-20' : 'lg:w-64'
                )}
            >
                {/* Logo */}
                <div className={cn(
                    'flex items-center h-16 px-6 border-b border-slate-700/50',
                    isCollapsed && 'justify-center px-3'
                )}>
                    <Link href="/" className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-sky-500/20">
                            <Home className="w-4 h-4 text-white" />
                        </div>
                        {!isCollapsed && (
                            <span className="text-lg font-bold text-slate-100 whitespace-nowrap overflow-hidden">
                                Emlak Scraper
                            </span>
                        )}
                    </Link>
                </div>

                {/* Navigation */}
                <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto overflow-x-hidden">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        const Icon = item.icon;

                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    'flex items-center gap-3 px-3 py-3 rounded-lg transition-all duration-200 group',
                                    isCollapsed && 'justify-center',
                                    isActive
                                        ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                                )}
                                title={isCollapsed ? item.label : undefined}
                            >
                                <Icon className={cn(
                                    'w-5 h-5 flex-shrink-0 transition-colors',
                                    isActive ? 'text-sky-400' : 'text-slate-500 group-hover:text-slate-300'
                                )} />
                                {!isCollapsed && (
                                    <span className={cn(
                                        'font-medium whitespace-nowrap',
                                        isActive ? 'text-sky-100' : ''
                                    )}>
                                        {item.label}
                                    </span>
                                )}
                            </Link>
                        );
                    })}
                </nav>

                {/* Footer */}
                <div className="px-4 py-4 border-t border-white/10">
                    {!isCollapsed && (
                        <p className="text-xs text-gray-500 mb-3 whitespace-nowrap">
                            Real Estate Scraper v2.0
                        </p>
                    )}
                    {/* Toggle Button */}
                    <button
                        onClick={() => setIsCollapsed(!isCollapsed)}
                        className={cn(
                            'w-full flex items-center justify-center rounded-lg transition-all duration-300',
                            'bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/5 hover:border-white/20',
                            isCollapsed ? 'p-2' : 'px-3 py-2'
                        )}
                    >
                        {isCollapsed ? (
                            <ChevronRight className="w-5 h-5" />
                        ) : (
                            <div className="flex items-center gap-2 w-full justify-center">
                                <ChevronLeft className="w-4 h-4" />
                                <span className="text-sm font-medium">Menüyü Daralt</span>
                            </div>
                        )}
                    </button>
                </div>
            </aside>
        </>
    );
}
