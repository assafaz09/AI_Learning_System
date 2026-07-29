"use client";

import Link from "next/link";
import type { Route } from "next";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  apiFetch,
  createGroupLearningSession,
  errorMessage,
  getGroupLearningMessages,
  GroupLearningMessage,
  GroupLearningSession,
  listGroupLearningSessions,
  postGroupLearningMessage,
  uploadFiles
} from "../../lib/api";
import { handleComposerEnterKeyDown } from "../../lib/composerEnter";

type Doc = { id: number; name: string };
type SelectedDocsResponse = { document_ids: number[] };

function roleLabel(role: string): string {
  if (role === "novice") return "סוכן מתחיל";
  if (role === "intermediate") return "סוכן בינוני";
  if (role === "user") return "אתה";
  return role;
}

function sessionButtonLabel(s: GroupLearningSession): string {
  const t = s.title?.trim();
  return t || `שיחה #${s.id}`;
}

export default function GroupLearningPage() {
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [savedSessions, setSavedSessions] = useState<GroupLearningSession[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [nextSpeakerHint, setNextSpeakerHint] = useState<string>("");
  const [messages, setMessages] = useState<GroupLearningMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const chatCanvasRef = useRef<HTMLElement | null>(null);

  const loadDocs = useCallback(async () => {
    const [docs, sel] = await Promise.all([
      apiFetch<Doc[]>("/documents"),
      apiFetch<SelectedDocsResponse>("/documents/selected")
    ]);
    setDocuments(docs);
    setSelected(sel.document_ids);
  }, []);

  const loadSavedSessions = useCallback(async () => {
    const list = await listGroupLearningSessions();
    setSavedSessions(list);
  }, []);

  useEffect(() => {
    void loadDocs();
    void loadSavedSessions();
  }, [loadDocs, loadSavedSessions]);

  const refreshMessages = useCallback(async (sid: number) => {
    const res = await getGroupLearningMessages(sid);
    setMessages(res.messages);
  }, []);

  useEffect(() => {
    const el = chatCanvasRef.current;
    if (!el) {
      return;
    }
    el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const applyNextSpeakerHint = useCallback((next: string) => {
    setNextSpeakerHint(next === "novice" ? "התור הבא: סוכן מתחיל" : "התור הבא: סוכן בינוני");
  }, []);

  const resetSession = () => {
    setSessionId(null);
    setMessages([]);
    setNextSpeakerHint("");
    setStatus("");
  };

  const openSavedSession = async (s: GroupLearningSession) => {
    setStatus("");
    setSessionId(s.id);
    applyNextSpeakerHint(s.next_speaker);
    try {
      await apiFetch<SelectedDocsResponse>("/documents/selected", {
        method: "PUT",
        body: JSON.stringify({ document_ids: s.document_ids })
      });
      setSelected(s.document_ids);
      await loadDocs();
      await refreshMessages(s.id);
    } catch (e) {
      setStatus(errorMessage(e, "טעינת הסשן נכשלה"));
    }
  };

  const startSession = async () => {
    if (selected.length === 0) {
      setStatus("בחר לפחות מסמך אחד.");
      return;
    }
    setStarting(true);
    setStatus("");
    try {
      const sess = await createGroupLearningSession({
        document_ids: selected,
        title: "למידה בקבוצה"
      });
      setSessionId(sess.id);
      applyNextSpeakerHint(sess.next_speaker);
      setMessages([]);
      await loadSavedSessions();
    } catch (e) {
      setStatus(errorMessage(e, "לא ניתן לפתוח סשן"));
    } finally {
      setStarting(false);
    }
  };

  const toggleDoc = async (docId: number) => {
    const next = selected.includes(docId) ? selected.filter((id) => id !== docId) : [...selected, docId];
    setSelected(next);
    await apiFetch<SelectedDocsResponse>("/documents/selected", {
      method: "PUT",
      body: JSON.stringify({ document_ids: next })
    });
  };

  const sendMessage = async () => {
    if (!sessionId || !input.trim() || loading) return;
    setLoading(true);
    setStatus("");
    try {
      await postGroupLearningMessage(sessionId, input.trim());
      setInput("");
      await refreshMessages(sessionId);
      const sessions = await listGroupLearningSessions();
      setSavedSessions(sessions);
      const row = sessions.find((s) => s.id === sessionId);
      if (row) {
        applyNextSpeakerHint(row.next_speaker);
      }
    } catch (err) {
      setStatus(errorMessage(err, "שגיאה בשליחה"));
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await sendMessage();
  };

  const onUpload = async (files: FileList | null) => {
    if (!files?.length) return;
    setStatus("מעלה…");
    try {
      await uploadFiles("/documents/upload", Array.from(files));
      await loadDocs();
      setStatus("");
    } catch (e) {
      setStatus(errorMessage(e, "העלאה נכשלה"));
    }
  };

  const showPreSessionEmpty = !sessionId && messages.length === 0;
  const showSessionEmpty = Boolean(sessionId) && messages.length === 0;
  const canSend = Boolean(sessionId && input.trim() && !loading);

  return (
    <main className="teacher-chat-screen group-learning-screen">
      <aside id="group-learning-docs-rail" className="teacher-docs-rail" aria-label="מסמכים ושיחות">
        <div className="glass teacher-drawer-layout">
          <div className="teacher-drawer-header">
            <h3>מסמכים</h3>
          </div>

          <div className="teacher-drawer-fixed">
            <div className="import-section">
              <strong>העלאת קבצים</strong>
              <input
                type="file"
                multiple
                accept=".pdf,.txt,.md,.csv,.json"
                onChange={(ev) => void onUpload(ev.target.files)}
              />
            </div>

            <div className="import-section stack" style={{ gap: 8 }}>
              <button
                type="button"
                className="btn-secondary"
                disabled={starting || selected.length === 0}
                onClick={() => void startSession()}
              >
                {starting ? "פותח…" : "התחל סשן חדש"}
              </button>
              {sessionId ? (
                <p className="muted" style={{ margin: 0 }}>
                  סשן פעיל #{sessionId}
                </p>
              ) : null}
            </div>
          </div>

          <div className="teacher-drawer-scrollable">
            <strong style={{ fontSize: "0.92rem" }}>שיחות שמורות</strong>
            <div className="item-list">
              {savedSessions.length === 0 ? (
                <p className="muted" style={{ margin: 0 }}>
                  אין עדיין שיחות. שיחות נשמרות אוטומטית אחרי שתתחילו סשן.
                </p>
              ) : null}
              {savedSessions.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className={`btn-secondary teacher-conversation-btn${sessionId === s.id ? " active" : ""}`}
                  onClick={() => void openSavedSession(s)}
                >
                  {sessionButtonLabel(s)}
                </button>
              ))}
            </div>

            <strong style={{ fontSize: "0.92rem", display: "block", marginTop: 8 }}>מסמכים לסשן</strong>
            <div className="item-list">
              {documents.map((d) => (
                <div key={d.id} className="item-row teacher-doc-row">
                  <label className="teacher-doc-checkbox">
                    <input type="checkbox" checked={selected.includes(d.id)} onChange={() => void toggleDoc(d.id)} />
                    <span>{d.name}</span>
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>
      </aside>

      <div className="teacher-chat-main">
        <h1 className="group-learning-page-title">למידה בקבוצה</h1>
        <header className="teacher-floating-actions">
          <Link href={"/teacher" as Route} className="btn-secondary" style={{ textDecoration: "none" }}>
            חזרה למורה
          </Link>
          <button type="button" className="btn-secondary" disabled={!sessionId} onClick={resetSession}>
            סשן חדש
          </button>
        </header>

        {nextSpeakerHint ? (
          <p className="status" style={{ margin: "0 0 8px" }}>
            {nextSpeakerHint}
          </p>
        ) : null}

        <section
          ref={chatCanvasRef}
          className="teacher-chat-canvas"
          role="log"
          aria-live="polite"
          aria-label="שיחת קבוצה"
        >
          {showPreSessionEmpty ? (
            <div className="teacher-empty-state">
              <p style={{ fontSize: "1.05rem", fontWeight: 600, marginBottom: 12 }}>
                הסבירו חומר לשני סוכנים (מתחיל ובינוני) שמגיבים לסירוגין.
              </p>
              <p className="muted">
                בחרו מסמכים בסרגל משמאל, לחצו &quot;התחל סשן חדש&quot; או פתחו שיחה שמורה, ואז כתבו כאן את ההסבר
                שלכם.
              </p>
            </div>
          ) : null}
          {showSessionEmpty ? (
            <div className="teacher-empty-state">
              <p>זה המקום ללמוד עם הסוכנים</p>
              <p className="muted">התחילו בהסבר קצר על נושא שתרצו לחדד.</p>
            </div>
          ) : null}
          {messages.map((m) => (
            <article key={m.id} className={`chat-message ${m.role === "user" ? "user" : "assistant"}`}>
              <strong>{roleLabel(m.role)}</strong>
              <p>{m.content}</p>
            </article>
          ))}
        </section>

        <footer className="teacher-composer-wrap">
          <form className="teacher-composer" onSubmit={(e) => void onSubmit(e)}>
            <textarea
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => handleComposerEnterKeyDown(e, canSend)}
              placeholder={sessionId ? "הסבר נושא לסוכנים…" : "פתחו סשן משמאל כדי להתחיל"}
              disabled={!sessionId || loading}
            />
            <button type="submit" disabled={!sessionId || loading || !input.trim()}>
              {loading ? "…" : "שלח"}
            </button>
          </form>
          {status ? <p className="status">{status}</p> : null}
        </footer>
      </div>
    </main>
  );
}
