import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/ui/Providers";
import cityConfig from "@/lib/city.config";
import "./globals.css";

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

// Absolute base for OG/Twitter image URLs. Without it Next falls back to
// http://localhost:3000 and every shared link previews a broken image.
// Order: explicit override → Vercel production domain → city.config domain.
function siteUrl(): URL {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL;
  if (explicit) return new URL(explicit);
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  if (vercel) return new URL(`https://${vercel}`);
  if (cityConfig.domain) return new URL(`https://${cityConfig.domain}`);
  return new URL("http://localhost:3000");
}

export const metadata: Metadata = {
  metadataBase: siteUrl(),
  title: cityConfig.brand,
  description: `Satellite-powered lake-health tracking for ${cityConfig.city}. Water area, algae levels, and health scores from Sentinel-2 imagery.`,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
