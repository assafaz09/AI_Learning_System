"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  apiFetch,
  deleteDocument,
  getConversationMessages,
  streamTeacherChat,
  TeacherMessage,
  uploadFiles
} from "../../lib/api";

type Doc = { id: number; name: string };
type SelectedDocsResponse = { document_ids: number[] };
type Conversation = { id: number; title: string; created_at: string };
type HistoryResponse = { conversations: Conversation[] };

export default function TeacherPage() {
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<TeacherMessage[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [uploadStatus, setUploadStatus] = useState("");
  const [selectionStatus, setSelectionStatus] = useState("");
  const [chatStatus, setChatStatus] = useState("");
  const [deleteStatus, setDeleteStatus] = useState("");
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const streamAnchorRef = useRef<HTMLDivElement | null>(null);

  const canAsk = useMemo(
    () => question.trim().length > 0 && selected.length > 0 && !isStreaming,
    [question, selected, isStreaming]
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
      setChatStatus(error instanceof Error ? error.message : "טעינת היסטוריית השיחה נכשלה");
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

  useEffect(() => {
    Promise.all([loadDocs(), loadConversations()]).catch((error) => {
      setUploadStatus(error instanceof Error ? error.message : "שגיאה בטעינת נתונים");
    });
  }, []);

  useEffect(() => {
    if (!streamAnchorRef.current) {
      return;
    }
    streamAnchorRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isStreaming]);

  const onFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const files: File[] = e.target.files ? Array.from(e.target.files as FileList) : [];
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
      const detail = error instanceof Error ? error.message : "שליחת השאלה נכשלה";
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
      setDeleteStatus(error instanceof Error ? error.message : "מחיקת המסמך נכשלה");
    }
  };

  const startNewConversation = () => {
    setCurrentConversationId(null);
    setMessages([]);
    setChatStatus("");
  };

  return (
    <main className="teacher-chat-screen">
      <header className="teacher-floating-actions">
        <button type="button" className="btn-secondary" onClick={startNewConversation} disabled={isStreaming}>
          חדש
        </button>
        <button type="button" className="btn-secondary" onClick={() => setIsDrawerOpen((prev) => !prev)}>
          ניהול מסמכים
        </button>
      </header>

      <section className="teacher-chat-canvas" role="log" aria-live="polite">
        {loadingConversation ? <p className="status">טוען שיחה...</p> : null}
        {messages.length === 0 && !loadingConversation ? (
          <div className="teacher-empty-state">
            <h2>סוכן מורה</h2>
            <p>שאלו שאלה כדי להתחיל שיחה חיה על בסיס המסמכים שבחרתם.</p>
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

      <section className={`teacher-drawer ${isDrawerOpen ? "open" : ""}`}>
        <div className="glass stack">
          <h3>מסמכים ושיחות</h3>
          <input type="file" multiple accept=".pdf,.txt,.md,.csv,.json" onChange={onFileChange} />
          {uploadStatus && <p className="status">{uploadStatus}</p>}
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
                        setSelectionStatus(error instanceof Error ? error.message : "שמירת הבחירה נכשלה");
                      }
                    }}
                  />
                  <span>{doc.name}</span>
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

          <div className="surface stack" style={{ gap: 8 }}>
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
                    setIsDrawerOpen(false);
                    loadConversationMessages(conversation.id);
                  }}
                >
                  {conversation.title}
                </button>
              ))}
            </div>
          </div>
        </div>
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
    </main>
  );
}
