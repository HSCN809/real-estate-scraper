import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === 'development';
const apiOrigin = new URL(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').origin;

// shortcut: nonce'suz statik CSP, script-src 'unsafe-inline' içerir (Next hidrasyon script'leri);
// sıkı XSS koruması gerekirse proxy.ts + nonce'a geç (tüm sayfalar dinamik render olur).
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ''}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' blob: data:",
  "font-src 'self'",
  // Harita GeoJSON'u: components/ui/ResultsMapInner.tsx
  `connect-src 'self' ${apiOrigin} https://raw.githubusercontent.com`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join('; ');

const nextConfig: NextConfig = {
  output: 'standalone',
  allowedDevOrigins: ['127.0.0.1', 'localhost'],

  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Content-Security-Policy', value: contentSecurityPolicy },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
    ];
  },

  // Bundle optimization for tree-shaking
  experimental: {
    optimizePackageImports: ['lucide-react', 'motion'],
    // Chunk splitting optimization
    optimizeCss: true,
  },
};

export default nextConfig;
