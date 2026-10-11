import { useState, Fragment } from 'react';
import { useParams } from 'react-router-dom';
import { Route, ChevronDown, ChevronRight, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import { PageHeader, EmptyState, LoadingState, ErrorState, SearchInput, useAsync } from '../components/ui';

export default function AttackPathsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: paths, loading, error, reload } = useAsync(
    () => api.listAttackPaths(projectId!),
    [projectId],
  );

  if (loading) return <LoadingState message="Loading attack paths..." />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const sorted = [...(paths ?? [])].sort((a, b) => b.priority_score - a.priority_score);
  const filtered = sorted.filter(p => {
    const q = search.toLowerCase();
    return !q || p.entry_point.toLowerCase().includes(q) || p.target_operation.toLowerCase().includes(q);
  });

  const priorityClass = (score: number) => {
    if (score >= 0.8) return 'badge badge-danger';
    if (score >= 0.5) return 'badge badge-warning';
    return 'badge badge-info';
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Attack Paths"
        icon={<Route size={20} />}
        subtitle={`${filtered.length} paths`}
      />

      <div className="toolbar">
        <SearchInput value={search} onChange={setSearch} placeholder="Search entry point or target..." />
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Route size={32} />}
          title="No attack paths"
          description={paths?.length ? 'No paths match your search.' : 'Run analysis to generate attack paths.'}
        />
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map(p => {
            const isOpen = expanded === p.id;
            return (
              <div key={p.id} className="card">
                <div
                  className="expand-row"
                  onClick={() => setExpanded(isOpen ? null : p.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <span className="expand-icon">{isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</span>
                  <div className="flex-1 flex flex-col gap-1">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="badge badge-accent" style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>{p.entry_point}</span>
                      <ArrowRight size={12} style={{ color: 'var(--text-muted)' }} />
                      <span className="badge badge-danger" style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>{p.target_operation}</span>
                    </div>
                  </div>
                  <span className={priorityClass(p.priority_score)}>priority {Math.round(p.priority_score * 100)}%</span>
                  <span className="badge badge-neutral">{Math.round(p.confidence * 100)}% confidence</span>
                </div>

                {isOpen && (
                  <div className="detail-panel" style={{ margin: '0 16px 16px' }}>
                    {p.potential_impact && (
                      <div className="detail-section">
                        <div className="detail-label">Impact</div>
                        <div className="detail-value">{p.potential_impact}</div>
                      </div>
                    )}

                    {p.intermediate_steps.length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Path</div>
                        <div className="flex items-center gap-1" style={{ flexWrap: 'wrap' }}>
                          <span className="badge badge-accent" style={{ fontSize: 10 }}>{p.entry_point}</span>
                          {p.intermediate_steps.map((s, i) => (
                            <Fragment key={s.node_id || i}>
                              <ArrowRight size={10} style={{ color: 'var(--text-muted)' }} />
                              <span className="badge badge-hypothesis" style={{ fontSize: 10 }}>{s.label}</span>
                            </Fragment>
                          ))}
                          <ArrowRight size={10} style={{ color: 'var(--text-muted)' }} />
                          <span className="badge badge-danger" style={{ fontSize: 10 }}>{p.target_operation}</span>
                        </div>
                      </div>
                    )}

                    {p.unverified_assumptions.length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label" style={{ color: 'var(--warning)' }}>Unverified Assumptions</div>
                        <ul className="text-sm" style={{ margin: 0, paddingLeft: 16, color: 'var(--warning)' }}>
                          {p.unverified_assumptions.map((a, i) => <li key={i}>{a}</li>)}
                        </ul>
                      </div>
                    )}

                    {p.preconditions.length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Preconditions</div>
                        <ul className="text-sm" style={{ margin: 0, paddingLeft: 16 }}>
                          {p.preconditions.map((c, i) => <li key={i}>{c}</li>)}
                        </ul>
                      </div>
                    )}

                    {p.recommended_steps.length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Recommended Steps</div>
                        <ol className="text-sm" style={{ margin: 0, paddingLeft: 16 }}>
                          {p.recommended_steps.map((s, i) => <li key={i}>{s}</li>)}
                        </ol>
                      </div>
                    )}

                    {p.observations.length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Observations</div>
                        <ul className="text-sm" style={{ margin: 0, paddingLeft: 16 }}>
                          {p.observations.map((o, i) => <li key={i}>{o}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
