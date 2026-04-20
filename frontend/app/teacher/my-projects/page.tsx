"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  createSavedProject,
  deleteSavedProject,
  errorMessage,
  ExperienceBand,
  listSavedProjects,
  ProjectImportance,
  SavedProject,
  SavedProjectStatus,
  updateSavedProject
} from "../../../lib/api";
import {
  defaultSaveTitle,
  splitProjectSuggestions,
  TEACHER_PROJECT_DRAFT_STORAGE_KEY,
  TeacherProjectDraft
} from "../../../lib/projectIdeasUtils";

const STATUS_OPTIONS: { value: SavedProjectStatus; label: string }[] = [
  { value: "not_started", label: "לא התחילתי" },
  { value: "in_progress", label: "בתהליך" },
  { value: "done", label: "הושלם" }
];

const IMPORTANCE_OPTIONS: { value: ProjectImportance; label: string }[] = [
  { value: "low", label: "נמוכה" },
  { value: "medium", label: "בינונית" },
  { value: "high", label: "גבוהה" }
];

const EXPERIENCE_LABELS: Record<string, string> = {
  beginner_short: "מתחיל · עד כמה שעות",
  intermediate_days: "ביניים · כמה ימים",
  advanced_extended: "מעמיק · מורחב",
  manual: "ידני"
};

