import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '../services/api';
import { PageHeader, EmptyState, LoadingState, ErrorState, SeverityBadge, StatusBadge, SearchInput, useToast, useAsync } from '../components/ui';

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];
const STATUS_OPTIONS = ['hypothesis', 'unvalidated', 'confirmed', 'false_positive', 'inconclusive'];

export default function FindingsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);

  const { data: findings, loading, error, reload } = useAsync(
    () => api.listFindings(projectId!),
    [projectId],
  );

  const handleStatusChange = async (findingId: string, status: string) => {
    setUpdating(findingId);
    try {
      await api.updateFinding(projectId!, findingId, { validation_status: status });
      toast('success', 'Status updated');
      reload();
    } catch (e: unknown) {
      toast('error', e instanceof Error ? e.message : 'Update failed');
    } finally {
      setUpdating(null);
    }
  };

  if (loading) return <LoadingState message="Loading findings..." />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const sorted = [...(findings ?? [])].sort((a, b) =>
    SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)
  );

  const filtered = sorted.filter(f => {
    const q = search.toLowerCase();
    if (q && !f.title.toLowerCase().includes(q) && !f.description.toLowerCase().includes(q)) return false;
    if (severityFilter !== 'all' && f.severity !== severityFilter) return false;
    if (statusFilter !== 'all' && f.validation_status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Findings"
        icon={<AlertTriangle size={20} />}
        subtitle={`${filtered.length} of ${(findings ?? []).length} findings`}
      />

      <div className="toolbar">
        <SearchInput value={search} onChange={setSearch} placeholder="Search findings..." />
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}>
          <option value="all">All Severities</option>
          {SEVERITY_ORDER.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="all">All Statuses</option>
          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<AlertTriangle size={32} />}
          title="No findings"
          description={findings?.length ? 'No findings match your filters.' : 'Run analysis to detect findings.'}
        />
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map(f => {
            const isOpen = expanded === f.id;
            return (
              <div key={f.id} className="card">
                <div
                  className="expand-row"
                  onClick={() => setExpanded(isOpen ? null : f.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <span className="expand-icon">{isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</span>
                  <SeverityBadge severity={f.severity} />
                  <span className="flex-1 text-sm" style={{ fontWeight: 500 }}>{f.title}</span>
                  <span className="text-muted text-xs">{Math.round(f.confidence * 100)}% confidence</span>
                  <StatusBadge status={f.validation_status} />
                </div>

                {isOpen && (
                  <div className="detail-panel" style={{ margin: '0 16px 16px' }}>
                    <div className="detail-section">
                      <div className="detail-label">Description</div>
                      <div className="detail-value">{f.description}</div>
                    </div>
                    {f.reasoning && (
                      <div className="detail-section">
                        <div className="detail-label">Reasoning</div>
                        <div className="detail-value">{f.reasoning}</div>
                      </div>
                    )}
                    {f.affected_endpoints.length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Affected Endpoints</div>
                        <div className="chip-list">
                          {f.affected_endpoints.map((ep, i) => <span key={i} className="chip">{ep}</span>)}
                        </div>
                      </div>
                    )}
                    {f.assumptions.length > 0 && (
                      <div className="detail-section">
                        <div className="detail-label">Assumptions</div>
                        <ul className="text-sm" style={{ margin: 0, paddingLeft: 16 }}>
                          {f.assumptions.map((a, i) => <li key={i}>{a}</li>)}
                        </ul>
                      </div>
                    )}
                    {f.reproduction_steps && (
                      <div className="detail-section">
                        <div className="detail-label">Reproduction Steps</div>
                        <pre className="text-xs" style={{ margin: 0, whiteSpace: 'pre-wrap', background: 'var(--bg-app)', padding: 8, borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>{f.reproduction_steps}</pre>
                      </div>
                    )}
                    {f.remediation && (
                      <div className="detail-section">
                        <div className="detail-label">Remediation</div>
                        <div className="detail-value">{f.remediation}</div>
                      </div>
                    )}
                    {f.detection_rule && (
                      <div className="detail-section">
                        <div className="detail-label">Detection Rule</div>
                        <pre className="text-xs mono" style={{ margin: 0, background: 'var(--bg-app)', padding: 8, borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>{f.detection_rule}</pre>
                      </div>
                    )}
                    <div className="detail-section">
                      <div className="detail-label">Validation Status</div>
                      <div className="flex gap-2 items-center">
                        <select
                          value={f.validation_status}
                          onChange={e => handleStatusChange(f.id, e.target.value)}
                          disabled={updating === f.id}
                        >
                          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
                        </select>
                        {updating === f.id && <span className="text-muted text-xs">Saving…</span>}
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
