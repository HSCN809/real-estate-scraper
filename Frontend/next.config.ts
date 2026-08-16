import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  allowedDevOrigins: ['127.0.0.1', 'localhost'],

  // Bundle optimization for tree-shaking
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion'],
    // Chunk splitting optimization
    optimizeCss: true,
  },
};

export default nextConfig;
