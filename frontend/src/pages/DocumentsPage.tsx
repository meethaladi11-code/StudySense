import { useEffect, useRef, useState, type DragEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentsApi } from '../api/documents';
import { AppShell, TopBar } from '../components/layout/Sidebar';
import { Spinner } from '../components/common/Spinner';
import { Alert, EmptyState } from '../components/common/Alert';
import { extractErrorMessage } from '../api/client';
import type { DocumentResponse } from '../types/api';

const ACCEPTED_TYPES = '.pdf,.txt,.docx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document';

function fileTypeIcon(type: string) {
  if (type === 'pdf') return '📕';
  if (type === 'docx') return '📘';
  return '📄';
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export function DocumentsPage() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => { loadDocs(); }, []);

  async function loadDocs() {
    setLoading(true);
    try {
      setDocs(await documentsApi.list());
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(file: File) {
    setError('');
    setSuccess('');
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!['pdf', 'txt', 'docx'].includes(ext)) {
      setError('Only PDF, TXT, and DOCX files are supported.');
      return;
    }
    setUploading(true);
    setUploadProgress(0);
    try {
      const doc = await documentsApi.upload(file, setUploadProgress);
      setDocs((prev) => [doc, ...prev]);
      setSuccess(`"${doc.filename}" uploaded and processed successfully.`);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }

  return (
    <AppShell>
      <TopBar title="Study Material" onMenuClick={() => {}} />

      <div style={{ padding: '28px 32px', maxWidth: 900, margin: '0 auto' }}>
        {/* Upload zone */}
        <section style={{ marginBottom: 28 }}>
          {error && <Alert message={error} onDismiss={() => setError('')} />}
          {success && <Alert type="success" message={success} onDismiss={() => setSuccess('')} />}
          <div style={{ marginTop: error || success ? 16 : 0 }}>
            <div
              className={`drop-zone ${isDragging ? 'drag-over' : ''}`}
              onClick={() => !uploading && fileRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              role="button"
              tabIndex={0}
              aria-label="Upload study material — click or drag a file"
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click(); }}
              style={{ opacity: uploading ? 0.7 : 1 }}
            >
              {uploading ? (
                <div>
                  <Spinner />
                  <p style={{ marginTop: 14, fontWeight: 500 }}>Uploading and processing…</p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--color-muted)', marginTop: 4 }}>
                    This may take up to 60 seconds for large files.
                  </p>
                  {uploadProgress > 0 && uploadProgress < 100 && (
                    <div style={{ marginTop: 14, width: 200, margin: '14px auto 0' }}>
                      <div className="progress-bar-track">
                        <div className="progress-bar-fill" style={{ width: `${uploadProgress}%` }} />
                      </div>
                      <p style={{ fontSize: '0.75rem', color: 'var(--color-muted)', marginTop: 4 }}>{uploadProgress}% uploaded</p>
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: '2.5rem', marginBottom: 10 }}>⬆</div>
                  <p style={{ fontWeight: 600, marginBottom: 4 }}>
                    Drag & drop or <span style={{ color: 'var(--color-primary)' }}>click to upload</span>
                  </p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--color-muted)' }}>
                    PDF, DOCX, TXT — up to large file sizes
                  </p>
                </div>
              )}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPTED_TYPES}
              onChange={onFileChange}
              style={{ display: 'none' }}
              aria-label="File picker"
            />
          </div>
        </section>

        {/* Document list */}
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>Your Documents</h2>
            <span style={{ fontSize: '0.8125rem', color: 'var(--color-muted)' }}>
              {docs.length} document{docs.length !== 1 ? 's' : ''}
            </span>
          </div>

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[...Array(3)].map((_, i) => (
                <div key={i} className="card card-pad" style={{ height: 68 }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <div className="skeleton" style={{ width: 36, height: 36, borderRadius: 8 }} />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div className="skeleton" style={{ height: 14, width: '50%' }} />
                      <div className="skeleton" style={{ height: 12, width: '30%' }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : docs.length === 0 ? (
            <div className="card">
              <EmptyState
                icon="📄"
                title="No study material yet"
                description="Upload your first PDF, DOCX, or TXT file to get started."
              />
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {docs.map((doc) => (
                <div key={doc.id} className="card card-pad fade-in">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div
                      style={{
                        width: 40,
                        height: 40,
                        background: 'var(--color-bg)',
                        border: '1px solid var(--color-border)',
                        borderRadius: 10,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 20,
                        flexShrink: 0,
                      }}
                    >
                      {fileTypeIcon(doc.file_type)}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: '0.9rem',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {doc.filename}
                      </div>
                      <div style={{ fontSize: '0.775rem', color: 'var(--color-muted)', marginTop: 2 }}>
                        {doc.file_type.toUpperCase()} · {doc.chunk_count} chunks · {formatDate(doc.created_at)}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                      <span
                        className={`badge ${doc.is_processed ? 'badge-strong' : 'badge-insufficient'}`}
                      >
                        {doc.is_processed ? 'Ready' : 'Processing'}
                      </span>
                      {doc.is_processed && (
                        <>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => navigate('/chat')}
                            title="Ask about this document"
                          >
                            Ask
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => navigate('/quizzes/new')}
                            title="Generate a quiz from this document"
                          >
                            Quiz
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
