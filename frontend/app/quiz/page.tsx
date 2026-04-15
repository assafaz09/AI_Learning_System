"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";

type Doc = { id: number; name: string };
type Question = { id: number; prompt: string };
type Quiz = { id: number; title: string; questions: Question[] };

export default function QuizPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    apiFetch<Doc[]>("/documents").then(setDocs).catch(() => undefined);
  }, []);

  const generate = async () => {
    setStatus("מייצר שאלון...");
    try {
      const data = await apiFetch<Quiz>("/quiz/generate", {
        method: "POST",
        body: JSON.stringify({ document_ids: selected, difficulty: "medium", question_count: 5 })
      });
      setQuiz(data);
      localStorage.setItem("active_quiz_id", String(data.id));
      setStatus("השאלון נוצר בהצלחה.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "יצירת השאלון נכשלה.");
    }
  };

  return (
    <main className="grid">
      <section className="glass stack">
        <h2>סוכן מחולל שאלות</h2>
        <p>בחרו מסמכים ולחצו על יצירה כדי לקבל שאלון מותאם אישי.</p>
        {docs.map((doc) => (
          <label key={doc.id} className="item-row">
            <input
              type="checkbox"
              checked={selected.includes(doc.id)}
              onChange={(e) => {
                if (e.target.checked) setSelected((prev) => [...prev, doc.id]);
                else setSelected((prev) => prev.filter((id) => id !== doc.id));
              }}
            />
            {doc.name}
          </label>
        ))}
        <button onClick={generate}>צור שאלון</button>
        {status && <p className="status">{status}</p>}
      </section>
      <section className="glass stack">
        <h3>שאלות שנוצרו</h3>
        <ul className="item-list">
          {quiz?.questions.map((q) => (
            <li key={q.id} className="surface">{q.prompt}</li>
          )) || <li className="surface">עדיין לא נוצר שאלון</li>}
        </ul>
      </section>
    </main>
  );
}
