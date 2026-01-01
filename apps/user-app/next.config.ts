import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      // 開発環境
      {
        protocol: 'https',
        hostname: 'fatsrmydhyyyragtmhaw.supabase.co',
        pathname: '/storage/v1/object/public/**',
      },
      // 本番環境
      {
        protocol: 'https',
        hostname: 'yhxypitfozoiecxqjyqe.supabase.co',
        pathname: '/storage/v1/object/public/**',
      },
    ],
  },
  // ngrok等の外部ドメインからの開発アクセスを許可
  allowedDevOrigins: [
    'https://*.ngrok-free.dev',
    'https://*.ngrok.io',
  ],
  // node_modulesのテストファイル等をバンドルから除外
  serverExternalPackages: ['pino', 'thread-stream', 'sonic-boom'],
};

export default nextConfig;
