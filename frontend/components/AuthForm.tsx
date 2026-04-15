"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch, setAccessToken } from "../lib/api";

type Tokens = { access_token: string; refresh_token?: string };
type AuthMode = "login" | "register";

type AuthFormProps = {
  mode: AuthMode;
};

export default function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [result, setResult] = useState("");
  const isLogin = mode === "login";

  const submit = async (endpoint: "/auth/register" | "/auth/login", event: FormEvent) => {
    event.preventDefault();
    try {
      const tokens = await apiFetch<Tokens>(endpoint, {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      setAccessToken(tokens.access_token);
      setResult("ההתחברות בוצעה בהצלחה");
      router.replace("/dashboard");
    } catch (error) {
      setResult(error instanceof Error ? error.message : "הפעולה נכשלה");
    }
  };

  return (
    <main className="auth-layout">
      <section className="glass auth-card stack">
        <header className="stack" style={{ gap: 6 }}>
          <h2>{isLogin ? "התחברות" : "הרשמה"}</h2>
          <p>
            {isLogin
              ? "שמחים שחזרת. התחברו כדי להמשיך ללמידה האישית שלכם."
              : "צרו חשבון חדש ותתחילו ללמוד עם מורה חכם ותוכן מותאם."}
          </p>
        </header>
        <form className="stack" style={{ gap: 12 }}>
        <input placeholder="אימייל" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input placeholder="סיסמה" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button onClick={(e) => submit(isLogin ? "/auth/login" : "/auth/register", e)}>
          {isLogin ? "התחברות" : "יצירת חשבון"}
        </button>
        </form>
        {result && <p className="status">{result}</p>}
        <p className="status">
          {isLogin ? "עדיין אין חשבון?" : "כבר רשומים למערכת?"}{" "}
          <Link href={isLogin ? "/register" : "/login"} className="nav-link active">
            {isLogin ? "להרשמה" : "להתחברות"}
          </Link>
        </p>
      </section>
    </main>
  );
}
