"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch } from "../../../lib/api";

type FeedbackItem = {
  question_id: number;
  prompt: string;
  your_answer: string;
  expected_core: string;
  why: string;
  how_to_improve: string;
  accepted_semantically: boolean;
  score: number;
};

type GradeResponse = {
  score: number;
  feedback: string;
  feedback_items: FeedbackItem[];
};

export default function FeedbackPage() {
  const router = useRouter();
  const params = useSearchParams();
  const quizId = params.get("quizId");
  const [result, setResult] = useState<GradeResponse | null>(null);
  const [status, setStatus] = useState("טוען משוב...");

  useEffect(() => {
    if (!quizId) {
      setStatus("לא נמצא שאלון להצגת משוב.");
      return;
    }
    apiFetch<GradeResponse>(`/grading/${quizId}`)
      .then((data) => {
        setResult(data);
        setStatus("");
      })
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "טעינת המשוב נכשלה");
      });
  }, [quizId]);

  const summary = useMemo(() => {
    if (!result) return null;
    const strong = result.feedback_items.filter((item) => item.score >= 75).length;
    const improve = result.feedback_items.length - strong;
    return { strong, improve };
  }, [result]);

  return (
    <main className="stack">
      <section className="glass stack">
        <h2>המשוב שלך</h2>
        <p>המשוב מבוסס הבנה סמנטית: גם תשובה במילים אחרות יכולה להיות נכונה אם היא עונה על הרעיון.</p>
        {status ? <p className="status">{status}</p> : null}
        {result ? (
          <div className="surface stack" style={{ gap: 8 }}>
            <h3>ציון כולל: {result.score}</h3>
            <p>{result.feedback}</p>
            {summary ? (
              <p>
                עוצמות: {summary.strong} | לשיפור: {summary.improve}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>

      {result?.feedback_items.map((item) => (
        <section key={item.question_id} className="glass stack">
          <h3>שאלה {item.question_id}</h3>
          <p style={{ color: "var(--text)", fontWeight: 600 }}>{item.prompt}</p>
          <div className="surface stack" style={{ gap: 6 }}>
            <p>התשובה שלך: {item.your_answer}</p>
            <p>עיקרי תשובה מצופים: {item.expected_core}</p>
            <p>הערכת הבנה: {item.accepted_semantically ? "הבנת את הרעיון" : "נדרש חיזוק בהבנה"}</p>
            <p>למה: {item.why}</p>
            <p>איך לשפר: {item.how_to_improve}</p>
            <p>ציון לשאלה: {item.score}</p>
          </div>
        </section>
      ))}

      <section className="glass actions actions-two">
        <button onClick={() => router.push("/quiz")}>ליצירת שאלון חדש</button>
        <button className="btn-secondary" onClick={() => router.push("/grader")}>
          חזרה למענה על שאלון
        </button>
      </section>
    </main>
  );
}
