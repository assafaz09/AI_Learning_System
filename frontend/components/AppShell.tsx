"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useMemo, useState } from "react";

const publicPaths = new Set(["/", "/auth", "/login", "/register"]);

const links: { href: Route; label: string }[] = [
  { href: "/dashboard", label: "בית" },
  { href: "/teacher", label: "המורה שלך" },
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
  const [sidebarOpen, setSidebarOpen] = useState(false);

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

  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

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
    <div className="app-layout">
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={`sidebar${sidebarOpen ? " open" : ""}`}>
        <div className="sidebar-brand">AI Learning System</div>
        <div className="sidebar-greeting">
          {greeting}
        </div>

        <nav className="sidebar-nav">
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

        <div className="sidebar-footer">
          <button className="sidebar-logout-btn" onClick={onLogout}>
            התנתקות
          </button>
        </div>
      </aside>

      <div className="app-content">
        <header className="mobile-topbar">
          <button
            type="button"
            className="sidebar-toggle"
            onClick={() => setSidebarOpen((p) => !p)}
            aria-label="תפריט"
          >
            <span /><span /><span />
          </button>
          <span className="brand">AI Learning System</span>
        </header>
        <div className="page">
          {children}
        </div>
      </div>
    </div>
  );
}
