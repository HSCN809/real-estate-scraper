'use client';

import { useTheme } from 'next-themes';
import { useSyncExternalStore } from 'react';
import { Sun, Moon } from 'lucide-react';
import { Button } from './Button';

const subscribe = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

export function ThemeToggle() {
    const { theme, setTheme } = useTheme();
    const mounted = useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);

    if (!mounted) {
        return (
            <Button variant="ghost" size="sm" className="w-9 h-9 p-0">
                <span className="sr-only">Tema değiştir</span>
            </Button>
        );
    }

    return (
        <Button
            variant="ghost"
            size="sm"
            className="w-9 h-9 p-0"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
            {theme === 'dark' ? (
                <Sun className="h-5 w-5 text-yellow-500" />
            ) : (
                <Moon className="h-5 w-5 text-gray-700" />
            )}
            <span className="sr-only">Tema değiştir</span>
        </Button>
    );
}
