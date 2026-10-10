import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api, type TestPlan } from '../services/api';
import { ClipboardList, ChevronDown, ChevronRight } from 'lucide-react';

export default function TestPlansPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [plans, setPlans] = useState<TestPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!projectId) return;
    api.listTestPlans(projectId).then(setPlans).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [projectId]);

  const updateStatus = async (planId: string, status: string) => {
    if (!projectId) return;
    await api.updateTestPlan(projectId, planId, { status });
    setPlans(prev => prev.map(p => p.id === planId ? { ...p, status } : p));
  };

  if (loading) return <div className="loading">Loading test plans...</div>;
  if (error) return <div className="card" style={{ color: 'var(--danger)' }}>{error}</div>;

  return (
    <div>
      <div className="page-header">
        <h1><ClipboardList size={20} style={{ verticalAlign: 'middle', marginRight: 8 }} />Test Plans</h1>
        <span style={{ color: 'var(--text-secondary)' }}>{plans.length} plans</span>
      </div>

      {plans.length === 0 ? (
        <div className="empty-state"><p>No test plans generated. Run analysis first.</p></div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {plans.map(p => (
            <div key={p.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                onClick={() => setExpanded(expanded === p.id ? null : p.id)}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {expanded === p.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <span style={{ fontWeight: 600 }}>{p.hypothesis}</span>
                </div>
                <select value={p.status} onClick={e => e.stopPropagation()}
                  onChange={e => updateStatus(p.id, e.target.value)}
                  style={{ width: 'auto', padding: '0.25rem 0.5rem' }}>
                  <option value="pending">Pending</option>
                  <option value="approved">Approved</option>
                  <option value="running">Running</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              {expanded === p.id && (
                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
                  <div style={{ marginBottom: '1rem' }}>
                    <strong>Required Accounts:</strong>
                    <ul style={{ paddingLeft: '1.25rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      {p.required_accounts.map((a: string, i: number) => <li key={i}>{a}</li>)}
                    </ul>
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <strong>Test Procedure:</strong>
                    <pre style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 6, marginTop: '0.5rem', whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      {p.test_procedure}
                    </pre>
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <strong>Expected Secure Behavior:</strong>
                    <p style={{ color: 'var(--success)', marginTop: '0.25rem' }}>{p.expected_secure_behavior}</p>
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <strong>Potential Insecure Outcomes:</strong>
                    <ul style={{ paddingLeft: '1.25rem', color: 'var(--danger)', marginTop: '0.25rem' }}>
                      {p.potential_insecure_outcomes.map((o: string, i: number) => <li key={i}>{o}</li>)}
                    </ul>
                  </div>

                  {p.limitations.length > 0 && (
                    <div>
                      <strong>Limitations:</strong>
                      <ul style={{ paddingLeft: '1.25rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                        {p.limitations.map((l: string, i: number) => <li key={i}>{l}</li>)}
                      </ul>
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
