import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { analyticsApi } from '../api/analytics';
import { AppShell, TopBar } from '../components/layout/Sidebar';
import { Skeleton } from '../components/common/Spinner';
import { EmptyState } from '../components/common/Alert';
import type { AnalyticsOverview, WeakTopicSummary } from '../types/api';
import { improvementApi } from '../api/improvement';
import { extractErrorMessage } from '../api/client';

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [weakTopics, setWeakTopics] = useState<WeakTopicSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [improvingTopic, setImprovingTopic] = useState<string | null>(null);
  const [improveError, setImproveError] = useState('');

  useEffect(() => {
    Promise.all([analyticsApi.overview(), analyticsApi.weakTopics()])
      .then(([ov, wt]) => {
        setOverview(ov);
        setWeakTopics(wt);
      })
      .catch(() => {/* analytics might be empty — silent fail */})
      .finally(() => setLoading(false));
  }, []);

  async function handleImprove(topic: string) {
    setImprovingTopic(topic);
    setImproveError('');
    try {
      const plan = await improvementApi.createPlan({ topic });
      navigate(`/improvement/${plan.id}`);
    } catch (err) {
      setImproveError(extractErrorMessage(err));
    } finally {
      setImprovingTopic(null);
    }
  }

  const hasData = overview && overview.total_attempts > 0;

  return (
    <AppShell>
      <TopBar title="Dashboard" onMenuClick={() => {}} />

      <div style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto' }}>
        {/* Greeting */}
        <div className="fade-in" style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            {getGreeting()}, {user?.username} 👋
          </h1>
          <p style={{ color: 'var(--color-muted)', marginTop: 4 }}>
            Ready to continue studying?
          </p>
        </div>

        {/* Quick Actions */}
        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
            Quick Actions
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
            {[
              { icon: '📄', title: 'Upload Study Material', desc: 'Add PDFs, DOCX or TXT', to: '/documents' },
              { icon: '💬', title: 'Ask StudySense', desc: 'Ask questions from your notes', to: '/chat' },
              { icon: '✎', title: 'Generate Quiz', desc: 'Test your understanding', to: '/quizzes/new' },
            ].map(({ icon, title, desc, to }) => (
              <Link
                key={to}
                to={to}
                style={{ textDecoration: 'none' }}
              >
                <div
                  className="card card-pad"
                  style={{
                    display: 'flex',
                    gap: 14,
                    alignItems: 'flex-start',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--shadow-md)';
                    (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--shadow-sm)';
                    (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      background: 'var(--color-primary-light)',
                      borderRadius: 10,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 20,
                      flexShrink: 0,
                    }}
                  >
                    {icon}
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{title}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--color-muted)', marginTop: 3 }}>{desc}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Stats */}
        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
            Performance Overview
          </h2>
          {loading ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
              {[...Array(4)].map((_, i) => <Skeleton key={i} height={88} />)}
            </div>
          ) : !hasData ? (
            <div className="card card-pad">
              <EmptyState
                icon="📊"
                title="No analytics yet"
                description="Take a quiz to start building your performance profile."
                action={<Link to="/quizzes/new" className="btn btn-primary btn-sm">Generate a Quiz</Link>}
              />
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
              <StatCard value={`${overview!.average_score.toFixed(1)}%`} label="Average Score" color="var(--color-primary)" />
              <StatCard value={overview!.total_attempts} label="Quizzes Taken" color="var(--color-text)" />
              <StatCard value={overview!.questions_answered} label="Questions Answered" color="var(--color-text)" />
              <StatCard value={overview!.correct_answers} label="Correct Answers" color="var(--color-success)" />
            </div>
          )}
        </section>

        {/* Needs Attention */}
        {!loading && weakTopics.length > 0 && (
          <section>
            <h2 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
              Needs Attention
            </h2>
            {improveError && (
              <div className="alert alert-error" style={{ marginBottom: 14 }}>{improveError}</div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 14 }}>
              {weakTopics.map((t) => (
                <div key={t.topic} className="card card-pad" style={{ borderLeft: '3px solid var(--color-danger)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{t.topic}</div>
                    <span className="badge badge-weak">Weak</span>
                  </div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-danger)', marginBottom: 12 }}>
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
      </div>
    </AppShell>
  );
}

function StatCard({ value, label, color }: { value: string | number; label: string; color: string }) {
  return (
    <div className="stat-card fade-in">
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
