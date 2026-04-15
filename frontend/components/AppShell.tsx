"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

const publicPaths = new Set(["/", "/auth", "/login", "/register"]);

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

  if (!isReady) {
    return null;
  }

  const links: { href: Route; label: string }[] = [
    { href: "/dashboard", label: "דשבורד" },
    { href: "/teacher", label: "סוכן מורה" },
    { href: "/quiz", label: "מחולל שאלות" },
    { href: "/grader", label: "בודק תשובות" },
    { href: "/history", label: "היסטוריה" },
  ];

  return (
    <>
      {isAuthenticated && (
        <nav className="glass topbar">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
            <span className="brand">AI Learning System</span>
            <div className="nav-links">
              {links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`nav-link${pathname === link.href ? " active" : ""}`}
                >
                  {link.label}
                </Link>
              ))}
            </div>
            <button style={{ width: "auto" }} onClick={onLogout}>
              התנתקות
            </button>
          </div>
        </nav>
      )}
      {children}
    </>
  );
}
