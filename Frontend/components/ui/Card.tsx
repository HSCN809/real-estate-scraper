import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface CardProps extends HTMLAttributes<HTMLDivElement> { }

const Card = forwardRef<HTMLDivElement, CardProps>(
    ({ className, children, ...props }, ref) => {
        return (
            <article
                ref={ref}
                className={cn(
                    'rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm',
                    className
                )}
                {...props}
            >
                {children}
            </article>
        );
    }
);

Card.displayName = 'Card';

interface CardHeaderProps extends HTMLAttributes<HTMLElement> { }

const CardHeader = forwardRef<HTMLElement, CardHeaderProps>(
    ({ className, children, ...props }, ref) => {
        return (
            <header
                ref={ref}
                className={cn('px-6 py-4 border-b border-gray-200 dark:border-gray-700', className)}
                {...props}
            >
                {children}
            </header>
        );
    }
);

CardHeader.displayName = 'CardHeader';

interface CardContentProps extends HTMLAttributes<HTMLDivElement> { }

const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
    ({ className, children, ...props }, ref) => {
        return (
            <div ref={ref} className={cn('px-6 py-4', className)} {...props}>
                {children}
            </div>
        );
    }
);

CardContent.displayName = 'CardContent';

export { Card, CardHeader, CardContent };
