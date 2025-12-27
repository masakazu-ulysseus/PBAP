import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'fatsrmydhyyyragtmhaw.supabase.co',
        pathname: '/storage/v1/object/public/**',
      },
    ],
  },
  // ngrok等の外部ドメインからの開発アクセスを許可
  allowedDevOrigins: [
    'https://*.ngrok-free.dev',
    'https://*.ngrok.io',
  ],
};

export default nextConfig;
