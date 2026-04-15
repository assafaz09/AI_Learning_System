"use client";

import { ChangeEvent, useEffect, useState } from "react";
import { apiFetch, uploadFiles } from "../../lib/api";

type Doc = { id: number; name: string };
type SelectedDocsResponse = { document_ids: number[] };

export default function TeacherPage() {
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [selectionStatus, setSelectionStatus] = useState("");
  const [chatStatus, setChatStatus] = useState("");
  const [loadingDocs, setLoadingDocs] = useState(false);

  const loadDocs = async () => {
    setLoadingDocs(true);
    try {
      const [docsData, selectedData] = await Promise.all([
        apiFetch<Doc[]>("/documents"),
        apiFetch<SelectedDocsResponse>("/documents/selected"),
      ]);
      setDocuments(docsData);
      setSelected(selectedData.document_ids);
    } finally {
      setLoadingDocs(false);
    }
  };

  const saveSelected = async (ids: number[]) => {
    const response = await apiFetch<SelectedDocsResponse>("/documents/selected", {
      method: "PUT",
      body: JSON.stringify({ document_ids: ids }),
    });
    setSelected(response.document_ids);
  };

  useEffect(() => {
    loadDocs().catch((error) => {
      setUploadStatus(error instanceof Error ? error.message : "שגיאה בטעינת מסמכים");
    });
  }, []);

  const onFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length === 0) {
      return;
    }
    setUploadStatus("מעלה מסמכים...");
    try {
      await uploadFiles("/documents/upload", files);
      await loadDocs();
      setUploadStatus(`הועלו בהצלחה ${files.length} מסמכים`);
    } catch (error) {
      setUploadStatus(error instanceof Error ? error.message : "העלאת המסמכים נכשלה");
    } finally {
      e.target.value = "";
    }
  };

  const ask = async () => {
    setChatStatus("המורה מעבד את השאלה...");
    try {
      const data = await apiFetch<{ answer: string }>("/teacher/chat", {
        method: "POST",
        body: JSON.stringify({ message: question, document_ids: selected }),
      });
      setAnswer(data.answer);
      setChatStatus("התקבלה תשובה");
    } catch (error) {
      setChatStatus(error instanceof Error ? error.message : "שליחת השאלה נכשלה");
    }
  };

  return (
    <main className="grid">
      <section className="glass stack">
        <h2>סוכן מורה</h2>
        <p>העלו חומרי לימוד, סמנו את המסמכים הפעילים, ושאלו את המורה שאלות מדויקות.</p>
        <input type="file" multiple accept=".pdf,.txt,.md,.csv,.json" onChange={onFileChange} />
        {uploadStatus && <p className="status">{uploadStatus}</p>}
        {loadingDocs && <p className="status">טוען מסמכים...</p>}
        <div className="item-list" style={{ marginTop: 12 }}>
          {documents.map((doc) => (
            <label key={doc.id} className="item-row">
              <input
                type="checkbox"
                checked={selected.includes(doc.id)}
                onChange={async (e) => {
                  const next = e.target.checked
                    ? [...selected, doc.id]
                    : selected.filter((id) => id !== doc.id);
                  setSelectionStatus("שומר בחירה...");
                  try {
                    await saveSelected(next);
                    setSelectionStatus("הבחירה נשמרה");
                  } catch (error) {
                    setSelectionStatus(error instanceof Error ? error.message : "שמירת הבחירה נכשלה");
                  }
                }}
              />
              {doc.name}
            </label>
          ))}
        </div>
        {selectionStatus && <p className="status">{selectionStatus}</p>}
      </section>
      <section className="glass stack">
        <h3>שיחה עם המורה</h3>
        <textarea rows={5} placeholder="שאלו שאלה על המסמכים שנבחרו" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button onClick={ask}>שליחת שאלה למורה</button>
        {chatStatus && <p className="status">{chatStatus}</p>}
        {answer && <div className="surface">{answer}</div>}
      </section>
    </main>
  );
}