export default function MyProjectsPage() {
  const [projects, setProjects] = useState<SavedProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [draft, setDraft] = useState<TeacherProjectDraft | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftImportance, setDraftImportance] = useState<ProjectImportance>("medium");
  const [draftSaving, setDraftSaving] = useState(false);
  const [draftStatus, setDraftStatus] = useState("");

  const [manualTitle, setManualTitle] = useState("");
  const [manualDescription, setManualDescription] = useState("");
  const [manualImportance, setManualImportance] = useState<ProjectImportance>("medium");
  const [manualStatus, setManualStatus] = useState<SavedProjectStatus>("not_started");
  const [manualSaving, setManualSaving] = useState(false);
  const [manualStatusMsg, setManualStatusMsg] = useState("");

  const [expandedIds, setExpandedIds] = useState<Set<number>>(() => new Set());
  const [titleDraftById, setTitleDraftById] = useState<Record<number, string>>({});
  const [descDraftById, setDescDraftById] = useState<Record<number, string>>({});
  const [notesDraftById, setNotesDraftById] = useState<Record<number, string>>({});

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setListError("");
    try {
      const list = await listSavedProjects();
      setProjects(list);
      setTitleDraftById((prev) => {
        const next = { ...prev };
        for (const p of list) {
          if (next[p.id] === undefined) next[p.id] = p.title;
        }
        return next;
      });
      setDescDraftById((prev) => {
        const next = { ...prev };
        for (const p of list) {
          if (next[p.id] === undefined) next[p.id] = p.description ?? "";
        }
        return next;
      });
      setNotesDraftById((prev) => {
        const next = { ...prev };
        for (const p of list) {
          if (next[p.id] === undefined) next[p.id] = p.notes ?? "";
        }
        return next;
      });
    } catch (e) {
      setListError(errorMessage(e, "טעינת הפרויקטים נכשלה"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
    try {
      const raw = sessionStorage.getItem(TEACHER_PROJECT_DRAFT_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as TeacherProjectDraft;
        if (parsed?.suggestions_body && parsed.document_ids?.length) {
          setDraft(parsed);
          setDraftTitle(parsed.title || defaultSaveTitle(parsed.suggestions_body, parsed.learning_focus));
          setDraftImportance("medium");
        }
      }
    } catch {
      sessionStorage.removeItem(TEACHER_PROJECT_DRAFT_STORAGE_KEY);
    }
  }, [loadProjects]);

  const dismissDraft = () => {
    setDraft(null);
    sessionStorage.removeItem(TEACHER_PROJECT_DRAFT_STORAGE_KEY);
    setDraftStatus("");
  };

  const saveDraftWithImportance = async () => {
    if (!draft || !draftTitle.trim()) {
      setDraftStatus("יש להזין כותרת.");
      return;
    }
    setDraftSaving(true);
    setDraftStatus("");
    try {
      const created = await createSavedProject({
        kind: "ai",
        title: draftTitle.trim(),
        suggestions_body: draft.suggestions_body.trim(),
        learning_focus: draft.learning_focus.trim(),
        experience_band: draft.experience_band as ExperienceBand,
        document_ids: draft.document_ids
      });
      if (draftImportance !== "medium") {
        await updateSavedProject(created.id, { importance: draftImportance });
      }
      dismissDraft();
      await loadProjects();
    } catch (e) {
      setDraftStatus(errorMessage(e, "שמירה נכשלה"));
    } finally {
      setDraftSaving(false);
    }
  };

  const submitManual = async (e: FormEvent) => {
    e.preventDefault();
    if (!manualTitle.trim() || !manualDescription.trim()) {
      setManualStatusMsg("מלאו כותרת ותיאור.");
      return;
    }
    setManualSaving(true);
    setManualStatusMsg("");
    try {
      await createSavedProject({
        kind: "manual",
        title: manualTitle.trim(),
        description: manualDescription.trim(),
        importance: manualImportance,
        status: manualStatus
      });
      setManualTitle("");
      setManualDescription("");
      setManualImportance("medium");
      setManualStatus("not_started");
      await loadProjects();
      setManualStatusMsg("הפרויקט נוסף.");
    } catch (e) {
      setManualStatusMsg(errorMessage(e, "הוספה נכשלה"));
    } finally {
      setManualSaving(false);
    }
  };

  const onPatchImportance = async (id: number, importance: ProjectImportance) => {
    try {
      const u = await updateSavedProject(id, { importance });
      setProjects((prev) => prev.map((p) => (p.id === id ? u : p)));
    } catch (e) {
      setListError(errorMessage(e, "עדכון חשיבות נכשל"));
    }
  };

  const onPatchStatus = async (id: number, status: SavedProjectStatus) => {
    try {
      const u = await updateSavedProject(id, { status });
      setProjects((prev) => prev.map((p) => (p.id === id ? u : p)));
    } catch (e) {
      setListError(errorMessage(e, "עדכון סטטוס נכשל"));
    }
  };

  const onTitleBlur = async (p: SavedProject) => {
    const t = (titleDraftById[p.id] ?? "").trim();
    if (!t || t === p.title) return;
    try {
      const u = await updateSavedProject(p.id, { title: t });
      setProjects((prev) => prev.map((x) => (x.id === p.id ? u : x)));
    } catch (e) {
      setListError(errorMessage(e, "עדכון כותרת נכשל"));
    }
  };

  const onDescBlur = async (p: SavedProject) => {
    const d = descDraftById[p.id] ?? "";
    const server = p.description ?? "";
    if (d === server) return;
    try {
      const u = await updateSavedProject(p.id, { description: d || null });
      setProjects((prev) => prev.map((x) => (x.id === p.id ? u : x)));
    } catch (e) {
      setListError(errorMessage(e, "עדכון תיאור נכשל"));
    }
  };

  const onNotesBlur = async (p: SavedProject) => {
    const n = notesDraftById[p.id] ?? "";
    const server = p.notes ?? "";
    if (n === server) return;
    try {
      const u = await updateSavedProject(p.id, { notes: n });
      setProjects((prev) => prev.map((x) => (x.id === p.id ? u : x)));
    } catch (e) {
      setListError(errorMessage(e, "שמירת הערות נכשלה"));
    }
  };

  const onDelete = async (id: number) => {
    if (!window.confirm("למחוק פרויקט זה?")) return;
    try {
      await deleteSavedProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      setListError(errorMessage(e, "מחיקה נכשלה"));
    }
  };

  const toggleExpand = (id: number) => {
    setExpandedIds((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  };

  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [projects]
  );

  return (
    <main className="my-projects-page">
      <header className="my-projects-header glass">
        <div>
          <h1>פרויקטים שלי</h1>
          <p className="status my-projects-subtitle">
            מעקב אחרי פרויקטים מהמורה ופרויקטים שאתם מגדירים ידנית — סטטוס, חשיבות והתקדמות.
          </p>
        </div>
        <Link href="/teacher" className="btn-secondary">
          חזרה למורה
        </Link>
      </header>

      {draft ? (
        <section className="surface my-projects-draft" aria-label="טיוטה מהמורה">
          <h2>טיוטה חדשה מהמורה</h2>
          <p className="status">
            עברתם מהמסך הראשי עם הצעות AI. אפשר לערוך כותרת וחשיבות, ואז לשמור לרשימה שלכם.
          </p>
          <div className="my-projects-draft-grid">
            <label className="stack teacher-form-field">
              <span className="teacher-form-label">כותרת</span>
              <input
                type="text"
                className="surface"
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                disabled={draftSaving}
              />
            </label>
            <label className="stack teacher-form-field">
              <span className="teacher-form-label">חשיבות</span>
              <select
                className="surface"
                value={draftImportance}
                onChange={(e) => setDraftImportance(e.target.value as ProjectImportance)}
                disabled={draftSaving}
              >
                {IMPORTANCE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="status my-projects-draft-meta">
            מיקוד: {draft.learning_focus} ·{" "}
            {EXPERIENCE_LABELS[draft.experience_band] ?? draft.experience_band}
          </p>
          <div className="teacher-suggestion-cards my-projects-draft-preview">
            {splitProjectSuggestions(draft.suggestions_body).map((block, idx) => (
              <article key={`draft-${idx}`} className="surface teacher-suggestion-card">
                <h4 className="teacher-suggestion-card-title">{block.title}</h4>
                <div className="teacher-suggestion-card-body">{block.body}</div>
              </article>
            ))}
          </div>
          <div className="my-projects-draft-actions">
            <button type="button" disabled={draftSaving || !draftTitle.trim()} onClick={saveDraftWithImportance}>
              {draftSaving ? "שומר..." : "שמור בפרויקטים שלי"}
            </button>
            <button type="button" className="btn-secondary" onClick={dismissDraft} disabled={draftSaving}>
              בטל טיוטה
            </button>
          </div>
          {draftStatus ? <p className="status">{draftStatus}</p> : null}
        </section>
      ) : null}

      <section className="surface my-projects-manual">
        <h2>הוספת פרויקט ידני</h2>
        <p className="status">דברים שכבר עשיתם או שרוצים לעשות — עם תיאור, חשיבות וסטטוס.</p>
        <form className="my-projects-manual-form" onSubmit={submitManual}>
          <label className="stack teacher-form-field">
            <span className="teacher-form-label">כותרת</span>
            <input
              type="text"
              className="surface"
              value={manualTitle}
              onChange={(e) => setManualTitle(e.target.value)}
              disabled={manualSaving}
            />
          </label>
          <label className="stack teacher-form-field">
            <span className="teacher-form-label">תיאור</span>
            <textarea
              rows={3}
              className="surface"
              value={manualDescription}
              onChange={(e) => setManualDescription(e.target.value)}
              disabled={manualSaving}
            />
          </label>
          <div className="my-projects-manual-row">
            <label className="stack teacher-form-field">
              <span className="teacher-form-label">חשיבות</span>
              <select
                className="surface"
                value={manualImportance}
                onChange={(e) => setManualImportance(e.target.value as ProjectImportance)}
                disabled={manualSaving}
              >
                {IMPORTANCE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="stack teacher-form-field">
              <span className="teacher-form-label">סטטוס</span>
              <select
                className="surface"
                value={manualStatus}
                onChange={(e) => setManualStatus(e.target.value as SavedProjectStatus)}
                disabled={manualSaving}
              >
                {STATUS_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <button type="submit" className="btn-secondary" disabled={manualSaving}>
            {manualSaving ? "מוסיף..." : "הוסף פרויקט"}
          </button>
        </form>
        {manualStatusMsg ? <p className="status">{manualStatusMsg}</p> : null}
      </section>

      <section className="my-projects-list-section">
        <h2>הפרויקטים שלכם</h2>
        {listError ? <p className="status">{listError}</p> : null}
        {loading ? (
          <p className="status">
            <span className="spinner-inline" /> טוען...
          </p>
        ) : sortedProjects.length === 0 ? (
          <p className="status">אין פרויקטים עדיין. הוסיפו ידנית או שמרו טיוטה מהמורה.</p>
        ) : (
          <ul className="my-projects-cards">
            {sortedProjects.map((p) => (
              <li key={p.id} className="surface my-projects-card">
                <div className="my-projects-card-head">
                  <span className={`my-projects-kind-badge kind-${p.kind}`}>
                    {p.kind === "ai" ? "מהמורה" : "ידני"}
                  </span>
                  <div className="my-projects-card-actions">
                    {p.kind === "ai" && p.suggestions_body.trim() ? (
                      <button type="button" className="btn-secondary" onClick={() => toggleExpand(p.id)}>
                        {expandedIds.has(p.id) ? "הסתר הצעות" : "הצג הצעות"}
                      </button>
                    ) : null}
                    <button type="button" className="btn-secondary teacher-saved-delete-btn" onClick={() => onDelete(p.id)}>
                      מחק
                    </button>
                  </div>
                </div>
                <label className="stack teacher-form-field">
                  <span className="teacher-form-label">כותרת</span>
                  <input
                    type="text"
                    className="surface"
                    value={titleDraftById[p.id] ?? p.title}
                    onChange={(e) => setTitleDraftById((prev) => ({ ...prev, [p.id]: e.target.value }))}
                    onBlur={() => onTitleBlur(p)}
                  />
                </label>
                <label className="stack teacher-form-field">
                  <span className="teacher-form-label">תיאור / הערות קצרות</span>
                  <textarea
                    rows={2}
                    className="surface"
                    placeholder={p.kind === "manual" ? "תיאור הפרויקט" : "תיאור נוסף (אופציונלי)"}
                    value={descDraftById[p.id] ?? ""}
                    onChange={(e) => setDescDraftById((prev) => ({ ...prev, [p.id]: e.target.value }))}
                    onBlur={() => onDescBlur(p)}
                  />
                </label>
                <div className="my-projects-card-row">
                  <label className="stack teacher-form-field">
                    <span className="teacher-form-label">חשיבות</span>
                    <select
                      className="surface"
                      value={p.importance}
                      onChange={(e) => onPatchImportance(p.id, e.target.value as ProjectImportance)}
                    >
                      {IMPORTANCE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="stack teacher-form-field">
                    <span className="teacher-form-label">סטטוס</span>
                    <select
                      className="surface"
                      value={p.status}
                      onChange={(e) => onPatchStatus(p.id, e.target.value as SavedProjectStatus)}
                    >
                      {STATUS_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="stack teacher-form-field">
                  <span className="teacher-form-label">הערות מעקב (יומן)</span>
                  <textarea
                    rows={2}
                    className="surface"
                    value={notesDraftById[p.id] ?? ""}
                    onChange={(e) => setNotesDraftById((prev) => ({ ...prev, [p.id]: e.target.value }))}
                    onBlur={() => onNotesBlur(p)}
                  />
                </label>
                {p.kind === "ai" ? (
                  <p className="status my-projects-card-meta">
                    מיקוד למידה: {p.learning_focus} · {EXPERIENCE_LABELS[p.experience_band] ?? p.experience_band} ·{" "}
                    {new Date(p.created_at).toLocaleDateString("he-IL")}
                  </p>
                ) : (
                  <p className="status my-projects-card-meta">
                    נוצר {new Date(p.created_at).toLocaleDateString("he-IL")}
                  </p>
                )}
                {p.kind === "ai" && expandedIds.has(p.id) && p.suggestions_body.trim() ? (
                  <div className="teacher-suggestion-cards my-projects-expand-cards">
                    {splitProjectSuggestions(p.suggestions_body).map((block, idx) => (
                      <article key={`p-${p.id}-${idx}`} className="surface teacher-suggestion-card">
                        <h4 className="teacher-suggestion-card-title">{block.title}</h4>
                        <div className="teacher-suggestion-card-body">{block.body}</div>
                      </article>
                    ))}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
