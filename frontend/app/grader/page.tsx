"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/api";
import { handleComposerEnterKeyDown } from "../../lib/composerEnter";

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

  const submit = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!quiz || status) return;
    setStatus("בודק את התשובות...");
    await apiFetch(`/quiz/${quiz.id}/submit`, { method: "POST", body: JSON.stringify({ answers }) });
    router.push(`/grader/feedback?quizId=${quiz.id}`);
  };

  const canSubmitGrader = Boolean(quiz && !status);

  return (
    <main className="glass stack">
      <h2>בחן את עצמך</h2>
      <p>ענו על השאלות שיצרתם ושלחו לבדיקה אוטומטית עם משוב מפורט לשיפור אמיתי.</p>
      {!quiz && <p className="status">קודם צריך ליצור שאלון.</p>}
      <form className="stack" style={{ gap: 18 }} onSubmit={(ev) => void submit(ev)}>
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
              <textarea
                rows={3}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                onKeyDown={(e) => handleComposerEnterKeyDown(e, canSubmitGrader)}
              />
            )}
          </div>
        ))}
        <button type="submit" disabled={!quiz || Boolean(status)}>
          שליחה לבדיקה
        </button>
      </form>
      {status ? <p className="status">{status}</p> : null}
    </main>
  );
}
