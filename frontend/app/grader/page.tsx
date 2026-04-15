"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";

type Question = { id: number; prompt: string };
type Quiz = { id: number; title: string; questions: Question[] };
type Grade = { score: number; feedback: string };

export default function GraderPage() {
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [grade, setGrade] = useState<Grade | null>(null);

  useEffect(() => {
    const quizId = localStorage.getItem("active_quiz_id");
    if (!quizId) return;
    apiFetch<Quiz>(`/quiz/${quizId}`).then(setQuiz).catch(() => undefined);
  }, []);

  const submit = async () => {
    if (!quiz) return;
    const result = await apiFetch<Grade>(`/quiz/${quiz.id}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers })
    });
    setGrade(result);
  };

  return (
    <main className="glass stack">
      <h2>סוכן בודק</h2>
      <p>ענו על השאלות שיצרתם ושלחו לבדיקה אוטומטית עם פידבק מיידי.</p>
      {!quiz && <p className="status">קודם צריך ליצור שאלון.</p>}
      {quiz?.questions.map((q) => (
        <div key={q.id} className="surface stack" style={{ gap: 8 }}>
          <p style={{ color: "var(--text)", fontWeight: 600 }}>{q.prompt}</p>
          <textarea rows={3} onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))} />
        </div>
      ))}
      <button onClick={submit}>שליחה לבדיקה</button>
      {grade && (
        <div className="surface stack" style={{ gap: 8 }}>
          <h3>ציון: {grade.score}</h3>
          <p>{grade.feedback}</p>
        </div>
      )}
    </main>
  );
}
