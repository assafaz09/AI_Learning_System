import "./globals.css";
import { ReactNode } from "react";
import AppShell from "../components/AppShell";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="he" dir="rtl">
      <body>
        <div className="page">
          <AppShell>{children}</AppShell>
        </div>
      </body>
    </html>
  );
}
