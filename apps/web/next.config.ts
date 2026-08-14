import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  transpilePackages: ["@phij/contracts"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.INTERNAL_API_URL ?? "http://localhost:4000"}/api/:path*`,
      },
    ];
  },
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        {key: "X-Content-Type-Options", value: "nosniff"},
        {key: "X-Frame-Options", value: "DENY"},
        {key: "Referrer-Policy", value: "no-referrer"},
        {key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()"},
        {
          key: "Content-Security-Policy",
          value: "default-src 'self'; script-src 'self' 'unsafe-inline'; worker-src 'self' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self' http: https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        },
      ],
    }];
  },
};

export default config;
