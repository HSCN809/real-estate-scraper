'use client';

import { motion } from 'framer-motion';
import { HTMLAttributes, ReactNode, forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface ArtCardProps extends HTMLAttributes<HTMLDivElement> {
    children: ReactNode;
    glowColor?: 'pink' | 'purple' | 'blue';
}

const ArtCard = forwardRef<HTMLDivElement, ArtCardProps>(
    ({ className, children, glowColor = 'purple', ...props }, ref) => {
        // glowColor prop is kept for API compatibility but now purely affects border/accent via CSS if needed
        // For Corporate Glass, we default to a standard clean look, maybe subtle variation

        return (
            <motion.div
                ref={ref}
                className={cn(
                    'art-card p-6 hover-art',
                    // Convert old glow props to potentially useful utility classes or just ignore
                    // For now, we rely on the global CSS .art-card style which is uniform
                    className
                )}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ scale: 1.02 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                {...props}
            >
                {children}
            </motion.div>
        );
    }
);

ArtCard.displayName = 'ArtCard';

export { ArtCard };
