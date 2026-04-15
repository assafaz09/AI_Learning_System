"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";

type HistoryData = {
  conversations: { id: number; title: string; created_at: string }[];
  quizzes: { id: number; title: string; created_at: string }[];
  grades: { id: number; quiz_id: number; score: number; created_at: string }[];
};

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryData | null>(null);

  useEffect(() => {
    apiFetch<HistoryData>("/history").then(setHistory).catch(() => undefined);
  }, []);

  return (
    <main className="grid">
      <section className="glass stack">
        <h3>שיחות</h3>
        <ul className="item-list">
          {history?.conversations.map((item) => (
            <li key={item.id} className="surface">{item.title}</li>
          )) || <li className="surface">אין שיחות עדיין</li>}
        </ul>
      </section>
      <section className="glass stack">
        <h3>שאלונים</h3>
        <ul className="item-list">
          {history?.quizzes.map((item) => (
            <li key={item.id} className="surface">{item.title}</li>
          )) || <li className="surface">אין שאלונים עדיין</li>}
        </ul>
      </section>
      <section className="glass stack">
        <h3>ציונים</h3>
        <ul className="item-list">
          {history?.grades.map((item) => (
            <li key={item.id} className="surface">שאלון {item.quiz_id}: {item.score}</li>
          )) || <li className="surface">אין ציונים עדיין</li>}
        </ul>
      </section>
    </main>
  );
}
