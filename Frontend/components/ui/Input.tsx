'use client';

import { InputHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
    label?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
    ({ className, label, type = 'text', ...props }, ref) => {
        return (
            <div className="flex flex-col gap-1.5">
                {label && (
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {label}
                    </label>
                )}
                <input
                    ref={ref}
                    type={type}
                    className={cn(
                        'w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600',
                        'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
                        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                        'placeholder:text-gray-400 dark:placeholder:text-gray-500',
                        className
                    )}
                    {...props}
                />
            </div>
        );
    }
);

Input.displayName = 'Input';

export { Input };
