import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: { root: process.cwd() },
  reactCompiler: true,
  async rewrites() {
    // Vercel's project-level service routing owns /api in hosted deployments.
    if (process.env.VERCEL === "1") return [];
    const backend = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
};

export default nextConfig;
