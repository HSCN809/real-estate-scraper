'use client';

import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CheckboxProps {
    label?: string;
    checked: boolean;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
    className?: string;
}

export function Checkbox({
    label,
    checked,
    onChange,
    disabled = false,
    className,
}: CheckboxProps) {
    return (
        <label
            className={cn(
                'flex items-center gap-3 cursor-pointer group select-none',
                disabled && 'opacity-50 cursor-not-allowed',
                className
            )}
        >
            <div className="relative">
                <input
                    type="checkbox"
                    className="sr-only"
                    checked={checked}
                    disabled={disabled}
                    onChange={(e) => onChange(e.target.checked)}
                />
                <div
                    className={cn(
                        'w-6 h-6 rounded-lg border-2 transition-all duration-200 flex items-center justify-center',
                        checked
                            ? 'bg-blue-500 border-blue-500'
                            : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 group-hover:border-blue-400'
                    )}
                >
                    <Check
                        className={cn(
                            'w-4 h-4 text-white transition-transform duration-200',
                            checked ? 'scale-100' : 'scale-0'
                        )}
                    />
                </div>
            </div>
            {label && (
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {label}
                </span>
            )}
        </label>
    );
}
