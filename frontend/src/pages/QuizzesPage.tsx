import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { quizzesApi } from '../api/quizzes';
import { AppShell, TopBar } from '../components/layout/Sidebar';
import { Skeleton } from '../components/common/Spinner';
import { EmptyState } from '../components/common/Alert';
import type { QuizSummary } from '../types/api';

function quizTypeBadge(type: string) {
  if (type === 'practice') return <span className="badge badge-practice">Practice</span>;
  if (type === 'retest') return <span className="badge badge-retest">Retest</span>;
  return <span className="badge badge-gray">Standard</span>;
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export function QuizzesPage() {
  const navigate = useNavigate();
  const [quizzes, setQuizzes] = useState<QuizSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    quizzesApi.list()
      .then(setQuizzes)
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <TopBar
        title="Quizzes"
        onMenuClick={() => {}}
        actions={
          <Link to="/quizzes/new" className="btn btn-primary btn-sm">
            + Generate Quiz
          </Link>
        }
      />

      <div style={{ padding: '28px 32px', maxWidth: 900, margin: '0 auto' }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Your Quizzes</h1>
          <p style={{ color: 'var(--color-muted)', marginTop: 4, fontSize: '0.875rem' }}>
            Generate quizzes from your study material and track your progress.
          </p>
        </div>

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[...Array(4)].map((_, i) => <Skeleton key={i} height={72} />)}
          </div>
        ) : quizzes.length === 0 ? (
          <div className="card">
            <EmptyState
              icon="✎"
              title="No quizzes yet"
              description="Generate your first quiz from your study notes."
              action={<Link to="/quizzes/new" className="btn btn-primary">Generate a Quiz</Link>}
            />
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {quizzes.map((quiz) => (
              <div
                key={quiz.id}
                className="card card-pad fade-in"
                style={{ cursor: 'pointer', transition: 'all 0.15s ease' }}
                onClick={() => navigate(`/quizzes/${quiz.id}/take`)}
                onMouseEnter={e => (e.currentTarget.style.boxShadow = 'var(--shadow-md)')}
                onMouseLeave={e => (e.currentTarget.style.boxShadow = 'var(--shadow-sm)')}
                role="button"
                tabIndex={0}
                onKeyDown={e => { if (e.key === 'Enter') navigate(`/quizzes/${quiz.id}/take`); }}
                aria-label={`Open quiz: ${quiz.title}`}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      background: 'var(--color-primary-light)',
                      borderRadius: 10,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 18,
                      flexShrink: 0,
                    }}
                  >
                    ✎
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {quiz.title}
                    </div>
                    <div style={{ fontSize: '0.775rem', color: 'var(--color-muted)', marginTop: 3 }}>
                      {quiz.question_count} questions · {formatDate(quiz.created_at)}
                      {quiz.target_topic && ` · ${quiz.target_topic}`}
                    </div>
                  </div>
                  <div style={{ flexShrink: 0 }}>{quizTypeBadge(quiz.quiz_type)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
