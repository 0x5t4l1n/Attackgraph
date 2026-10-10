import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, type Finding } from '../services/api';

export default function FindingsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [sevFilter, setSevFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    api
      .listFindings(projectId)
      .then(setFindings)
      .finally(() => setLoading(false));
  }, [projectId]);

  const handleStatusChange = (findingId: string, status: string) => {
    if (!projectId) return;
    api.updateFinding(projectId, findingId, { validation_status: status }).then(() => {
      setFindings((prev) =>
        prev.map((f) => (f.id === findingId ? { ...f, validation_status: status } : f)),
      );
    });
  };

  const filtered = findings.filter((f) => {
    if (sevFilter && f.severity !== sevFilter) return false;
    if (statusFilter && f.validation_status !== statusFilter) return false;
    return true;
  });

  if (loading) return <div className="loading">Loading findings...</div>;

  return (
    <div>
      <div className="page-header">
        <h1>Findings ({filtered.length})</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <select value={sevFilter} onChange={(e) => setSevFilter(e.target.value)} style={{ width: 'auto' }}>
            <option value="">All Severities</option>
            {['critical', 'high', 'medium', 'low', 'info'].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ width: 'auto' }}>
            <option value="">All Statuses</option>
            {['hypothesis', 'unvalidated', 'confirmed', 'false_positive', 'inconclusive'].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">No findings. Run analysis to generate security hypotheses.</div>
      ) : (
        <div>
          {filtered.map((f) => (
            <div
              key={f.id}
              className="card"
              style={{ marginBottom: '0.75rem', cursor: 'pointer' }}
              onClick={() => setExpanded(expanded === f.id ? null : f.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{f.title}</div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
                    <span className={`badge badge-${f.severity}`}>{f.severity}</span>
                    <span className={`badge badge-${f.validation_status === 'confirmed' ? 'confirmed' : 'hypothesis'}`}>
                      {f.validation_status}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Confidence: {(f.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <select
                  value={f.validation_status}
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) => handleStatusChange(f.id, e.target.value)}
                  style={{ width: 'auto', fontSize: '0.75rem' }}
                >
                  <option value="hypothesis">Hypothesis</option>
                  <option value="unvalidated">Unvalidated</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="false_positive">False Positive</option>
                  <option value="inconclusive">Inconclusive</option>
                </select>
              </div>

              {expanded === f.id && (
                <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border)', paddingTop: '1rem', fontSize: '0.85rem' }}>
                  <div style={{ marginBottom: '0.75rem' }}>
                    <strong>Description:</strong>
                    <div style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{f.description}</div>
                  </div>
                  <div style={{ marginBottom: '0.75rem' }}>
                    <strong>Reasoning:</strong>
                    <div style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{f.reasoning}</div>
                  </div>
                  <div style={{ marginBottom: '0.75rem' }}>
                    <strong>Affected Endpoints:</strong>
                    <div style={{ fontFamily: 'monospace', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                      {f.affected_endpoints.map((ep, i) => <div key={i}>{ep}</div>)}
                    </div>
                  </div>
                  <div style={{ marginBottom: '0.75rem' }}>
                    <strong>Assumptions:</strong>
                    <ul style={{ marginLeft: '1rem', color: 'var(--text-secondary)' }}>
                      {f.assumptions.map((a, i) => <li key={i}>{a}</li>)}
                    </ul>
                  </div>
                  <div style={{ marginBottom: '0.75rem' }}>
                    <strong>Reproduction Steps:</strong>
                    <pre style={{ background: 'var(--bg-primary)', padding: '0.75rem', borderRadius: 4, whiteSpace: 'pre-wrap', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                      {f.reproduction_steps}
                    </pre>
                  </div>
                  <div>
                    <strong>Remediation:</strong>
                    <div style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{f.remediation}</div>
                  </div>
                  <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Detection rule: {f.detection_rule}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
