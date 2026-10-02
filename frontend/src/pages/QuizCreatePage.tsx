import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentsApi } from '../api/documents';
import { quizzesApi } from '../api/quizzes';
import { AppShell, TopBar } from '../components/layout/Sidebar';
import { Spinner } from '../components/common/Spinner';
import { Alert } from '../components/common/Alert';
import { extractErrorMessage } from '../api/client';
import type { DocumentResponse } from '../types/api';

const DIFFICULTIES = ['easy', 'medium', 'hard', 'mixed'] as const;
type Difficulty = (typeof DIFFICULTIES)[number];

export function QuizCreatePage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [title, setTitle] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [numQuestions, setNumQuestions] = useState(10);
  const [difficulty, setDifficulty] = useState<Difficulty>('mixed');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    documentsApi
      .list()
      .then((docs) => setDocuments(docs.filter((d) => d.is_processed)))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoadingDocs(false));
  }, []);

  function toggleDoc(id: number) {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!title.trim()) { setError('Quiz title is required.'); return; }
    if (selectedDocIds.length === 0) { setError('Select at least one document.'); return; }
    setGenerating(true);
    try {
      const quiz = await quizzesApi.generate({
        title: title.trim(),
        document_ids: selectedDocIds,
        num_questions: numQuestions,
        difficulty,
      });
      navigate(`/quizzes/${quiz.id}/take`);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  }

  return (
    <AppShell>
      <TopBar title="Generate Quiz" onMenuClick={() => {}} />

      <div style={{ padding: '28px 32px', maxWidth: 680, margin: '0 auto' }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Generate a Quiz</h1>
          <p style={{ color: 'var(--color-muted)', marginTop: 4, fontSize: '0.875rem' }}>
            AI will create multiple-choice questions grounded in your study material.
          </p>
        </div>

        {generating ? (
          <div className="card card-pad" style={{ textAlign: 'center', padding: '60px 24px' }}>
            <Spinner />
            <p style={{ marginTop: 18, fontWeight: 600 }}>Creating your quiz from your study material…</p>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-muted)', marginTop: 6 }}>
              This usually takes 20–90 seconds depending on the material.
            </p>
          </div>
        ) : (
          <div className="card card-pad">
            {error && <div style={{ marginBottom: 18 }}><Alert message={error} onDismiss={() => setError('')} /></div>}

            <form onSubmit={handleSubmit}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
                {/* Title */}
                <div className="form-group">
                  <label className="form-label" htmlFor="quiz-title">Quiz title</label>
                  <input
                    id="quiz-title"
                    className="form-input"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Chapter 3 — Sorting Algorithms"
                    required
                    maxLength={200}
                  />
                </div>

                {/* Documents */}
                <div className="form-group">
                  <label className="form-label">
                    Documents ({selectedDocIds.length} selected)
                  </label>
                  {loadingDocs ? (
                    <div className="skeleton" style={{ height: 80 }} />
                  ) : documents.length === 0 ? (
                    <div className="alert alert-info">
                      No processed documents found. Upload study material first.
                    </div>
                  ) : (
                    <div
                      style={{
                        border: '1px solid var(--color-border)',
                        borderRadius: 8,
                        overflow: 'hidden',
                      }}
                    >
                      {documents.map((doc, i) => (
                        <label
                          key={doc.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10,
                            padding: '11px 14px',
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                            borderTop: i === 0 ? 'none' : '1px solid var(--color-border)',
                            background: selectedDocIds.includes(doc.id) ? 'var(--color-primary-light)' : 'transparent',
                            transition: 'background 0.15s ease',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={selectedDocIds.includes(doc.id)}
                            onChange={() => toggleDoc(doc.id)}
                            aria-label={doc.filename}
                            style={{ accentColor: 'var(--color-primary)' }}
                          />
                          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {doc.filename}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)', flexShrink: 0 }}>
                            {doc.file_type.toUpperCase()}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                {/* Number of questions */}
                <div className="form-group">
                  <label className="form-label" htmlFor="num-questions">
                    Number of questions: <strong>{numQuestions}</strong>
                  </label>
                  <input
                    id="num-questions"
                    type="range"
                    min={3}
                    max={20}
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(Number(e.target.value))}
                    style={{ accentColor: 'var(--color-primary)', width: '100%' }}
                    aria-valuemin={3}
                    aria-valuemax={20}
                    aria-valuenow={numQuestions}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--color-muted)' }}>
                    <span>3</span><span>20</span>
                  </div>
                </div>

                {/* Difficulty */}
                <div className="form-group">
                  <label className="form-label">Difficulty</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {DIFFICULTIES.map((d) => (
                      <button
                        key={d}
                        type="button"
                        className={`btn ${difficulty === d ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                        onClick={() => setDifficulty(d)}
                        style={{ flex: 1, textTransform: 'capitalize' }}
                        aria-pressed={difficulty === d}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="submit"
                  className="btn btn-primary btn-lg"
                  disabled={generating || documents.length === 0}
                  style={{ width: '100%' }}
                >
                  Generate Quiz
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </AppShell>
  );
}
