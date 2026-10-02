import { useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { AppShell, TopBar } from '../components/layout/Sidebar';
import type { QuizSubmitResponse, ReviewItem } from '../types/api';

function ResultIcon({ isCorrect }: { isCorrect: boolean }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 22,
        height: 22,
        borderRadius: '50%',
        background: isCorrect ? 'var(--color-success)' : 'var(--color-danger)',
        color: '#fff',
        fontSize: 12,
        fontWeight: 700,
        flexShrink: 0,
      }}
      aria-label={isCorrect ? 'Correct' : 'Incorrect'}
    >
      {isCorrect ? '✓' : '✕'}
    </span>
  );
}

function ReviewCard({ item, index }: { item: ReviewItem; index: number }) {
  const [showSources, setShowSources] = useState(false);

  return (
    <div
      className="card card-pad fade-in"
      style={{
        borderLeft: `3px solid ${item.is_correct ? 'var(--color-success)' : 'var(--color-danger)'}`,
      }}
    >
      {/* Question */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 14 }}>
        <ResultIcon isCorrect={item.is_correct} />
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-muted)', marginBottom: 4 }}>
            Q{index + 1} · {item.topic}
          </div>
          <p style={{ fontWeight: 600, lineHeight: 1.55 }}>{item.question_text}</p>
        </div>
      </div>

      {/* Answers */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
        <div
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: 8,
            background: item.is_correct ? 'var(--color-success-bg)' : 'var(--color-danger-bg)',
            fontSize: '0.8375rem',
          }}
        >
          <div
            style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-muted)', marginBottom: 3 }}
          >
            YOUR ANSWER
          </div>
          <div
            style={{
              fontWeight: 600,
              color: item.is_correct ? 'var(--color-success)' : 'var(--color-danger)',
            }}
          >
            {item.selected_answer}
          </div>
        </div>
        {!item.is_correct && (
          <div
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 8,
              background: 'var(--color-success-bg)',
              fontSize: '0.8375rem',
            }}
          >
            <div
              style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-muted)', marginBottom: 3 }}
            >
              CORRECT ANSWER
            </div>
            <div style={{ fontWeight: 600, color: 'var(--color-success)' }}>
              {item.correct_answer}
            </div>
          </div>
        )}
      </div>

      {/* Explanation */}
      {item.explanation && (
        <div
          style={{
            background: 'var(--color-bg)',
            borderRadius: 8,
            padding: '10px 14px',
            fontSize: '0.875rem',
            lineHeight: 1.65,
            color: 'var(--color-text)',
            marginBottom: item.sources && item.sources.length > 0 ? 10 : 0,
          }}
        >
          <div
            style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-muted)', marginBottom: 4 }}
          >
            EXPLANATION
          </div>
          {item.explanation}
        </div>
      )}

      {/* Sources */}
      {item.sources && item.sources.length > 0 && (
        <div>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setShowSources(!showSources)}
            style={{ fontSize: '0.75rem' }}
            aria-expanded={showSources}
          >
            {showSources ? '▲' : '▼'} {item.sources.length} source
            {item.sources.length !== 1 ? 's' : ''}
          </button>
          {showSources && (
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {item.sources.map((s, i) => (
                <div key={i} className="source-card">
                  <div style={{ fontWeight: 500, fontSize: '0.8rem' }}>
                    {s.filename}
                    {s.page != null ? ` — Page ${s.page}` : ''}
                  </div>
                  {s.content_preview && (
                    <div
                      style={{
                        marginTop: 3,
                        color: 'var(--color-muted)',
                        fontStyle: 'italic',
                        fontSize: '0.775rem',
                      }}
                    >
                      "{s.content_preview}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatPill({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div
      style={{
        padding: '8px 20px',
        background: 'var(--color-bg)',
        borderRadius: 8,
        border: '1px solid var(--color-border)',
        textAlign: 'center',
      }}
    >
      <div style={{ fontWeight: 700, fontSize: '1.25rem', color }}>{value}</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--color-muted)', marginTop: 2 }}>{label}</div>
    </div>
  );
}

export function QuizResultPage() {
  const { quizId } = useParams<{ quizId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as {
    result: QuizSubmitResponse;
    quizTitle?: string;
    fromPlan?: string;
  } | null;

  if (!state?.result) {
    return (
      <AppShell>
        <TopBar title="Quiz Result" onMenuClick={() => {}} />
        <div style={{ padding: 32 }}>
          <p style={{ color: 'var(--color-muted)' }}>
            No result data. Please take a quiz first.
          </p>
          <button
            className="btn btn-primary"
            style={{ marginTop: 12 }}
            onClick={() => navigate('/quizzes')}
          >
            Go to Quizzes
          </button>
        </div>
      </AppShell>
    );
  }

  const { result, quizTitle, fromPlan } = state;
  const pct = result.score_percentage;
  const color =
    pct >= 80
      ? 'var(--color-success)'
      : pct >= 60
      ? 'var(--color-warning)'
      : 'var(--color-danger)';

  return (
    <AppShell>
      <TopBar title="Quiz Result" onMenuClick={() => {}} />

      <div style={{ padding: '28px 32px', maxWidth: 780, margin: '0 auto' }}>
        {/* Score card */}
        <div
          className="card card-pad fade-in"
          style={{ textAlign: 'center', marginBottom: 28, padding: '36px 24px' }}
        >
          {quizTitle && (
            <div
              style={{
                fontSize: '0.8rem',
                color: 'var(--color-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: 8,
              }}
            >
              {quizTitle}
            </div>
          )}
          <div
            style={{
              fontSize: '4rem',
              fontWeight: 800,
              color,
              letterSpacing: '-0.04em',
              lineHeight: 1,
              marginBottom: 6,
            }}
          >
            {pct.toFixed(1)}%
          </div>
          <div style={{ color: 'var(--color-muted)', fontSize: '0.9rem', marginBottom: 20 }}>
            {result.correct_count} correct / {result.total_questions} total
          </div>
          <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
            <StatPill label="Correct" value={result.correct_count} color="var(--color-success)" />
            <StatPill
              label="Incorrect"
              value={result.total_questions - result.correct_count}
              color="var(--color-danger)"
            />
            <StatPill label="Total" value={result.total_questions} color="var(--color-text)" />
          </div>

          <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn btn-secondary" onClick={() => navigate('/quizzes')}>
              All Quizzes
            </button>
            {fromPlan && (
              <button
                className="btn btn-secondary"
                onClick={() => navigate(`/improvement/${fromPlan}`)}
              >
                Back to Plan
              </button>
            )}
            <button
              className="btn btn-primary"
              onClick={() => navigate(`/quizzes/${quizId}/take`)}
            >
              Retake Quiz
            </button>
          </div>
        </div>

        {/* Review */}
        <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 16 }}>Review</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {result.review.map((item, i) => (
            <ReviewCard key={item.question_id} item={item} index={i} />
          ))}
        </div>
      </div>
    </AppShell>
  );
}
