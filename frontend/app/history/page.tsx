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
  const [status, setStatus] = useState("טוען היסטוריה...");

  useEffect(() => {
    apiFetch<HistoryData>("/history")
      .then((data) => {
        setHistory(data);
        setStatus("");
      })
      .catch(() => {
        setStatus("טעינת ההיסטוריה נכשלה.");
      });
  }, []);

  const formatDate = (isoDate: string) =>
    new Intl.DateTimeFormat("he-IL", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(isoDate));

  return (
    <main className="history-layout">
      <section className="glass stack history-header">
        <h2>היסטוריה</h2>
        <p>כאן תמצאו את כל הפעילות שלכם: שיחות, שאלונים וציונים אחרונים.</p>
        {status ? <p className="status">{status}</p> : null}
      </section>

      <section className="glass stack history-column">
        <h3>שיחות</h3>
        <ul className="item-list history-list">
          {history?.conversations.map((item) => (
            <li key={item.id} className="surface history-card">
              <p className="history-title">{item.title}</p>
              <p className="history-meta">נוצר בתאריך: {formatDate(item.created_at)}</p>
            </li>
          )) || <li className="surface">אין שיחות עדיין</li>}
        </ul>
      </section>

      <section className="glass stack history-column">
        <h3>שאלונים</h3>
        <ul className="item-list history-list">
          {history?.quizzes.map((item) => (
            <li key={item.id} className="surface history-card">
              <p className="history-title">{item.title}</p>
              <p className="history-meta">נוצר בתאריך: {formatDate(item.created_at)}</p>
            </li>
          )) || <li className="surface">אין שאלונים עדיין</li>}
        </ul>
      </section>

      <section className="glass stack history-column">
        <h3>ציונים</h3>
        <ul className="item-list history-list">
          {history?.grades.map((item) => (
            <li key={item.id} className="surface history-card">
              <p className="history-title">שאלון #{item.quiz_id}</p>
              <p className="history-score">ציון: {item.score}</p>
              <p className="history-meta">עודכן בתאריך: {formatDate(item.created_at)}</p>
            </li>
          )) || <li className="surface">אין ציונים עדיין</li>}
        </ul>
      </section>
    </main>
  );
}
