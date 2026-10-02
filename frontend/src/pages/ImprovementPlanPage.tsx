import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { improvementApi } from '../api/improvement';
import { AppShell, TopBar } from '../components/layout/Sidebar';
import { Spinner } from '../components/common/Spinner';
import { Alert } from '../components/common/Alert';
import { extractErrorMessage } from '../api/client';
import type { ImprovementPlanResponse } from '../types/api';

function AccuracyDelta({ change }: { change: number | null }) {
  if (change === null) return null;
  const isPositive = change >= 0;
  return (
    <span
      style={{
        fontWeight: 700,
        color: isPositive ? 'var(--color-success)' : 'var(--color-danger)',
      }}
    >
      {isPositive ? '+' : ''}
      {change.toFixed(1)}%
    </span>
  );
}

function statusBadge(status: string) {
  const map: Record<string, { label: string; cls: string }> = {
    active: { label: 'Active', cls: 'badge-primary' },
    improved: { label: 'Improved', cls: 'badge-strong' },
    needs_work: { label: 'Needs Work', cls: 'badge-weak' },
    completed: { label: 'Completed', cls: 'badge-strong' },
  };
  const entry = map[status] ?? { label: status, cls: 'badge-gray' };
  return <span className={`badge ${entry.cls}`}>{entry.label}</span>;
}

