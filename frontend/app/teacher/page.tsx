"use client";

import Link from "next/link";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  apiFetch,
  deleteDocument,
  errorMessage,
  ExperienceBand,
  fetchPodcastAudioBlob,
  getConversationMessages,
  getPodcastList,
  PodcastItem,
  streamPodcastGeneration,
  streamTeacherChat,
  suggestLearningProjects,
  TeacherMessage,
  uploadFiles
} from "../../lib/api";
import {
  defaultSaveTitle,
  splitProjectSuggestions,
  TEACHER_PROJECT_DRAFT_STORAGE_KEY,
  TeacherProjectDraft
} from "../../lib/projectIdeasUtils";

const IMPORT_PROGRESS_MESSAGES = [
  "מתחבר למקור...",
  "מוריד תוכן...",
  "מעבד ומנתח...",
  "מתמלל אודיו (עשוי לקחת דקה)...",
  "מאנדקס את התוכן...",
  "כמעט סיימנו...",
];

type Doc = {
  id: number;
  name: string;
  source_type?: "file" | "web" | "youtube";
  source_url?: string | null;
};
type SelectedDocsResponse = { document_ids: number[] };
type Conversation = { id: number; title: string; created_at: string };
type HistoryResponse = { conversations: Conversation[] };

type TeacherToolTab = "podcast" | "quiz" | "chats" | "projects" | "roadmap";

const EXPERIENCE_BAND_OPTIONS: { value: ExperienceBand; label: string }[] = [
  { value: "beginner_short", label: "מתחיל · עד כמה שעות" },
  { value: "intermediate_days", label: "ביניים · כמה ימים" },
  { value: "advanced_extended", label: "מעמיק · פרויקט מורחב" }
];

const TEACHER_ROADMAP_ITEMS: { title: string; detail: string }[] = [
  { title: "הרחבת מצבי למידה", detail: "בפיתוח" },
  { title: "ייצוא שיחות", detail: "בתכנון" },
];

