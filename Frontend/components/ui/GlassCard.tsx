'use client';

import { motion } from 'framer-motion';
import { HTMLAttributes, ReactNode, forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
    children: ReactNode;
    variant?: 'default' | 'strong' | 'dark';
    hoverable?: boolean;
    neonBorder?: 'purple' | 'blue' | 'pink' | 'none';
    glow?: boolean;
}

const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
    (
        {
            className,
            children,
            variant = 'default',
            hoverable = true,
            neonBorder = 'none',
            glow = false,
            ...props
        },
        ref
    ) => {
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

        const MotionDiv = motion.div;

        return (
            <MotionDiv
                ref={ref}
                className={cn(
                    'rounded-2xl p-6 transition-all duration-300',
                    variantClasses[variant],
                    hoverable && 'hover-lift cursor-pointer',
                    neonClasses[neonBorder],
                    glow && 'glow-purple',
                    className
                )}
                whileHover={hoverable ? { scale: 1.02 } : {}}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                {...props}
            >
                {children}
            </MotionDiv>
        );
    }
);

GlassCard.displayName = 'GlassCard';

export { GlassCard };
