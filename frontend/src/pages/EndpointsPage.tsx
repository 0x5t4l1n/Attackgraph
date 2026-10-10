import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, type Endpoint, type EndpointDetail } from '../services/api';

export default function EndpointsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [methodFilter, setMethodFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [selected, setSelected] = useState<EndpointDetail | null>(null);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    api
      .listEndpoints(projectId)
      .then(setEndpoints)
      .finally(() => setLoading(false));
  }, [projectId]);

  const handleSelect = (ep: Endpoint) => {
    if (!projectId) return;
    api.getEndpoint(projectId, ep.id).then(setSelected).catch(() => {});
  };

  const filtered = endpoints.filter((ep) => {
    if (methodFilter && ep.method !== methodFilter) return false;
    if (sourceFilter && ep.discovery_source !== sourceFilter) return false;
    return true;
  });

  const methods = [...new Set(endpoints.map((e) => e.method))].sort();
  const sources = [...new Set(endpoints.map((e) => e.discovery_source))].sort();

  const methodColor = (m: string) => {
    switch (m) {
      case 'GET': return '#3fb950';
      case 'POST': return '#58a6ff';
      case 'PUT': return '#d29922';
      case 'PATCH': return '#d29922';
      case 'DELETE': return '#f85149';
      default: return 'var(--text-secondary)';
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Endpoints ({filtered.length})</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <select value={methodFilter} onChange={(e) => setMethodFilter(e.target.value)} style={{ width: 'auto' }}>
            <option value="">All Methods</option>
            {methods.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} style={{ width: 'auto' }}>
            <option value="">All Sources</option>
            {sources.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading endpoints...</div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">No endpoints found. Run a crawl or import traffic first.</div>
      ) : (
        <div style={{ display: 'flex', gap: '1rem' }}>
          <div style={{ flex: 1, overflow: 'auto', maxHeight: 'calc(100vh - 150px)' }}>
            <table>
              <thead>
                <tr>
                  <th>Method</th>
                  <th>URL</th>
                  <th>Status</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((ep) => (
                  <tr
                    key={ep.id}
                    onClick={() => handleSelect(ep)}
                    style={{
                      cursor: 'pointer',
                      background: selected?.id === ep.id ? 'var(--bg-tertiary)' : 'transparent',
                    }}
                  >
                    <td><span style={{ color: methodColor(ep.method), fontWeight: 600, fontFamily: 'monospace' }}>{ep.method}</span></td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ep.url}</td>
                    <td>{ep.status_code || '-'}</td>
                    <td><span className="badge badge-info">{ep.discovery_source}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selected && (
            <div className="card" style={{ width: 400, flexShrink: 0, maxHeight: 'calc(100vh - 150px)', overflowY: 'auto' }}>
              <h2 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Endpoint Details</h2>
              <div style={{ fontSize: '0.85rem' }}>
                <div style={{ marginBottom: '0.5rem' }}>
                  <span style={{ color: methodColor(selected.method), fontWeight: 600 }}>{selected.method}</span>{' '}
                  <span style={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>{selected.url}</span>
                </div>
                <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Status: {selected.status_code || 'unknown'}</div>
                <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Content-Type: {selected.content_type || 'unknown'}</div>
                <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Source: {selected.discovery_source}</div>
                {selected.parent_url && (
                  <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Parent: <span style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{selected.parent_url}</span></div>
                )}

                {selected.observations.length > 0 && (
                  <>
                    <h3 style={{ fontSize: '0.9rem', marginTop: '1rem', marginBottom: '0.5rem' }}>
                      Observations ({selected.observations.length})
                    </h3>
                    {selected.observations.map((obs) => (
                      <div key={obs.id} style={{ borderBottom: '1px solid var(--border)', padding: '0.5rem 0', fontSize: '0.8rem' }}>
                        <div>{obs.request_method} {obs.request_url}</div>
                        <div style={{ color: 'var(--text-muted)' }}>
                          Status: {obs.response_status || '-'} | Source: {obs.source_type} | {new Date(obs.timestamp).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
              <button onClick={() => setSelected(null)} style={{ marginTop: '1rem', width: '100%' }} type="button">Close</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