export default function TeacherPage() {
  const router = useRouter();

  const getSourceLabel = (doc: Doc) => {
    if (doc.source_type === "youtube") {
      return "YouTube";
    }
    if (doc.source_type === "web") {
      return "Web";
    }
    return "File";
  };

  const [documents, setDocuments] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<TeacherMessage[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [uploadStatus, setUploadStatus] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceStatus, setSourceStatus] = useState("");
  const [selectionStatus, setSelectionStatus] = useState("");
  const [chatStatus, setChatStatus] = useState("");
  const [deleteStatus, setDeleteStatus] = useState("");
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeToolTab, setActiveToolTab] = useState<TeacherToolTab>("chats");
  const [isImporting, setIsImporting] = useState(false);
  const [importProgress, setImportProgress] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [podcasts, setPodcasts] = useState<PodcastItem[]>([]);
  const [isGeneratingPodcast, setIsGeneratingPodcast] = useState(false);
  const [podcastProgress, setPodcastProgress] = useState("");
  const [podcastModalOpen, setPodcastModalOpen] = useState(false);
  const [podcastDocIds, setPodcastDocIds] = useState<number[]>([]);
  const [playingPodcastId, setPlayingPodcastId] = useState<number | null>(null);
  const [podcastAudioObjectUrl, setPodcastAudioObjectUrl] = useState<string | null>(null);
  const [podcastAudioLoading, setPodcastAudioLoading] = useState(false);
  const [podcastAudioError, setPodcastAudioError] = useState("");
  const podcastAudioUrlRef = useRef<string | null>(null);
  const streamAnchorRef = useRef<HTMLDivElement | null>(null);
  const importTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [projectFocus, setProjectFocus] = useState("");
  const [projectBand, setProjectBand] = useState<ExperienceBand>("beginner_short");
  const [projectSuggestions, setProjectSuggestions] = useState("");
  const [projectStatus, setProjectStatus] = useState("");
  const [projectLoading, setProjectLoading] = useState(false);
  const [saveTitleDraft, setSaveTitleDraft] = useState("");
  const [showTransferPrompt, setShowTransferPrompt] = useState(false);

  const startImportProgress = useCallback(() => {
    let step = 0;
    setImportProgress(IMPORT_PROGRESS_MESSAGES[0]);
    importTimerRef.current = setInterval(() => {
      step = Math.min(step + 1, IMPORT_PROGRESS_MESSAGES.length - 1);
      setImportProgress(IMPORT_PROGRESS_MESSAGES[step]);
    }, 4000);
  }, []);

  const stopImportProgress = useCallback(() => {
    if (importTimerRef.current) {
      clearInterval(importTimerRef.current);
      importTimerRef.current = null;
    }
    setImportProgress("");
  }, []);

  const canAsk = useMemo(
    () => question.trim().length > 0 && selected.length > 0 && !isStreaming,
    [question, selected, isStreaming]
  );

  const canSuggestProjects = useMemo(
    () => projectFocus.trim().length > 0 && selected.length > 0 && !projectLoading,
    [projectFocus, selected, projectLoading]
  );

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

  const loadConversations = async () => {
    const history = await apiFetch<HistoryResponse>("/history");
    setConversations(history.conversations);
  };

  const loadConversationMessages = async (conversationId: number) => {
    setLoadingConversation(true);
    try {
      const data = await getConversationMessages(conversationId);
      setMessages(data.messages);
      setCurrentConversationId(data.conversation_id);
    } catch (error) {
      setChatStatus(errorMessage(error, "טעינת היסטוריית השיחה נכשלה"));
    } finally {
      setLoadingConversation(false);
    }
  };

  const saveSelected = async (ids: number[]) => {
    const response = await apiFetch<SelectedDocsResponse>("/documents/selected", {
      method: "PUT",
      body: JSON.stringify({ document_ids: ids }),
    });
    setSelected(response.document_ids);
  };

  const loadPodcasts = async () => {
    try {
      const list = await getPodcastList();
      setPodcasts(list);
    } catch {
      // silent — podcast list is not critical
    }
  };

  useEffect(() => {
    Promise.all([loadDocs(), loadConversations(), loadPodcasts()]).catch((error) => {
      setUploadStatus(errorMessage(error, "שגיאה בטעינת נתונים"));
    });
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!playingPodcastId || isGeneratingPodcast) {
      if (podcastAudioUrlRef.current) {
        URL.revokeObjectURL(podcastAudioUrlRef.current);
        podcastAudioUrlRef.current = null;
      }
      setPodcastAudioObjectUrl(null);
      setPodcastAudioLoading(false);
      setPodcastAudioError("");
      return;
    }

    setPodcastAudioLoading(true);
    setPodcastAudioError("");
    setPodcastAudioObjectUrl(null);

    fetchPodcastAudioBlob(playingPodcastId)
      .then((blob) => {
        if (cancelled) return;
        if (podcastAudioUrlRef.current) {
          URL.revokeObjectURL(podcastAudioUrlRef.current);
        }
        const url = URL.createObjectURL(blob);
        podcastAudioUrlRef.current = url;
        setPodcastAudioObjectUrl(url);
      })
      .catch((error) => {
        if (!cancelled) {
          setPodcastAudioError(errorMessage(error, "טעינת האודיו נכשלה"));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setPodcastAudioLoading(false);
        }
      });

    return () => {
      cancelled = true;
      if (podcastAudioUrlRef.current) {
        URL.revokeObjectURL(podcastAudioUrlRef.current);
        podcastAudioUrlRef.current = null;
      }
    };
  }, [playingPodcastId, isGeneratingPodcast]);

  useEffect(() => {
    if (!streamAnchorRef.current) {
      return;
    }
    streamAnchorRef.current.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages, isStreaming]);

  const onFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const files: File[] = e.target.files ? Array.from(e.target.files as FileList) : [];
    if (files.length === 0) {
      return;
    }
    setIsUploading(true);
    setUploadStatus("");
    try {
      await uploadFiles("/documents/upload", files);
      await loadDocs();
      setUploadStatus(`הועלו בהצלחה ${files.length} מסמכים`);
    } catch (error) {
      setUploadStatus(errorMessage(error, "העלאת המסמכים נכשלה"));
    } finally {
      setIsUploading(false);
      e.target.value = "";
    }
  };

  const importExternalSource = async () => {
    if (!sourceUrl.trim()) {
      setSourceStatus("יש להזין קישור תקין.");
      return;
    }
    setIsImporting(true);
    setSourceStatus("");
    startImportProgress();
    try {
      await apiFetch("/documents/import-url", {
        method: "POST",
        body: JSON.stringify({ url: sourceUrl.trim() })
      });
      setSourceUrl("");
      await loadDocs();
      setSourceStatus("המקור החיצוני נוסף בהצלחה.");
    } catch (error) {
      setSourceStatus(errorMessage(error, "ייבוא מקור חיצוני נכשל"));
    } finally {
      setIsImporting(false);
      stopImportProgress();
    }
  };

  const ask = async (event: FormEvent) => {
    event.preventDefault();
    if (!canAsk) {
      return;
    }
    const trimmedQuestion = question.trim();
    const tempUserMessageId = -Date.now();
    const tempAssistantMessageId = tempUserMessageId - 1;

    setMessages((prev) => [
      ...prev,
      {
        id: tempUserMessageId,
        role: "user",
        content: trimmedQuestion,
        created_at: new Date().toISOString()
      },
      {
        id: tempAssistantMessageId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString()
      }
    ]);
    setQuestion("");
    setIsStreaming(true);
    setChatStatus("שולח הודעה...");

    let nextConversationId = currentConversationId;
    let streamErrorMessage = "";
    try {
      await streamTeacherChat(
        {
          message: trimmedQuestion,
          document_ids: selected,
          conversation_id: currentConversationId
        },
        {
          onDelta: (delta) => {
            setChatStatus("המורה מקליד...");
            setMessages((prev) =>
              prev.map((message) =>
                message.id === tempAssistantMessageId
                  ? { ...message, content: `${message.content}${delta}` }
                  : message
              )
            );
          },
          onDone: (conversationId) => {
            nextConversationId = conversationId;
          },
          onError: (detail) => {
            streamErrorMessage = detail;
          }
        }
      );

      if (streamErrorMessage) {
        throw new Error(streamErrorMessage);
      }

      if (nextConversationId !== null) {
        setCurrentConversationId(nextConversationId);
      }
      await loadConversations();
      setChatStatus("התקבלה תשובה");
    } catch (error) {
      const detail = errorMessage(error, "שליחת השאלה נכשלה");
      setMessages((prev) =>
        prev.map((message) =>
          message.id === tempAssistantMessageId && !message.content
            ? { ...message, content: `שגיאה: ${detail}` }
            : message
        )
      );
      setChatStatus(detail);
    } finally {
      setIsStreaming(false);
    }
  };

  const onDeleteDocument = async (documentId: number) => {
    setDeleteStatus("מוחק מסמך...");
    try {
      await deleteDocument(documentId);
      const nextSelected = selected.filter((id) => id !== documentId);
      setSelected(nextSelected);
      await Promise.all([loadDocs(), loadConversations()]);
      setDeleteStatus("המסמך נמחק בהצלחה");
    } catch (error) {
      setDeleteStatus(errorMessage(error, "מחיקת המסמך נכשלה"));
    }
  };

  const startNewConversation = () => {
    setCurrentConversationId(null);
    setMessages([]);
    setChatStatus("");
  };

  const openPodcastModal = () => {
    setPodcastDocIds([...selected]);
    setPodcastModalOpen(true);
  };

  const submitProjectIdeas = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSuggestProjects) {
      return;
    }
    setProjectLoading(true);
    setProjectStatus("");
    setProjectSuggestions("");
    setShowTransferPrompt(false);
    try {
      const res = await suggestLearningProjects({
        learning_focus: projectFocus.trim(),
        experience_band: projectBand,
        document_ids: selected
      });
      setProjectSuggestions(res.suggestions);
      setSaveTitleDraft(defaultSaveTitle(res.suggestions, projectFocus.trim()));
      setProjectStatus("התקבלו הצעות");
      setShowTransferPrompt(true);
    } catch (error) {
      setProjectStatus(errorMessage(error, "בקשת הצעות הפרויקטים נכשלה"));
    } finally {
      setProjectLoading(false);
    }
  };

  const goToMyProjectsWithDraft = () => {
    if (!projectSuggestions.trim() || selected.length === 0) {
      setProjectStatus("יש תוצאות ומסמכים נבחרים כדי להעביר טיוטה.");
      return;
    }
    const title = saveTitleDraft.trim() || defaultSaveTitle(projectSuggestions, projectFocus.trim());
    const draft: TeacherProjectDraft = {
      title,
      suggestions_body: projectSuggestions.trim(),
      learning_focus: projectFocus.trim(),
      experience_band: projectBand,
      document_ids: [...selected]
    };
    sessionStorage.setItem(TEACHER_PROJECT_DRAFT_STORAGE_KEY, JSON.stringify(draft));
    setShowTransferPrompt(false);
    router.push("/teacher/my-projects" as Route);
  };

  const generatePodcast = async () => {
    if (podcastDocIds.length === 0) return;
    setPodcastModalOpen(false);
    setIsGeneratingPodcast(true);
    setPodcastProgress("מתחיל ליצור פודקאסט...");

    try {
      await streamPodcastGeneration(podcastDocIds, {
        onProgress: (message) => setPodcastProgress(message),
        onDone: (podcastId) => {
          setPlayingPodcastId(podcastId);
          loadPodcasts();
        },
        onError: (detail) => {
          setPodcastProgress(`שגיאה: ${detail}`);
        },
      });
    } catch (error) {
      setPodcastProgress(errorMessage(error, "יצירת הפודקאסט נכשלה"));
    } finally {
      setIsGeneratingPodcast(false);
    }
  };

  const formatDuration = (seconds: number) => {
    if (!Number.isFinite(seconds) || seconds <= 0) {
      return "0:00";
    }
    const totalSec = Math.round(seconds);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const toolTabBtn = (id: TeacherToolTab, label: string, panelId: string) => (
    <button
      type="button"
      role="tab"
      id={`teacher-tab-${id}`}
      aria-selected={activeToolTab === id}
      aria-controls={panelId}
      className={`btn-secondary teacher-tool-tab${activeToolTab === id ? " active" : ""}`}
      onClick={() => setActiveToolTab(id)}
    >
      {label}
    </button>
  );

  return (
    <main className="teacher-chat-screen">
      <aside id="teacher-docs-rail" className="teacher-docs-rail" aria-label="מסמכים">
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
                onChange={onFileChange}
                disabled={isUploading || isImporting}
              />
              {isUploading && (
                <div className="import-progress-bar">
                  <div className="import-progress-indicator">
                    <span className="spinner-inline" />
                    <span>מעלה מסמכים...</span>
                  </div>
                </div>
              )}
            </div>

            <div className="import-section">
              <strong>ייבוא מקישור</strong>
              <input
                placeholder="הדביקו קישור YouTube או אתר אינטרנט"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                disabled={isImporting}
              />
              <button
                type="button"
                className={isImporting ? "btn-importing" : ""}
                onClick={importExternalSource}
                disabled={isStreaming || isImporting}
              >
                {isImporting ? (
                  <span className="btn-loading-content">
                    <span className="spinner-inline" />
                    <span>מייבא...</span>
                  </span>
                ) : (
                  "ייבוא מקור חיצוני"
                )}
              </button>
              {isImporting && importProgress && (
                <div className="import-progress-bar">
                  <div className="import-progress-track">
                    <div className="import-progress-fill" />
                  </div>
                  <div className="import-progress-indicator">
                    <span>{importProgress}</span>
                  </div>
                </div>
              )}
            </div>

            {uploadStatus && !isUploading && <p className="status">{uploadStatus}</p>}
            {sourceStatus && !isImporting && <p className="status">{sourceStatus}</p>}
          </div>

          <div className="teacher-drawer-scrollable">
            {deleteStatus && <p className="status">{deleteStatus}</p>}
            {loadingDocs && <p className="status">טוען מסמכים...</p>}
            <div className="item-list">
              {documents.map((doc) => (
                <div key={doc.id} className="item-row teacher-doc-row">
                  <label className="teacher-doc-checkbox">
                    <input
                      type="checkbox"
                      checked={selected.includes(doc.id)}
                      disabled={isStreaming}
                      onChange={async (e) => {
                        const next = e.target.checked
                          ? [...selected, doc.id]
                          : selected.filter((id) => id !== doc.id);
                        setSelectionStatus("שומר בחירה...");
                        try {
                          await saveSelected(next);
                          setSelectionStatus("הבחירה נשמרה");
                        } catch (error) {
                          setSelectionStatus(errorMessage(error, "שמירת הבחירה נכשלה"));
                        }
                      }}
                    />
                    <span>
                      {doc.name} <small>({getSourceLabel(doc)})</small>
                    </span>
                  </label>
                  <button
                    type="button"
                    className="btn-secondary teacher-delete-btn"
                    disabled={isStreaming}
                    onClick={() => onDeleteDocument(doc.id)}
                  >
                    מחיקה
                  </button>
                </div>
              ))}
            </div>
            {selectionStatus && <p className="status">{selectionStatus}</p>}
          </div>
        </div>
      </aside>

      <div className="teacher-chat-main">
        <header className="teacher-floating-actions">
          <button type="button" className="btn-secondary" onClick={startNewConversation} disabled={isStreaming}>
            חדש
          </button>
        </header>

        <section className="teacher-chat-canvas" role="log" aria-live="polite">
          {loadingConversation ? <p className="status">טוען שיחה...</p> : null}
          {messages.length === 0 && !loadingConversation ? (
            <div className="teacher-empty-state">
              <p>זה המקום ללמוד</p>
            </div>
          ) : null}
          {messages.map((message) => (
            <article
              key={message.id}
              className={`chat-message ${message.role === "assistant" ? "assistant" : "user"}`}
              data-cursor-element-id={`message-${message.id}`}
            >
              <strong>{message.role === "assistant" ? "מורה" : "את/ה"}</strong>
              <p>{message.content || "המורה מקליד..."}</p>
            </article>
          ))}
          <div ref={streamAnchorRef} />
        </section>

        <footer className="teacher-composer-wrap">
          <form className="teacher-composer" onSubmit={ask}>
            <textarea
              rows={2}
              placeholder="Ask in English or Hebrew..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={isStreaming}
            />
            <button type="submit" disabled={!canAsk}>
              {isStreaming ? "..." : "שלח"}
            </button>
          </form>
          {chatStatus && <p className="status">{chatStatus}</p>}
        </footer>
      </div>

      <aside className="teacher-tools-rail" aria-label="כלים">
        <div className="glass teacher-tools-layout">
          <div className="teacher-tablist" role="tablist" aria-label="כלים ופיצ׳רים">
            {toolTabBtn("podcast", "פודקאסט", "teacher-panel-podcast")}
            {toolTabBtn("quiz", "צור שאלון", "teacher-panel-quiz")}
            {toolTabBtn("chats", "שיחות", "teacher-panel-chats")}
            {toolTabBtn("projects", "הצעות לפרויקטים", "teacher-panel-projects")}
            {toolTabBtn("roadmap", "בפיתוח", "teacher-panel-roadmap")}
          </div>

          <div className="teacher-tool-panels">
            {activeToolTab === "podcast" ? (
              <div
                id="teacher-panel-podcast"
                role="tabpanel"
                aria-labelledby="teacher-tab-podcast"
                className="teacher-tool-panel stack"
              >
                <button
                  type="button"
                  className="btn-podcast-generate"
                  disabled={isGeneratingPodcast || documents.length === 0}
                  onClick={openPodcastModal}
                >
                  {isGeneratingPodcast ? (
                    <span className="btn-loading-content">
                      <span className="spinner-inline" />
                      <span>יוצר פודקאסט...</span>
                    </span>
                  ) : (
                    "צור פודקאסט"
                  )}
                </button>

                {isGeneratingPodcast && podcastProgress && (
                  <div className="podcast-progress">
                    <div className="import-progress-bar">
                      <div className="import-progress-track">
                        <div className="import-progress-fill" />
                      </div>
                      <div className="import-progress-indicator">
                        <span className="spinner-inline" />
                        <span>{podcastProgress}</span>
                      </div>
                    </div>
                  </div>
                )}

                {!isGeneratingPodcast && podcastProgress && podcastProgress.startsWith("שגיאה") && (
                  <p className="status">{podcastProgress}</p>
                )}

                {playingPodcastId && !isGeneratingPodcast && (
                  <div className="podcast-player">
                    <strong>פודקאסט מוכן!</strong>
                    {podcastAudioLoading && (
                      <p className="status">
                        <span className="spinner-inline" /> טוען אודיו...
                      </p>
                    )}
                    {podcastAudioError && <p className="status">{podcastAudioError}</p>}
                    {podcastAudioObjectUrl && !podcastAudioLoading && (
                      <audio key={podcastAudioObjectUrl} controls src={podcastAudioObjectUrl} style={{ width: "100%" }}>
                        הדפדפן אינו תומך בהשמעת אודיו.
                      </audio>
                    )}
                  </div>
                )}

                {podcasts.length > 0 && (
                  <div className="surface stack" style={{ gap: 8 }}>
                    <strong>פודקאסטים קודמים</strong>
                    <div className="item-list">
                      {podcasts.map((p) => (
                        <button
                          type="button"
                          key={p.id}
                          className={`btn-secondary teacher-conversation-btn${playingPodcastId === p.id ? " active" : ""}`}
                          onClick={() => setPlayingPodcastId(p.id)}
                        >
                          {p.title} ({formatDuration(p.duration_seconds)})
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}

            {activeToolTab === "quiz" ? (
              <div
                id="teacher-panel-quiz"
                role="tabpanel"
                aria-labelledby="teacher-tab-quiz"
                className="teacher-tool-panel stack"
              >
                <p className="status">שאלון מותאם אישית מהמסמכים שלכם — בעמוד ייעודי.</p>
                <Link href="/quiz" className="action-link">
                  צור שאלון
                </Link>
              </div>
            ) : null}

            {activeToolTab === "chats" ? (
              <div
                id="teacher-panel-chats"
                role="tabpanel"
                aria-labelledby="teacher-tab-chats"
                className="teacher-tool-panel stack"
              >
                <strong>שיחות קודמות</strong>
                <div className="item-list">
                  {conversations.length === 0 ? <p className="status">אין שיחות עדיין</p> : null}
                  {conversations.map((conversation) => (
                    <button
                      type="button"
                      key={conversation.id}
                      className={`btn-secondary teacher-conversation-btn${
                        currentConversationId === conversation.id ? " active" : ""
                      }`}
                      disabled={isStreaming}
                      onClick={() => {
                        loadConversationMessages(conversation.id);
                      }}
                    >
                      {conversation.title}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {activeToolTab === "projects" ? (
              <div
                id="teacher-panel-projects"
                role="tabpanel"
                aria-labelledby="teacher-tab-projects"
                className="teacher-tool-panel stack teacher-projects-panel"
              >
                <p className="status teacher-projects-hint">
                  ניהול מלא ומעקב — ב
                  <Link href={"/teacher/my-projects" as Route} className="action-link teacher-projects-page-link">
                    עמוד פרויקטים שלי
                  </Link>
                  .
                </p>
                <p className="status teacher-projects-hint">
                  מבוסס על המסמכים המסומנים. בחרו לפחות מסמך אחד כדי לקבל הצעות.
                </p>
                <form className="stack teacher-project-form" onSubmit={submitProjectIdeas}>
                      <label className="stack teacher-form-field">
                        <span className="teacher-form-label">במה תרצה להתמקד?</span>
                        <textarea
                          rows={3}
                          className="surface"
                          placeholder="נושא מהחומר, מיומנות, או סוג פרויקט..."
                          value={projectFocus}
                          onChange={(e) => setProjectFocus(e.target.value)}
                          disabled={projectLoading}
                        />
                      </label>
                      <label className="stack teacher-form-field">
                        <span className="teacher-form-label">רמה ומסגרת זמן</span>
                        <select
                          className="surface"
                          value={projectBand}
                          onChange={(e) => setProjectBand(e.target.value as ExperienceBand)}
                          disabled={projectLoading}
                        >
                          {EXPERIENCE_BAND_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button type="submit" className="btn-secondary" disabled={!canSuggestProjects}>
                        {projectLoading ? (
                          <span className="btn-loading-content">
                            <span className="spinner-inline" />
                            <span>מציע...</span>
                          </span>
                        ) : (
                          "הצע פרויקטים"
                        )}
                      </button>
                </form>
                {projectStatus ? <p className="status">{projectStatus}</p> : null}
                {projectSuggestions && showTransferPrompt ? (
                  <div className="surface teacher-projects-transfer-prompt" role="dialog" aria-label="העברה לפרויקטים שלי">
                    <p className="teacher-projects-transfer-text">
                      לעבור לעמוד &quot;פרויקטים שלי&quot; כדי לשמור את הטיוטה ולעקוב אחרי ההתקדמות?
                    </p>
                    <label className="stack teacher-form-field">
                      <span className="teacher-form-label">כותרת לטיוטה (בעמוד הבא)</span>
                      <input
                        type="text"
                        className="surface"
                        value={saveTitleDraft}
                        onChange={(e) => setSaveTitleDraft(e.target.value)}
                      />
                    </label>
                    <div className="teacher-projects-transfer-actions">
                      <button type="button" onClick={goToMyProjectsWithDraft}>
                        כן, מעבר לעמוד פרויקטים שלי
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => setShowTransferPrompt(false)}
                      >
                        לא, אשאר כאן
                      </button>
                    </div>
                  </div>
                ) : null}
                {projectSuggestions ? (
                  <div className="teacher-suggestions-wrap">
                    <div className="teacher-suggestion-cards" aria-label="הצעות פרויקטים">
                      {splitProjectSuggestions(projectSuggestions).map((block, idx) => (
                        <article key={`${block.title}-${idx}`} className="surface teacher-suggestion-card">
                          <h4 className="teacher-suggestion-card-title">{block.title}</h4>
                          <div className="teacher-suggestion-card-body">{block.body}</div>
                        </article>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}

            {activeToolTab === "roadmap" ? (
              <div
                id="teacher-panel-roadmap"
                role="tabpanel"
                aria-labelledby="teacher-tab-roadmap"
                className="teacher-tool-panel stack"
              >
                <strong>פיצ׳רים בדרך</strong>
                <ul className="teacher-roadmap-list">
                  {TEACHER_ROADMAP_ITEMS.map((item) => (
                    <li key={item.title} className="surface teacher-roadmap-item">
                      <strong className="teacher-roadmap-item-title">{item.title}</strong>
                      <p className="status teacher-roadmap-item-detail">{item.detail}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      </aside>

      {podcastModalOpen && (
        <div className="podcast-modal-overlay" onClick={() => setPodcastModalOpen(false)}>
          <div className="podcast-modal glass stack" onClick={(e) => e.stopPropagation()}>
            <h3>בחר מסמכים לפודקאסט</h3>
            <div className="item-list">
              {documents.map((doc) => (
                <label key={doc.id} className="teacher-doc-checkbox">
                  <input
                    type="checkbox"
                    checked={podcastDocIds.includes(doc.id)}
                    onChange={(e) => {
                      setPodcastDocIds((prev) =>
                        e.target.checked ? [...prev, doc.id] : prev.filter((id) => id !== doc.id)
                      );
                    }}
                  />
                  <span>{doc.name} <small>({getSourceLabel(doc)})</small></span>
                </label>
              ))}
            </div>
            <div className="podcast-modal-actions">
              <button
                type="button"
                disabled={podcastDocIds.length === 0}
                onClick={generatePodcast}
              >
                צור פודקאסט ({podcastDocIds.length} מסמכים)
              </button>
              <button type="button" className="btn-secondary" onClick={() => setPodcastModalOpen(false)}>
                ביטול
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
