'use client';

import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface NavbarProps {
    onMenuClick?: () => void;
}

export function Navbar({ onMenuClick }: NavbarProps) {
    return (
        <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm px-4 lg:px-6">
            {/* Mobil menü butonu */}
            <Button
                variant="ghost"
                size="sm"
                className="lg:hidden"
                onClick={onMenuClick}
            >
                <Menu className="h-5 w-5" />
                <span className="sr-only">Menüyü aç/kapat</span>
            </Button>

            {/* Boşluk */}
            <div className="flex-1" />

            {/* Sağ taraf */}
            <div className="flex items-center gap-4">
                <ThemeToggle />
            </div>
        </header>
    );
}
