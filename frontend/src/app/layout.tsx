import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/ui/Providers";
import cityConfig from "@/lib/city.config";
import "./globals.css";

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
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
