import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyticsApi } from '../api/analytics';
import { improvementApi } from '../api/improvement';
import { AppShell, TopBar } from '../components/layout/Sidebar';
import { Skeleton } from '../components/common/Spinner';
import { Alert, EmptyState } from '../components/common/Alert';
import { extractErrorMessage } from '../api/client';
import type { AnalyticsOverview, TopicStat, WeakTopicSummary, AttemptSummary } from '../types/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

function statusBadge(status: string) {
  switch (status) {
    case 'strong': return <span className="badge badge-strong">Strong</span>;
    case 'improving': return <span className="badge badge-improving">Improving</span>;
    case 'weak': return <span className="badge badge-weak">Weak</span>;
    case 'insufficient_data': return <span className="badge badge-insufficient">Insufficient Data</span>;
    default: return <span className="badge badge-gray">{status}</span>;
  }
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function AnalyticsPage() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [topics, setTopics] = useState<TopicStat[]>([]);
  const [weakTopics, setWeakTopics] = useState<WeakTopicSummary[]>([]);
  const [history, setHistory] = useState<AttemptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [improvingTopic, setImprovingTopic] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      analyticsApi.overview(),
      analyticsApi.topics(),
      analyticsApi.weakTopics(),
      analyticsApi.history(),
    ])
      .then(([ov, tp, wt, hist]) => {
        setOverview(ov);
        setTopics(tp);
        setWeakTopics(wt);
        setHistory(hist);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  async function handleImprove(topic: string) {
    setImprovingTopic(topic);
    try {
      const plan = await improvementApi.createPlan({ topic });
      navigate(`/improvement/${plan.id}`);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setImprovingTopic(null);
    }
  }

  // Build chart data from history (last 10 attempts)
  const chartData = [...history]
    .slice(0, 10)
    .reverse()
    .map((a, i) => ({
      name: formatDate(a.submitted_at ?? a.started_at),
      score: a.score_percentage,
      index: i + 1,
    }));

  if (loading) {
    return (
      <AppShell>
        <TopBar title="Analytics" onMenuClick={() => {}} />
        <div style={{ padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[...Array(3)].map((_, i) => <Skeleton key={i} height={100} />)}
        </div>
      </AppShell>
    );
  }

  const hasData = overview && overview.total_attempts > 0;

  return (
    <AppShell>
      <TopBar title="Analytics" onMenuClick={() => {}} />

      <div style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto' }}>
        {error && <div style={{ marginBottom: 20 }}><Alert message={error} onDismiss={() => setError('')} /></div>}

        {!hasData ? (
          <div className="card">
            <EmptyState
              icon="📊"
              title="No analytics yet"
              description="Take a quiz to start building your performance profile."
              action={<button className="btn btn-primary" onClick={() => navigate('/quizzes/new')}>Generate a Quiz</button>}
            />
          </div>
        ) : (
          <>
            {/* Overview cards */}
            <section style={{ marginBottom: 32 }}>
              <h2 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
                Overview
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
                <div className="stat-card">
                  <div className="stat-value" style={{ color: 'var(--color-primary)' }}>
                    {overview!.average_score.toFixed(1)}%
                  </div>
                  <div className="stat-label">Average Score</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{overview!.total_attempts}</div>
                  <div className="stat-label">Total Quizzes</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{overview!.questions_answered}</div>
                  <div className="stat-label">Questions Answered</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ color: 'var(--color-success)' }}>
                    {overview!.correct_answers}
                  </div>
                  <div className="stat-label">Correct Answers</div>
                </div>
              </div>
            </section>

            {/* Score history chart */}
            {chartData.length > 1 && (
              <section style={{ marginBottom: 32 }}>
                <h2 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
                  Score History
                </h2>
                <div className="card card-pad">
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--color-muted)' }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: 'var(--color-muted)' }} unit="%" />
                      <Tooltip
                        formatter={(val: unknown) => [`${(val as number).toFixed(1)}%`, 'Score']}
                        contentStyle={{ border: '1px solid var(--color-border)', borderRadius: 8, boxShadow: 'var(--shadow-md)' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="score"
                        stroke="var(--color-primary)"
                        strokeWidth={2}
                        dot={{ fill: 'var(--color-primary)', r: 4 }}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </section>
            )}

            {/* Needs Attention */}
            {weakTopics.length > 0 && (
              <section style={{ marginBottom: 32 }}>
                <h2 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
                  Needs Attention
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                  {weakTopics.map((t) => (
                    <div key={t.topic} className="card card-pad" style={{ borderLeft: '3px solid var(--color-danger)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{t.topic}</div>
                        <span className="badge badge-weak">Weak</span>
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-danger)', marginBottom: 10 }}>
                        {t.accuracy.toFixed(0)}%
                      </div>
                      <button
                        className="btn btn-primary btn-sm"
                        style={{ width: '100%' }}
                        disabled={improvingTopic === t.topic}
                        onClick={() => handleImprove(t.topic)}
                      >
                        {improvingTopic === t.topic ? 'Building plan…' : 'Improve This Topic'}
                      </button>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Topic breakdown */}
            <section>
              <h2 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
                Topic Performance
              </h2>
              <div className="card" style={{ overflow: 'hidden' }}>
                {topics.length === 0 ? (
                  <EmptyState icon="📐" title="No topic data yet" description="Answer more questions to see per-topic stats." />
                ) : (
                  <div>
                    {topics.map((t, i) => (
                      <div
                        key={t.topic}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 14,
                          padding: '14px 20px',
                          borderTop: i === 0 ? 'none' : '1px solid var(--color-border)',
                        }}
                      >
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 500, fontSize: '0.875rem', marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {t.topic}
                          </div>
                          {t.status !== 'insufficient_data' && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <div className="progress-bar-track" style={{ height: 6, flex: 1, maxWidth: 200 }}>
                                <div
                                  className="progress-bar-fill"
                                  style={{
                                    width: `${t.accuracy}%`,
                                    background:
                                      t.accuracy >= 80 ? 'var(--color-success)' :
                                      t.accuracy >= 60 ? 'var(--color-warning)' :
                                      'var(--color-danger)',
                                  }}
                                />
                              </div>
                              <span style={{ fontSize: '0.8rem', fontWeight: 600, minWidth: 36 }}>
                                {t.accuracy.toFixed(0)}%
                              </span>
                            </div>
                          )}
                          {t.status === 'insufficient_data' && (
                            <div style={{ fontSize: '0.775rem', color: 'var(--color-muted)' }}>
                              Answer more questions on this topic to classify it.
                            </div>
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
                          <span style={{ fontSize: '0.775rem', color: 'var(--color-muted)' }}>
                            {t.questions_answered} answered
                          </span>
                          {statusBadge(t.status)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
