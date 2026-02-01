'use client';

import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode, forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface ArtCardProps extends HTMLMotionProps<"div"> {
    children: ReactNode;
    glowColor?: 'pink' | 'purple' | 'blue';
}

const ArtCard = forwardRef<HTMLDivElement, ArtCardProps>(
    ({ className, children, glowColor = 'purple', ...props }, ref) => {
        return (
            <motion.article
                ref={ref}
                className={cn(
                    'art-card p-6 hover-art',
                    className
                )}
                whileHover={{ scale: 1.02 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                {...props}
            >
                {children}
            </motion.article>
        );
    }
);

ArtCard.displayName = 'ArtCard';

export { ArtCard };
