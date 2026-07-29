"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useMemo, useState } from "react";

const publicPaths = new Set(["/", "/auth", "/login", "/register"]);

const links: { href: Route; label: string }[] = [
  { href: "/dashboard", label: "התקדמות" },
  { href: "/teacher", label: "המורה שלך" },
  { href: "/group-learning" as Route, label: "למידה בקבוצה" },
  { href: "/teacher/my-projects" as Route, label: "פרויקטים שלי" },
  { href: "/quiz", label: "צור שאלון" },
  { href: "/grader", label: "בחן את עצמך" },
  { href: "/history", label: "היסטוריה" },
];

function getIsraelGreeting(): string {
  const hour = new Date(
    new Date().toLocaleString("en-US", { timeZone: "Asia/Jerusalem" })
  ).getHours();
  if (hour >= 5 && hour < 12) return "בוקר טוב";
  if (hour >= 12 && hour < 17) return "צהריים טובים";
  if (hour >= 17 && hour < 21) return "ערב טוב";
  return "לילה טוב";
}

export default function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const authed = Boolean(token);
    setIsAuthenticated(authed);

    if (!authed && !publicPaths.has(pathname)) {
      router.replace("/");
      setIsReady(true);
      return;
    }

    if (authed && publicPaths.has(pathname)) {
      router.replace("/dashboard");
      setIsReady(true);
      return;
    }

    setIsReady(true);
  }, [pathname, router]);

  const onLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
    router.replace("/");
  };

  const greeting = useMemo(() => getIsraelGreeting(), []);

  if (!isReady) {
    return null;
  }

  if (!isAuthenticated) {
    return <div className="page">{children}</div>;
  }

  return (
    <div className="app-layout app-layout--topnav">
      <div className="app-content">
        <header className="mobile-topbar mobile-topbar--persistent">
          <div className="app-topbar-start">
            <span className="brand">AI Learning System</span>
            <span className="app-topbar-greeting">{greeting}</span>
          </div>
          <div className="app-topbar-end">
            <nav className="app-topbar-nav" aria-label="ניווט ראשי">
              {links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`sidebar-link${pathname === link.href ? " active" : ""}`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
            <button type="button" className="btn-secondary app-topbar-logout" onClick={onLogout}>
              התנתקות
            </button>
          </div>
        </header>
        <div className="page">
          {children}
        </div>
      </div>
    </div>
  );
}
