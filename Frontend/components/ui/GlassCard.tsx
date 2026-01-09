'use client';

import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface GlassCardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
    children: ReactNode;
    variant?: 'default' | 'strong' | 'dark';
    hoverable?: boolean;
    neonBorder?: 'purple' | 'blue' | 'pink' | 'none';
    glow?: boolean;
}

export function GlassCard({
    className,
    children,
    variant = 'default',
    hoverable = true,
    neonBorder = 'none',
    glow = false,
    ...props
}: GlassCardProps) {
    const variantClasses = {
        default: 'glass',
        strong: 'glass-strong',
        dark: 'glass-dark',
    };

    const neonClasses = {
        purple: 'neon-border-purple',
        blue: 'neon-border-blue',
        pink: 'neon-border-pink',
        none: '',
    };

    return (
        <motion.div
            className={cn(
                'rounded-2xl p-6 transition-all duration-300',
                variantClasses[variant],
                hoverable && 'hover-lift cursor-pointer',
                neonClasses[neonBorder],
                glow && 'glow-purple',
                className
            )}
            whileHover={hoverable ? { scale: 1.02 } : undefined}
            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            {...props}
        >
            {children}
        </motion.div>
    );
}
