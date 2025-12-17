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
        const glowClass = {
            pink: 'neon-pink',
            purple: 'neon-purple',
            blue: 'neon-blue',
        }[glowColor];

        return (
            <motion.div
                ref={ref}
                className={cn(
                    'art-card p-6 hover-art',
                    glowClass,
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
