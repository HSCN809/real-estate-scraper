'use client';

import dynamic from 'next/dynamic';
import { useSyncExternalStore } from 'react';

const FloatingLines = dynamic(() => import('./FloatingLines'), { ssr: false });
const animationQuery = '(min-width: 48rem) and (pointer: fine) and (prefers-reduced-motion: no-preference)';
const staticBackground = {
    background: 'radial-gradient(ellipse at 18% 20%, #0c4a6e, transparent 58%), radial-gradient(ellipse at 82% 72%, #164e63, transparent 60%), #020617',
};

function subscribe(onChange: () => void) {
    const media = window.matchMedia(animationQuery);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
}

function getSnapshot() {
    return window.matchMedia(animationQuery).matches;
}

function getServerSnapshot() {
    return false;
}

export function ResultsBackground() {
    const canAnimate = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

    return (
        <div
            aria-hidden="true"
            data-results-background
            className="fixed inset-0 z-0"
            style={canAnimate ? undefined : staticBackground}
        >
            {canAnimate && (
                <FloatingLines
                    linesGradient={['#38bdf8', '#0ea5e9', '#34d399', '#818cf8']}
                    enabledWaves={['top', 'middle', 'bottom']}
                    lineCount={5}
                    lineDistance={5}
                    bendRadius={5}
                    bendStrength={-0.5}
                    interactive
                    parallax
                />
            )}
        </div>
    );
}
