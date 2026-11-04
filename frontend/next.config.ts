import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import type { NextConfig } from "next";

// The README has you keep ONE .env at the repo root. Next.js only reads
// frontend/.env* on its own, so pull in the root file too. Anything already
// set (frontend/.env*, Vercel project settings, CI env) wins.
// (@next/env's loadEnvConfig can't be used here: it caches its first call,
// so a second call for another directory is silently a no-op.)
function loadRootEnv(): void {
  const file = path.resolve(process.cwd(), "..", ".env");
  if (!existsSync(file)) return;
  for (const raw of readFileSync(file, "utf8").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const m = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!m) continue;
    const [, key, rawValue] = m;
    let value = rawValue;
    const quoted = value.match(/^(['"])(.*)\1$/);
    if (quoted) value = quoted[2];
    else value = value.replace(/\s+#.*$/, "");
    if (process.env[key] === undefined) process.env[key] = value;
  }
}
loadRootEnv();

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
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
