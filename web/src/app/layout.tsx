import type { Metadata } from "next";
import { Geist, Geist_Mono, Source_Serif_4, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif-4",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "WaveScout — Surf Discovery from Space",
  description:
    "Satellite-based surf spot discovery for Nova Scotia. Using Sentinel-2 imagery and coastline geometry to find where waves break.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://wavescout.vercel.app"
  ),
  openGraph: {
    title: "WaveScout — Surf Discovery from Space",
    description:
      "Satellite-based surf spot discovery for Nova Scotia. Sentinel-2 imagery, coastline geometry, and ocean conditions.",
    siteName: "WaveScout",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "WaveScout — Surf Discovery from Space",
    description:
      "Satellite-based surf spot discovery for Nova Scotia.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${sourceSerif.variable} ${plexMono.variable} h-full antialiased`}
    >
      <head>
        <link
          href="https://api.mapbox.com/mapbox-gl-js/v3.4.0/mapbox-gl.css"
          rel="stylesheet"
        />
      </head>
      <body className="h-full flex flex-col">{children}</body>
    </html>
  );
}
