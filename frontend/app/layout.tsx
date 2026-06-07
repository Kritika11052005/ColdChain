import type { Metadata } from "next";
import { Inter, Syne } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const syne = Syne({
  variable: "--font-display",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ColdChain — Autonomous B2B Cold Outreach Pipeline",
  description: "Automate lookalike company discovery, decision-maker verification, and AI-personalized cold outreach in a cinematic dark-mode terminal UI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${syne.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#060A12] text-[#F5E6CA]">
        {children}
      </body>
    </html>
  );
}
