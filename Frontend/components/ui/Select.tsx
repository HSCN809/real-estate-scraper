'use client';

import { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown } from 'lucide-react';

interface SelectProps {
    label?: string;
    value: string;
    onChange: (e: { target: { value: string } }) => void;
    options: { value: string; label: string }[];
    disabled?: boolean;
    className?: string;
    maxHeight?: number;  // Dropdown max height in pixels
}

const Select = ({ label, value, onChange, options, disabled, className, maxHeight = 250 }: SelectProps) => {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // Seçili option'ın label'ını bul
    const selectedLabel = options.find(opt => opt.value === value)?.label || 'Seçiniz...';

    // Dışarı tıklandığında kapat
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelect = (optionValue: string) => {
        onChange({ target: { value: optionValue } });
        setIsOpen(false);
    };

    return (
        <div className="flex flex-col gap-1.5" ref={containerRef}>
            {label && (
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {label}
                </label>
            )}
            <div className="relative">
                {/* Trigger Button */}
                <button
                    type="button"
                    onClick={() => !disabled && setIsOpen(!isOpen)}
                    disabled={disabled}
                    className={cn(
                        'w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600',
                        'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
                        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                        'flex items-center justify-between gap-2 text-left',
                        'transition-all duration-200',
                        disabled && 'opacity-50 cursor-not-allowed',
                        className
                    )}
                >
                    <span className="truncate">{selectedLabel}</span>
                    <ChevronDown
                        className={cn(
                            'w-4 h-4 flex-shrink-0 transition-transform duration-200',
                            isOpen && 'transform rotate-180'
                        )}
                    />
                </button>

                {/* Dropdown List */}
                {isOpen && !disabled && (
                    <div
                        className={cn(
                            'absolute z-50 w-full mt-1 rounded-lg border border-gray-300 dark:border-gray-600',
                            'bg-white dark:bg-gray-800 shadow-lg',
                            'overflow-y-auto'
                        )}
                        style={{ maxHeight: `${maxHeight}px` }}
                    >
                        {options.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                onClick={() => handleSelect(option.value)}
                                className={cn(
                                    'w-full px-3 py-2 text-left',
                                    'text-gray-900 dark:text-gray-100',
                                    'hover:bg-blue-50 dark:hover:bg-gray-700',
                                    'transition-colors duration-150',
                                    'first:rounded-t-lg last:rounded-b-lg',
                                    value === option.value && 'bg-blue-100 dark:bg-blue-900/30 font-medium'
                                )}
                            >
                                {option.label}
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

Select.displayName = 'Select';

export { Select };
