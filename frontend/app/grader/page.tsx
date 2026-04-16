"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/api";

type Question = { id: number; prompt: string; question_type: "open" | "mcq"; options: string[] };
type Quiz = { id: number; title: string; questions: Question[] };

export default function GraderPage() {
  const router = useRouter();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [status, setStatus] = useState("");

  useEffect(() => {
    const quizId = localStorage.getItem("active_quiz_id");
    if (!quizId) return;
    apiFetch<Quiz>(`/quiz/${quizId}`).then(setQuiz).catch(() => undefined);
  }, []);

  const submit = async () => {
    if (!quiz) return;
    setStatus("בודק את התשובות...");
    await apiFetch(`/quiz/${quiz.id}/submit`, { method: "POST", body: JSON.stringify({ answers }) });
    router.push(`/grader/feedback?quizId=${quiz.id}`);
  };

  return (
    <main className="glass stack">
      <h2>בחן את עצמך</h2>
      <p>ענו על השאלות שיצרתם ושלחו לבדיקה אוטומטית עם משוב מפורט לשיפור אמיתי.</p>
      {!quiz && <p className="status">קודם צריך ליצור שאלון.</p>}
      {quiz?.questions.map((q) => (
        <div key={q.id} className="surface stack" style={{ gap: 8 }}>
          <p style={{ color: "var(--text)", fontWeight: 600 }}>{q.prompt}</p>
          {q.question_type === "mcq" ? (
            <select onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}>
              <option value="">בחר/י תשובה</option>
              {q.options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          ) : (
            <textarea rows={3} onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))} />
          )}
        </div>
      ))}
      <button onClick={submit}>שליחה לבדיקה</button>
      {status ? <p className="status">{status}</p> : null}
    </main>
  );
}
