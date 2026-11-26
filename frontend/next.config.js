/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Emits .next/standalone so the Docker image ships only the server it needs.
  output: 'standalone',
  images: { domains: ['in.bmscdn.com', 'assets.in.bmscdn.com', 'www.district.in', 'firebasestorage.googleapis.com'] },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  async rewrites() {
    // Server-side proxy target. In Docker, Caddy intercepts /api/* before it
    // reaches Next, so this only matters for `next dev` and bare `next start`.
    const apiTarget =
      process.env.API_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000';
    return [
      { source: '/api/:path*', destination: `${apiTarget}/api/:path*` },
    ];
  },
};
module.exports = nextConfig;
