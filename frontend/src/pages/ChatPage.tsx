import { useEffect, useRef, useState, type FormEvent } from 'react';
import { chatApi } from '../api/chat';
import { documentsApi } from '../api/documents';
import { AppShell, TopBar } from '../components/layout/Sidebar';
import { Spinner } from '../components/common/Spinner';
import { Alert, EmptyState } from '../components/common/Alert';
import { extractErrorMessage } from '../api/client';
import type { ChatMessagePublic, ChatSessionDetail, ChatSessionSummary, DocumentResponse } from '../types/api';

const SUGGESTIONS = [
  'Summarize this chapter',
  'Explain this concept simply',
  'Give me exam-important points',
  'Compare these concepts',
];

function SourcesList({ sources }: { sources: NonNullable<ChatMessagePublic['sources']> }) {
  const [open, setOpen] = useState(false);
  if (sources.length === 0) return null;
  return (
    <div style={{ marginTop: 10 }}>
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => setOpen(!open)}
        style={{ fontSize: '0.75rem', padding: '4px 8px' }}
        aria-expanded={open}
      >
        {open ? '▲' : '▼'} {sources.length} source{sources.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {sources.map((s, i) => (
            <div key={i} className="source-card">
              <div style={{ fontWeight: 500, fontSize: '0.8rem' }}>
                {s.filename}{s.page != null ? ` — Page ${s.page}` : ''}
              </div>
              {s.content_preview && (
                <div style={{ marginTop: 4, color: 'var(--color-muted)', fontStyle: 'italic', fontSize: '0.775rem', lineHeight: 1.5 }}>
                  "{s.content_preview}"
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChatPage() {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSessionDetail | null>(null);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [sessionTitle, setSessionTitle] = useState('');
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessagePublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [showNew, setShowNew] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([chatApi.listSessions(), documentsApi.list()])
      .then(([s, d]) => {
        setSessions(s);
        setDocuments(d.filter((doc) => doc.is_processed));
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function loadSession(id: number) {
    setError('');
    try {
      const detail = await chatApi.getSession(id);
      setActiveSession(detail);
      setMessages(detail.messages);
      setShowNew(false);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function createSession(e: FormEvent) {
    e.preventDefault();
    if (!sessionTitle.trim()) { setError('Session title is required.'); return; }
    if (selectedDocIds.length === 0) { setError('Select at least one document.'); return; }
    setCreating(true);
    setError('');
    try {
      const session = await chatApi.createSession({ title: sessionTitle.trim(), document_ids: selectedDocIds });
      setSessions((prev) => [session, ...prev]);
      await loadSession(session.id);
      setSessionTitle('');
      setSelectedDocIds([]);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  async function sendMessage(text: string) {
    if (!activeSession || !text.trim() || sending) return;
    setError('');
    setSending(true);

    const userMsg: ChatMessagePublic = {
      id: Date.now(),
      role: 'user',
      content: text.trim(),
      sources: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion('');

    try {
      const response = await chatApi.sendMessage(activeSession.id, { question: text.trim() });
      const assistantMsg: ChatMessagePublic = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSending(false);
    }
  }

  function toggleDocId(id: number) {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  return (
    <AppShell>
      <div style={{ display: 'flex', height: 'calc(100vh - 0px)', overflow: 'hidden' }}>
        {/* Session list sidebar */}
        <div
          style={{
            width: 260,
            minWidth: 260,
            background: 'var(--color-surface)',
            borderRight: '1px solid var(--color-border)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div style={{ padding: '16px 14px 12px', borderBottom: '1px solid var(--color-border)' }}>
            <div style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: 10 }}>Ask StudySense</div>
            <button
              className="btn btn-primary btn-sm"
              style={{ width: '100%' }}
              onClick={() => { setShowNew(true); setActiveSession(null); setMessages([]); }}
            >
              + New Chat
            </button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '10px 8px' }}>
            {loading ? (
              <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="skeleton" style={{ height: 44, borderRadius: 8 }} />
                ))}
              </div>
            ) : sessions.length === 0 && !showNew ? (
              <div style={{ padding: 16, textAlign: 'center', color: 'var(--color-muted)', fontSize: '0.8rem' }}>
                No sessions yet. Start a new chat.
              </div>
            ) : (
              sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => loadSession(s.id)}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    padding: '9px 10px',
                    borderRadius: 8,
                    border: 'none',
                    cursor: 'pointer',
                    background: activeSession?.id === s.id ? 'var(--color-primary-light)' : 'transparent',
                    color: activeSession?.id === s.id ? 'var(--color-primary)' : 'var(--color-text)',
                    fontWeight: activeSession?.id === s.id ? 600 : 400,
                    fontSize: '0.8375rem',
                    transition: 'all 0.15s ease',
                    fontFamily: 'inherit',
                  }}
                >
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Main chat area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Header */}
          <div className="top-bar" style={{ position: 'static', borderBottom: '1px solid var(--color-border)' }}>
            <span className="top-bar-title">
              {activeSession ? activeSession.title : 'New Chat'}
            </span>
            {activeSession && (
              <div style={{ fontSize: '0.775rem', color: 'var(--color-muted)' }}>
                {activeSession.documents.map((d) => d.filename).join(', ')}
              </div>
            )}
          </div>

          {/* New session form */}
          {showNew && !activeSession && (
            <div style={{ padding: 24, borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg)' }}>
              <h3 style={{ marginBottom: 16, fontSize: '1rem' }}>Start a New Chat</h3>
              {error && <div style={{ marginBottom: 12 }}><Alert message={error} onDismiss={() => setError('')} /></div>}
              <form onSubmit={createSession}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div className="form-group">
                    <label className="form-label">Session title</label>
                    <input
                      className="form-input"
                      value={sessionTitle}
                      onChange={(e) => setSessionTitle(e.target.value)}
                      placeholder="e.g. Chapter 5 review"
                      required
                      disabled={creating}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Select documents ({selectedDocIds.length} selected)</label>
                    {documents.length === 0 ? (
                      <div className="alert alert-info">No processed documents. Upload study material first.</div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 180, overflowY: 'auto' }}>
                        {documents.map((doc) => (
                          <label key={doc.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: '0.875rem' }}>
                            <input
                              type="checkbox"
                              checked={selectedDocIds.includes(doc.id)}
                              onChange={() => toggleDocId(doc.id)}
                              disabled={creating}
                            />
                            {doc.filename}
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                  <button type="submit" className="btn btn-primary" disabled={creating || documents.length === 0}>
                    {creating ? <><Spinner size="sm" /> Creating…</> : 'Start Chat'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Messages */}
          {!showNew && !activeSession && (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <EmptyState
                icon="💬"
                title="No chat selected"
                description="Create a new chat or select an existing session."
                action={
                  <button className="btn btn-primary" onClick={() => setShowNew(true)}>
                    + New Chat
                  </button>
                }
              />
            </div>
          )}

          {activeSession && (
            <>
              <div
                style={{
                  flex: 1,
                  overflowY: 'auto',
                  padding: '20px 24px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 20,
                }}
              >
                {messages.length === 0 && (
                  <div style={{ padding: '40px 0' }}>
                    <p style={{ color: 'var(--color-muted)', marginBottom: 16, fontSize: '0.875rem', fontWeight: 500 }}>
                      Try asking:
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {SUGGESTIONS.map((s) => (
                        <button
                          key={s}
                          className="btn btn-secondary btn-sm"
                          onClick={() => sendMessage(s)}
                          disabled={sending}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}
                    className="fade-in"
                  >
                    {msg.role === 'user' ? (
                      <div className="chat-bubble-user">{msg.content}</div>
                    ) : (
                      <div className="chat-bubble-assistant" style={{ maxWidth: '85%' }}>
                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>{msg.content}</div>
                        {msg.sources && msg.sources.length > 0 && (
                          <SourcesList sources={msg.sources} />
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {sending && (
                  <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                    <div className="chat-bubble-assistant" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Spinner size="sm" /> Thinking…
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div style={{ padding: '14px 20px', borderTop: '1px solid var(--color-border)', background: 'var(--color-surface)' }}>
                {error && <div style={{ marginBottom: 10 }}><Alert message={error} onDismiss={() => setError('')} /></div>}
                <form
                  onSubmit={(e) => { e.preventDefault(); sendMessage(question); }}
                  style={{ display: 'flex', gap: 10 }}
                >
                  <textarea
                    className="form-textarea"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask a question about your study material…"
                    rows={2}
                    style={{ flex: 1, resize: 'none' }}
                    disabled={sending}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage(question);
                      }
                    }}
                  />
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={sending || !question.trim()}
                    style={{ alignSelf: 'flex-end' }}
                    aria-label="Send message"
                  >
                    {sending ? <Spinner size="sm" /> : '↑'}
                  </button>
                </form>
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