export function ImprovementPlanPage() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<ImprovementPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [generatingPractice, setGeneratingPractice] = useState(false);
  const [generatingRetest, setGeneratingRetest] = useState(false);

  useEffect(() => {
    if (!planId) return;
    improvementApi
      .getPlan(Number(planId))
      .then(setPlan)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [planId]);

  async function handlePractice() {
    if (!planId) return;
    setGeneratingPractice(true);
    setError('');
    try {
      const quiz = await improvementApi.practice(Number(planId));
      navigate(`/quizzes/${quiz.quiz_id}/take`, {
        state: { quizTitle: quiz.title, fromPlan: planId },
      });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setGeneratingPractice(false);
    }
  }

  async function handleRetest() {
    if (!planId) return;
    setGeneratingRetest(true);
    setError('');
    try {
      const quiz = await improvementApi.retest(Number(planId));
      navigate(`/quizzes/${quiz.quiz_id}/take`, {
        state: { quizTitle: quiz.title, fromPlan: planId, isRetest: true },
      });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setGeneratingRetest(false);
    }
  }

  if (loading) {
    return (
      <AppShell>
        <TopBar title="Improvement Plan" onMenuClick={() => {}} />
        <div style={{ padding: 40, display: 'flex', justifyContent: 'center' }}>
          <Spinner />
        </div>
      </AppShell>
    );
  }

  if (error && !plan) {
    return (
      <AppShell>
        <TopBar title="Improvement Plan" onMenuClick={() => {}} />
        <div style={{ padding: 32 }}>
          <Alert message={error} />
          <button
            className="btn btn-secondary"
            style={{ marginTop: 12 }}
            onClick={() => navigate('/analytics')}
          >
            Back to Analytics
          </button>
        </div>
      </AppShell>
    );
  }

  if (!plan) return null;

  const hasRetestData = plan.latest_accuracy !== null;

  return (
    <AppShell>
      <TopBar title="Improvement Plan" onMenuClick={() => {}} />

      <div style={{ padding: '28px 32px', maxWidth: 860, margin: '0 auto' }}>
        {/* Header */}
        <div className="fade-in" style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              {plan.topic}
            </h1>
            {statusBadge(plan.status)}
          </div>
          <p style={{ color: 'var(--color-muted)', fontSize: '0.875rem' }}>
            Personalised improvement plan based on your quiz performance and study material.
          </p>
        </div>

        {error && (
          <div style={{ marginBottom: 20 }}>
            <Alert message={error} onDismiss={() => setError('')} />
          </div>
        )}

        {/* Before / After */}
        <section style={{ marginBottom: 24 }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: hasRetestData ? 'repeat(3, 1fr)' : 'repeat(2, 1fr)',
              gap: 14,
            }}
          >
            <div className="stat-card">
              <div
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  color: 'var(--color-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  marginBottom: 8,
                }}
              >
                BEFORE (Baseline)
              </div>
              <div
                className="stat-value"
                style={{ color: 'var(--color-danger)', fontSize: '2.25rem' }}
              >
                {plan.baseline_accuracy.toFixed(0)}%
              </div>
              <div className="stat-label">Accuracy when plan was created</div>
            </div>

            {hasRetestData && (
              <div className="stat-card">
                <div
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    color: 'var(--color-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    marginBottom: 8,
                  }}
                >
                  AFTER (Latest)
                </div>
                <div
                  className="stat-value"
                  style={{
                    color:
                      (plan.latest_accuracy ?? 0) >= (plan.baseline_accuracy ?? 0)
                        ? 'var(--color-success)'
                        : 'var(--color-danger)',
                    fontSize: '2.25rem',
                  }}
                >
                  {plan.latest_accuracy!.toFixed(0)}%
                </div>
                <div className="stat-label">After retest</div>
              </div>
            )}

            <div className="stat-card">
              <div
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  color: 'var(--color-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  marginBottom: 8,
                }}
              >
                {hasRetestData ? 'CHANGE' : 'TARGET'}
              </div>
              {hasRetestData ? (
                <>
                  <div style={{ fontSize: '2.25rem', fontWeight: 700, lineHeight: 1 }}>
                    <AccuracyDelta change={plan.accuracy_change} />
                  </div>
                  <div className="stat-label">Improvement since baseline</div>
                </>
              ) : (
                <>
                  <div className="stat-value" style={{ color: 'var(--color-primary)', fontSize: '2.25rem' }}>
                    80%
                  </div>
                  <div className="stat-label">Accuracy goal</div>
                </>
              )}
            </div>
          </div>
        </section>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
          {/* Focus Areas */}
          <div className="card card-pad">
            <h2 style={{ fontSize: '0.875rem', fontWeight: 700, marginBottom: 14 }}>Focus Areas</h2>
            {plan.focus_areas.length === 0 ? (
              <p style={{ color: 'var(--color-muted)', fontSize: '0.875rem' }}>No focus areas specified.</p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {plan.focus_areas.map((area) => (
                  <span key={area} className="focus-chip">
                    {area}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Time Recommendation */}
          <div className="card card-pad">
            <h2 style={{ fontSize: '0.875rem', fontWeight: 700, marginBottom: 14 }}>
              Recommended Study Time
            </h2>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--color-primary)', lineHeight: 1 }}>
                {plan.recommended_minutes}
              </div>
              <div style={{ color: 'var(--color-muted)', fontWeight: 500 }}>minutes</div>
            </div>
            <p style={{ color: 'var(--color-muted)', fontSize: '0.8125rem', marginTop: 8 }}>
              Estimated time to close the gap on this topic.
            </p>
          </div>
        </div>

        {/* Study Plan */}
        <div className="card card-pad" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: '0.875rem', fontWeight: 700, marginBottom: 14 }}>Study Plan</h2>
          <div
            style={{
              fontSize: '0.9rem',
              lineHeight: 1.8,
              color: 'var(--color-text)',
              whiteSpace: 'pre-wrap',
              fontFamily: 'inherit',
            }}
          >
            {plan.study_plan}
          </div>
        </div>

        {/* Source References */}
        {plan.source_refs && plan.source_refs.length > 0 && (
          <div className="card card-pad" style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: '0.875rem', fontWeight: 700, marginBottom: 14 }}>Source References</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {plan.source_refs.map((ref, i) => (
                <div key={i} className="source-card">
                  <div style={{ fontWeight: 600, fontSize: '0.8375rem' }}>
                    {ref.filename}
                    {ref.page != null && (
                      <span style={{ fontWeight: 400, color: 'var(--color-muted)' }}>
                        {' '}— Page {ref.page}
                      </span>
                    )}
                  </div>
                  {ref.content_preview && (
                    <div
                      style={{
                        marginTop: 5,
                        fontSize: '0.8rem',
                        color: 'var(--color-muted)',
                        fontStyle: 'italic',
                        lineHeight: 1.6,
                      }}
                    >
                      "{ref.content_preview}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="card card-pad">
          <h2 style={{ fontSize: '0.875rem', fontWeight: 700, marginBottom: 6 }}>Practice</h2>
          <p style={{ color: 'var(--color-muted)', fontSize: '0.875rem', marginBottom: 16 }}>
            Reinforce your understanding with targeted questions, then take a formal retest to
            measure your improvement.
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <button
              className="btn btn-primary"
              onClick={handlePractice}
              disabled={generatingPractice || generatingRetest}
            >
              {generatingPractice ? (
                <>
                  <Spinner size="sm" /> Building practice quiz…
                </>
              ) : (
                'Start Targeted Practice'
              )}
            </button>
            <button
              className="btn btn-secondary"
              onClick={handleRetest}
              disabled={generatingPractice || generatingRetest}
            >
              {generatingRetest ? (
                <>
                  <Spinner size="sm" /> Building retest…
                </>
              ) : (
                'Take Re-test'
              )}
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => navigate('/analytics')}
              disabled={generatingPractice || generatingRetest}
            >
              Back to Analytics
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
