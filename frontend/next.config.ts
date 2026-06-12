import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
      {
        source: "/frames/:path*",
        destination: `${backend}/frames/:path*`,
      },
      {
        source: "/assets/:path*",
        destination: `${backend}/assets/:path*`,
      },
    ];
  },
};

export default nextConfig;
