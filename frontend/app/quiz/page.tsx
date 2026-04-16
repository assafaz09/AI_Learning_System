"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/api";

type Doc = { id: number; name: string };
type Quiz = {
  id: number;
  title: string;
  questions: { id: number; prompt: string; question_type: "open" | "mcq"; options: string[] }[];
};
type QuizQuestionType = "open" | "mcq";

export default function QuizPage() {
  const router = useRouter();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [status, setStatus] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [questionType, setQuestionType] = useState<QuizQuestionType | "">("");
  const canGenerate = selected.length > 0 && questionType !== "" && !isGenerating;

  useEffect(() => {
    apiFetch<Doc[]>("/documents").then(setDocs).catch(() => undefined);
  }, []);

  const generate = async () => {
    if (questionType === "") {
      setStatus("בחרו קודם סוג שאלון: פתוח או אמריקאי.");
      return;
    }
    setIsGenerating(true);
    setStatus("מייצר שאלון...");
    try {
      const data = await apiFetch<Quiz>("/quiz/generate", {
        method: "POST",
        body: JSON.stringify({ document_ids: selected, difficulty: "medium", question_count: 5, question_type: questionType })
      });
      setQuiz(data);
      localStorage.setItem("active_quiz_id", String(data.id));
      setStatus("השאלון נוצר בהצלחה. מוכנים לבחן את עצמך?");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "יצירת השאלון נכשלה.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <main className="grid quiz-page">
      {isGenerating ? (
        <div className="fullscreen-loader" role="status" aria-live="polite">
          <div className="fullscreen-loader-card">
            <div className="spinner-ring" />
            <h3>מחולל השאלות עובד עכשיו</h3>
            <p>אנחנו מנתחים את החומר שלך ובונים שאלון מותאם אישית.</p>
          </div>
        </div>
      ) : null}
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
        <label>
          סוג שאלות
          <select
            value={questionType}
            onChange={(e) => setQuestionType((e.target.value === "open" || e.target.value === "mcq" ? e.target.value : ""))}
          >
            <option value="">בחרו סוג שאלון</option>
            <option value="open">שאלות פתוחות</option>
            <option value="mcq">שאלות אמריקאיות</option>
          </select>
        </label>
        <button onClick={generate} disabled={!canGenerate}>
          צור שאלון
        </button>
        {status && <p className="status">{status}</p>}
      </section>
      <section className="glass stack">
        <h3>השלב הבא</h3>
        {!quiz ? <p className="surface">אחרי יצירת השאלון תוכלו לעבור לעמוד בחן את עצמך.</p> : null}
        {quiz ? (
          <div className="surface stack" style={{ gap: 10 }}>
            <p>השאלון מוכן. רוצים להתחיל לענות ולקבל משוב מפורט?</p>
            <button onClick={() => router.push("/grader")}>מעבר ל-בחן את עצמך</button>
          </div>
        ) : null}
      </section>
    </main>
  );
}
