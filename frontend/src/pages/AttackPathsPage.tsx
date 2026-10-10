import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api, type AttackPath } from '../services/api';
import { Route, ChevronDown, ChevronRight } from 'lucide-react';

export default function AttackPathsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [paths, setPaths] = useState<AttackPath[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!projectId) return;
    api.listAttackPaths(projectId).then(setPaths).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <div className="loading">Loading attack paths...</div>;
  if (error) return <div className="card" style={{ color: 'var(--danger)' }}>{error}</div>;

  return (
    <div>
      <div className="page-header">
        <h1><Route size={20} style={{ verticalAlign: 'middle', marginRight: 8 }} />Attack Paths</h1>
        <span style={{ color: 'var(--text-secondary)' }}>{paths.length} candidate paths</span>
      </div>

      {paths.length === 0 ? (
        <div className="empty-state">
          <p>No attack paths found. Run analysis first.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {paths.map(p => (
            <div key={p.id} className="card" style={{ cursor: 'pointer' }} onClick={() => setExpanded(expanded === p.id ? null : p.id)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {expanded === p.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <span style={{ fontWeight: 600 }}>{p.entry_point}</span>
                  <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
                  <span style={{ fontWeight: 600, color: 'var(--danger)' }}>{p.target_operation}</span>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <span className="badge badge-medium">Priority: {p.priority_score.toFixed(2)}</span>
                  <span className="badge badge-info">Confidence: {(p.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>

              {expanded === p.id && (
                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
                  <div style={{ marginBottom: '1rem' }}>
                    <strong>Impact:</strong> <span style={{ color: 'var(--text-secondary)' }}>{p.potential_impact}</span>
                  </div>

                  {p.intermediate_steps.length > 0 && (
                    <div style={{ marginBottom: '1rem' }}>
                      <strong>Path:</strong>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                        <span className="badge badge-info">{p.entry_point}</span>
                        {p.intermediate_steps.map((s: any, i: number) => (
                          <span key={i}>
                            <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
                            <span className="badge badge-hypothesis" style={{ marginLeft: '0.5rem' }}>{s.label}</span>
                          </span>
                        ))}
                        <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
                        <span className="badge badge-high">{p.target_operation}</span>
                      </div>
                    </div>
                  )}

                  {p.unverified_assumptions.length > 0 && (
                    <div style={{ marginBottom: '1rem' }}>
                      <strong>Unverified Assumptions:</strong>
                      <ul style={{ marginTop: '0.25rem', paddingLeft: '1.25rem', color: 'var(--warning)' }}>
                        {p.unverified_assumptions.map((a: string, i: number) => <li key={i}>{a}</li>)}
                      </ul>
                    </div>
                  )}

                  {p.recommended_steps.length > 0 && (
                    <div>
                      <strong>Recommended Steps:</strong>
                      <ol style={{ marginTop: '0.25rem', paddingLeft: '1.25rem', color: 'var(--text-secondary)' }}>
                        {p.recommended_steps.map((s: string, i: number) => <li key={i}>{s}</li>)}
                      </ol>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
