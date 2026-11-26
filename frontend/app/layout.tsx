import type { Metadata, Viewport } from "next";
import { Outfit, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import Footer from "../components/Footer";
import Starfield from "../components/Starfield";
import ScrollToTop from "../components/ScrollToTop";

const outfit = Outfit({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-outfit",
  display: "swap",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-jakarta",
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "#06070a",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  title: "TicketFox — Real-Time Movie Ticket Drops & Premiere Alerts (BookMyShow & District)",
  description:
    "Ultra-fast real-time showtime detection and opening alerts for BookMyShow and District across India. Created by Y Sai Sandeep.",
  keywords: [
    "BookMyShow alerts",
    "movie tickets notification",
    "District tickets",
    "IMAX opening alerts",
    "TicketFox",
    "premiere show alert",
  ],
  authors: [{ name: "Y Sai Sandeep" }],
  icons: {
    icon: "/logo.jpg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${outfit.variable} ${jakarta.variable}`}>
      <body className="app-shell justify-between">
        <Starfield />
        <main className="flex-1 w-full">{children}</main>
        <Footer />
        <ScrollToTop />
      </body>
    </html>
  );
}
