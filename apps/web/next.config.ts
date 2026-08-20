import type { NextConfig } from "next";

/**
 * RecoverFlow Next.js configuration.
 *
 * Why: Centralises Next.js settings so environment-specific behaviour
 * (API URL rewrites, image domains, etc.) is managed in one place
 * rather than scattered across components.
 */
const nextConfig: NextConfig = {
  // Strict mode catches common React mistakes in development.
  reactStrictMode: true,

  // Standalone output bundles only what's needed to run the app.
  // Required for the Dockerfile.web multi-stage build (server.js).
  output: "standalone",

  // Expose the public API URL to browser-side components.
  // Values prefixed NEXT_PUBLIC_ are bundled into the client.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  },

  // Rewrites so the browser calls /api/* and we proxy to the FastAPI service.
  // This avoids CORS issues in development and keeps API URLs clean.
  async rewrites() {
    const apiUrl =
      process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://api:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
