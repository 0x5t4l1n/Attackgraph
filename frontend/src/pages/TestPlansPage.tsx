import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { ClipboardList, ChevronDown, ChevronRight } from 'lucide-react';
import { api, type TestPlan } from '../services/api';
import { PageHeader, EmptyState, LoadingState, ErrorState, StatusBadge, SearchInput, useToast, useAsync } from '../components/ui';

const STATUS_OPTIONS = ['pending', 'approved', 'running', 'completed', 'cancelled'];

export default function TestPlansPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);

  const { data: plans, loading, error, reload } = useAsync(
    () => api.listTestPlans(projectId!),
    [projectId],
  );

  const handleStatusChange = async (planId: string, status: string) => {
    setUpdating(planId);
    try {
      await api.updateTestPlan(projectId!, planId, { status });
      toast('success', 'Status updated');
      reload();
    } catch (e: unknown) {
      toast('error', e instanceof Error ? e.message : 'Update failed');
    } finally {
      setUpdating(null);
    }
  };

  if (loading) return <LoadingState message="Loading test plans..." />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const filtered = (plans ?? []).filter((p: TestPlan) => {
    const q = search.toLowerCase();
    if (q && !p.hypothesis.toLowerCase().includes(q)) return false;
    if (statusFilter !== 'all' && p.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Test Plans"
        icon={<ClipboardList size={20} />}
        subtitle={`${filtered.length} plans`}
      />

      <div className="toolbar">
        <SearchInput value={search} onChange={setSearch} placeholder="Search hypothesis..." />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="all">All Statuses</option>
          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<ClipboardList size={32} />}
          title="No test plans"
          description={plans?.length ? 'No plans match your filters.' : 'Run analysis to generate test plans.'}
        />
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map((p: TestPlan) => {
            const isOpen = expanded === p.id;
            return (
              <div key={p.id} className="card">
                <div
                  className="expand-row"
                  onClick={() => setExpanded(isOpen ? null : p.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <span className="expand-icon">{isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</span>
                  <span className="flex-1 text-sm">{p.hypothesis}</span>
                  <StatusBadge status={p.status} />
                </div>

                {isOpen && (
                  <div className="detail-panel" style={{ margin: '0 16px 16px' }}>
                    {(p.required_accounts ?? []).length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Required Accounts</div>
                        <div className="chip-list">
                          {p.required_accounts.map((a, i) => <span key={i} className="chip">{a}</span>)}
                        </div>
                      </div>
                    )}
                    {(p.preconditions ?? []).length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Preconditions</div>
                        <ul className="text-sm" style={{ margin: 0, paddingLeft: 16 }}>
                          {p.preconditions.map((c, i) => <li key={i}>{c}</li>)}
                        </ul>
                      </div>
                    )}
                    {p.test_procedure && (
                      <div className="detail-section">
                        <div className="detail-label">Test Procedure</div>
                        <pre className="text-xs" style={{ margin: 0, whiteSpace: 'pre-wrap', background: 'var(--bg-app)', padding: '8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)' }}>{p.test_procedure}</pre>
                      </div>
                    )}
                    {p.expected_secure_behavior && (
                      <div className="detail-section">
                        <div className="detail-label">Expected Secure Behavior</div>
                        <div className="detail-value">{p.expected_secure_behavior}</div>
                      </div>
                    )}
                    {(p.potential_insecure_outcomes ?? []).length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Potential Insecure Outcomes</div>
                        <ul className="text-sm" style={{ margin: 0, paddingLeft: 16, color: 'var(--danger)' }}>
                          {p.potential_insecure_outcomes.map((o, i) => <li key={i}>{o}</li>)}
                        </ul>
                      </div>
                    )}
                    {(p.evidence_to_capture ?? []).length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Evidence to Capture</div>
                        <ul className="text-sm" style={{ margin: 0, paddingLeft: 16 }}>
                          {(p.evidence_to_capture ?? []).map((e, i) => <li key={i}>{e}</li>)}
                        </ul>
                      </div>
                    )}
                    {(p.cleanup_steps ?? []).length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Cleanup Steps</div>
                        <ul className="text-sm" style={{ margin: 0, paddingLeft: 16 }}>
                          {p.cleanup_steps.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      </div>
                    )}
                    {(p.limitations ?? []).length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Limitations</div>
                        <ul className="text-sm text-muted" style={{ margin: 0, paddingLeft: 16 }}>
                          {p.limitations.map((l, i) => <li key={i}>{l}</li>)}
                        </ul>
                      </div>
                    )}
                    <div className="detail-section">
                      <div className="detail-label">Status</div>
                      <div className="flex gap-2 items-center">
                        <select
                          value={p.status}
                          onChange={e => handleStatusChange(p.id, e.target.value)}
                          disabled={updating === p.id}
                          onClick={e => e.stopPropagation()}
                        >
                          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                        {updating === p.id && <span className="text-muted text-xs">Saving…</span>}
                      </div>
                    </div>
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
