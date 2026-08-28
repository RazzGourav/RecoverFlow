/** @type {import('next').NextConfig} */
const nextConfig = {
  // Strict mode catches common React mistakes in development.
  reactStrictMode: true,

  // Standalone output bundles only what's needed to run the app.
  // Required for the Dockerfile.web multi-stage build (server.js).
  output: "standalone",

  // Expose the public API URL and payment provider mode to browser-side components.
  // Values prefixed NEXT_PUBLIC_ are bundled into the client at build time.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    // PAYMENT_PROVIDER is set in .env; we expose it as NEXT_PUBLIC so the client-side
    // provider badge (DataSourceBadge) can render without an extra network round-trip.
    NEXT_PUBLIC_PAYMENT_PROVIDER: process.env.PAYMENT_PROVIDER ?? "mock",
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
