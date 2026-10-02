import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/Nav";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Unified Entity Resolution Platform",
  description: "Multi-database entity resolution and unified data repository",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${mono.variable} min-h-screen font-sans antialiased`}>
        <div className="grid-overlay min-h-screen">
          <Nav />
          <main className="mx-auto max-w-7xl px-6 pb-16 pt-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
