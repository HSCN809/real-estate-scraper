'use client';

import React, { useRef, ReactNode, MouseEventHandler } from 'react';
import { motion, useInView } from 'motion/react';

interface AnimatedItemProps {
  children: ReactNode;
  delay?: number;
  index: number;
  onMouseEnter?: MouseEventHandler<HTMLDivElement>;
  onClick?: MouseEventHandler<HTMLDivElement>;
}

const AnimatedItem: React.FC<AnimatedItemProps> = ({ children, delay = 0, index, onMouseEnter, onClick }) => {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.5, once: false });
  return (
    <motion.div
      ref={ref}
      data-index={index}
      onMouseEnter={onMouseEnter}
      onClick={onClick}
      initial={{ scale: 0.7, opacity: 0 }}
      animate={inView ? { scale: 1, opacity: 1 } : { scale: 0.7, opacity: 0 }}
      transition={{ duration: 0.2, delay }}
      className="mb-4"
    >
      {children}
    </motion.div>
  );
};

interface AnimatedListProps {
  items: ReactNode[];
  className?: string;
  itemClassName?: string;
  showGradients?: boolean;
}

const AnimatedList: React.FC<AnimatedListProps> = ({
  items,
  className = '',
  itemClassName = '',
  showGradients = true
}) => {
  const listRef = useRef<HTMLDivElement>(null);
  const [topGradientOpacity, setTopGradientOpacity] = React.useState<number>(0);
  const [bottomGradientOpacity, setBottomGradientOpacity] = React.useState<number>(1);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target as HTMLDivElement;
    setTopGradientOpacity(Math.min(scrollTop / 50, 1));
    const bottomDistance = scrollHeight - (scrollTop + clientHeight);
    setBottomGradientOpacity(scrollHeight <= clientHeight ? 0 : Math.min(bottomDistance / 50, 1));
  };

  return (
    <div className={`relative ${className}`}>
      <div
        ref={listRef}
        className="overflow-y-auto p-4 scrollbar-thin scrollbar-track-slate-900 scrollbar-thumb-slate-700"
        onScroll={handleScroll}
        style={{
          scrollbarWidth: 'thin',
          scrollbarColor: '#334155 #0f172a'
        }}
      >
        {items.map((item, index) => (
          <AnimatedItem
            key={index}
            delay={0.05 * index}
            index={index}
          >
            <div className={itemClassName}>
              {item}
            </div>
          </AnimatedItem>
        ))}
      </div>
      {showGradients && (
        <>
          <div
            className="absolute top-0 left-0 right-0 h-[50px] bg-gradient-to-b from-slate-900 to-transparent pointer-events-none transition-opacity duration-300 ease"
            style={{ opacity: topGradientOpacity }}
          />
          <div
            className="absolute bottom-0 left-0 right-0 h-[100px] bg-gradient-to-t from-slate-900 to-transparent pointer-events-none transition-opacity duration-300 ease"
            style={{ opacity: bottomGradientOpacity }}
          />
        </>
      )}
    </div>
  );
};

export default AnimatedList;
