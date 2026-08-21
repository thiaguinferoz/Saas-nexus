import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope" });

export const metadata: Metadata = {
  title: "Nexus — Automações inteligentes para WhatsApp",
  description: "Conecte atendimento, inteligência artificial e automação em uma única experiência no WhatsApp.",
  icons: {
    icon: [{ url: "/nexus-brand.jfif", type: "image/jpeg" }],
    shortcut: "/nexus-brand.jfif",
    apple: "/nexus-brand.jfif",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className={manrope.variable}>{children}</body>
    </html>
  );
}
