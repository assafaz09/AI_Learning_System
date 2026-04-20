import "./globals.css";
import { Rubik } from "next/font/google";
import { ReactNode } from "react";
import AppShell from "../components/AppShell";

const siteFont = Rubik({
  subsets: ["latin", "hebrew"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-sans",
});

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="he" dir="rtl" className={siteFont.variable}>
      <body className={siteFont.className}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
