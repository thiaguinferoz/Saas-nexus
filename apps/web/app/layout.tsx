import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import "./globals.css";
import "./professional-refresh.css";
import "./nexus-landing.css";
import "./brand-system.css";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope" });
const interfaceFont = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Nexus — Conversas que viram negócios",
  description: "A Nexus usa inteligência artificial para atender, entender e transformar conversas no WhatsApp em novas oportunidades de negócio.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className={`${manrope.variable} ${interfaceFont.variable}`}>{children}</body>
    </html>
  );
}
