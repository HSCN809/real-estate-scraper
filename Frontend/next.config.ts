import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker için standalone output
  output: 'standalone',

  // Bundle optimization for tree-shaking
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion'],
    // Chunk splitting optimization
    optimizeCss: true,
  },
};

export default nextConfig;
