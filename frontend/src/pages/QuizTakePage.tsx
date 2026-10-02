import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { quizzesApi } from '../api/quizzes';
import { AppShell, TopBar } from '../components/layout/Sidebar';
import { Spinner } from '../components/common/Spinner';
import { Alert } from '../components/common/Alert';
import { extractErrorMessage } from '../api/client';
import type { QuizTakeResponse } from '../types/api';

const LETTERS = ['A', 'B', 'C', 'D'] as const;

export function QuizTakePage() {
  const { quizId } = useParams<{ quizId: string }>();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState<QuizTakeResponse | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    if (!quizId) return;
    quizzesApi
      .take(Number(quizId))
      .then((q) => setQuiz(q))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [quizId]);

  function selectAnswer(questionId: number, letter: string) {
    setAnswers((prev) => ({ ...prev, [questionId]: letter }));
  }

  async function submitQuiz() {
    if (!quiz || !quizId) return;
    setSubmitting(true);
    setError('');
    try {
      const result = await quizzesApi.submit(Number(quizId), {
        answers: Object.entries(answers).map(([qId, selected]) => ({
          question_id: Number(qId),
          selected_answer: selected as 'A' | 'B' | 'C' | 'D',
        })),
      });
      navigate(`/quizzes/${quizId}/result`, { state: { result, quizTitle: quiz.title } });
    } catch (err) {
      setError(extractErrorMessage(err));
      setShowConfirm(false);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <AppShell>
        <TopBar title="Quiz" onMenuClick={() => {}} />
        <div style={{ padding: 40, display: 'flex', justifyContent: 'center' }}>
          <Spinner />
        </div>
      </AppShell>
    );
  }

  if (error && !quiz) {
    return (
      <AppShell>
        <TopBar title="Quiz" onMenuClick={() => {}} />
        <div style={{ padding: 32 }}>
          <Alert message={error} />
        </div>
      </AppShell>
    );
  }

  if (!quiz) return null;

  const question = quiz.questions[currentIndex];
  const answeredCount = Object.keys(answers).length;
  const total = quiz.questions.length;
  const progress = Math.round(((currentIndex + 1) / total) * 100);

  return (
    <AppShell>
      <TopBar title={quiz.title} onMenuClick={() => {}} />

      <div style={{ padding: '28px 32px', maxWidth: 740, margin: '0 auto' }}>
        {/* Progress */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', color: 'var(--color-muted)', marginBottom: 8 }}>
            <span>Question {currentIndex + 1} of {total}</span>
            <span>{answeredCount} of {total} answered</span>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>

        {/* Question card */}
        <div className="card card-pad" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 10, marginBottom: 18, alignItems: 'flex-start' }}>
            <span
              style={{
                flexShrink: 0,
                background: 'var(--color-primary-light)',
                color: 'var(--color-primary)',
                fontWeight: 700,
                fontSize: '0.75rem',
                padding: '3px 9px',
                borderRadius: 100,
              }}
            >
              Q{currentIndex + 1}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)', padding: '3px 0', textTransform: 'capitalize' }}>
              {question.difficulty} · {question.topic}
            </span>
          </div>

          <p style={{ fontSize: '1rem', fontWeight: 600, lineHeight: 1.6, marginBottom: 22 }}>
            {question.question_text}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {LETTERS.map((letter) => {
              const isSelected = answers[question.question_id] === letter;
              return (
                <div
                  key={letter}
                  className={`choice-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => selectAnswer(question.question_id, letter)}
                  role="radio"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') selectAnswer(question.question_id, letter);
                  }}
                >
                  <div className="choice-letter">{letter}</div>
                  <div style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
                    {question.options[letter]}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Navigation */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <button
            className="btn btn-secondary"
            onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
            disabled={currentIndex === 0}
          >
            ← Previous
          </button>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
            {quiz.questions.map((q, i) => (
              <button
                key={q.question_id}
                onClick={() => setCurrentIndex(i)}
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 6,
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  background: i === currentIndex
                    ? 'var(--color-primary)'
                    : answers[q.question_id]
                    ? 'var(--color-primary-light)'
                    : 'var(--color-border)',
                  color: i === currentIndex
                    ? '#fff'
                    : answers[q.question_id]
                    ? 'var(--color-primary)'
                    : 'var(--color-muted)',
                  transition: 'all 0.15s ease',
                  fontFamily: 'inherit',
                }}
                aria-label={`Go to question ${i + 1}`}
                aria-current={i === currentIndex ? 'true' : undefined}
              >
                {i + 1}
              </button>
            ))}
          </div>

          {currentIndex < total - 1 ? (
            <button
              className="btn btn-secondary"
              onClick={() => setCurrentIndex((i) => Math.min(total - 1, i + 1))}
            >
              Next →
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={() => setShowConfirm(true)}
              disabled={submitting}
            >
              Submit Quiz
            </button>
          )}
        </div>

        {error && <div style={{ marginTop: 16 }}><Alert message={error} onDismiss={() => setError('')} /></div>}
      </div>

      {/* Confirmation modal */}
      {showConfirm && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgb(0 0 0 / 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: 16,
          }}
          onClick={() => !submitting && setShowConfirm(false)}
        >
          <div
            className="card card-pad"
            style={{ maxWidth: 420, width: '100%', borderRadius: 'var(--radius-lg)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 12 }}>Submit Quiz?</h3>
            <p style={{ color: 'var(--color-muted)', fontSize: '0.9rem', marginBottom: 8 }}>
              Answered: <strong style={{ color: 'var(--color-text)' }}>{answeredCount} / {total}</strong>
            </p>
            {answeredCount < total && (
              <div className="alert alert-warning" style={{ marginBottom: 16 }}>
                You have {total - answeredCount} unanswered question{total - answeredCount !== 1 ? 's' : ''}. They will be counted as incorrect.
              </div>
            )}
            <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1 }}
                onClick={() => setShowConfirm(false)}
                disabled={submitting}
              >
                Keep reviewing
              </button>
              <button
                className="btn btn-primary"
                style={{ flex: 1 }}
                onClick={submitQuiz}
                disabled={submitting}
              >
                {submitting ? <><Spinner size="sm" /> Submitting…</> : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
