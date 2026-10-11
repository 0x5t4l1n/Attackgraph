import { useState, useMemo, useCallback, Fragment } from 'react';
import { useParams } from 'react-router-dom';
import { Network, ChevronUp, ChevronDown, X } from 'lucide-react';
import { api, type Endpoint, type EndpointDetail } from '../services/api';
import {
  PageHeader,
  SearchInput,
  MethodBadge,
  RelativeTime,
  EmptyState,
  LoadingState,
  ErrorState,
  useAsync,
} from '../components/ui';

type SortKey = 'path' | 'status' | 'first_seen';
type SortDir = 'asc' | 'desc';

export default function EndpointsPage() {
  const { projectId } = useParams<{ projectId: string }>();

  const {
    data: endpoints,
    loading,
    error,
    reload,
  } = useAsync<Endpoint[]>(
    () => (projectId ? api.listEndpoints(projectId) : Promise.resolve([])),
    [projectId],
  );

  const [search, setSearch] = useState('');
  const [methodFilter, setMethodFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('path');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [selected, setSelected] = useState<EndpointDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Derived filter options
  const methods = useMemo(
    () => [...new Set((endpoints || []).map((e) => e.method))].sort(),
    [endpoints],
  );
  const sources = useMemo(
    () => [...new Set((endpoints || []).map((e) => e.discovery_source))].sort(),
    [endpoints],
  );

  // Filtered and sorted endpoints
  const filtered = useMemo(() => {
    let result = endpoints || [];
    if (search) {
      const q = search.toLowerCase();
      result = result.filter((ep) => ep.normalized_url.toLowerCase().includes(q) || ep.url.toLowerCase().includes(q));
    }
    if (methodFilter) {
      result = result.filter((ep) => ep.method === methodFilter);
    }
    if (sourceFilter) {
      result = result.filter((ep) => ep.discovery_source === sourceFilter);
    }
    // Sort
    result = [...result].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'path':
          cmp = a.normalized_url.localeCompare(b.normalized_url);
          break;
        case 'status':
          cmp = (a.status_code || 0) - (b.status_code || 0);
          break;
        case 'first_seen':
          cmp = new Date(a.first_seen).getTime() - new Date(b.first_seen).getTime();
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return result;
  }, [endpoints, search, methodFilter, sourceFilter, sortKey, sortDir]);

  const toggleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortKey(key);
        setSortDir('asc');
      }
    },
    [sortKey],
  );

  const handleSelect = useCallback(
    (ep: Endpoint) => {
      if (!projectId) return;
      if (selected?.id === ep.id) {
        setSelected(null);
        return;
      }
      setDetailLoading(true);
      api
        .getEndpoint(projectId, ep.id)
        .then(setSelected)
        .catch(() => setSelected(null))
        .finally(() => setDetailLoading(false));
    },
    [projectId, selected],
  );

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return null;
    return sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
  };

  return (
    <div>
      <PageHeader
        title="Endpoints"
        subtitle={endpoints ? `${filtered.length} of ${endpoints.length} endpoints` : undefined}
        icon={<Network size={20} />}
      />

      {/* Toolbar */}
      <div className="toolbar">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Filter by URL path..."
        />
        <div className="toolbar-divider" />
        <select value={methodFilter} onChange={(e) => setMethodFilter(e.target.value)}>
          <option value="">All Methods</option>
          {methods.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
          <option value="">All Sources</option>
          {sources.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <LoadingState message="Loading endpoints..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Network size={32} />}
          title="No endpoints found"
          description={
            endpoints && endpoints.length > 0
              ? 'No endpoints match the current filters. Try adjusting your search or filters.'
              : 'Run a crawl or import traffic to discover endpoints.'
          }
        />
      ) : (
        <div className="card">
          <div className="overflow-auto">
            <table>
              <thead>
                <tr>
                  <th>Method</th>
                  <th
                    className="expand-row"
                    onClick={() => toggleSort('path')}
                  >
                    <span className="flex items-center gap-1">
                      Path <SortIcon column="path" />
                    </span>
                  </th>
                  <th
                    className="expand-row"
                    onClick={() => toggleSort('status')}
                  >
                    <span className="flex items-center gap-1">
                      Status <SortIcon column="status" />
                    </span>
                  </th>
                  <th>Content Type</th>
                  <th>Source</th>
                  <th
                    className="expand-row"
                    onClick={() => toggleSort('first_seen')}
                  >
                    <span className="flex items-center gap-1">
                      First Seen <SortIcon column="first_seen" />
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((ep) => (
                  <Fragment key={ep.id}>
                    <tr
                      className="expand-row"
                      onClick={() => handleSelect(ep)}
                      style={selected?.id === ep.id ? { background: 'var(--bg-active)' } : undefined}
                    >
                      <td><MethodBadge method={ep.method} /></td>
                      <td className="mono truncate" style={{ maxWidth: 400 }}>{ep.normalized_url}</td>
                      <td>{ep.status_code || <span className="text-muted">--</span>}</td>
                      <td className="text-sm text-secondary truncate" style={{ maxWidth: 180 }}>
                        {ep.content_type || <span className="text-muted">--</span>}
                      </td>
                      <td><span className="badge badge-neutral">{ep.discovery_source}</span></td>
                      <td><RelativeTime date={ep.first_seen} /></td>
                    </tr>

                    {/* Inline expansion row — directly below selected row */}
                    {selected?.id === ep.id && (
                      <tr key={`${ep.id}-detail`}>
                        <td colSpan={6} style={{ padding: 0, background: 'var(--bg-surface)', borderBottom: `2px solid var(--accent)` }}>
                          {detailLoading ? (
                            <div className="p-4">
                              <LoadingState message="Loading endpoint details..." />
                            </div>
                          ) : (
                            <div className="detail-panel" style={{ margin: 0, borderRadius: 0, border: 'none', borderLeft: `3px solid var(--accent)` }}>
                              <div className="detail-section">
                                <div className="flex items-center justify-between mb-3">
                                  <div className="flex items-center gap-2">
                                    <MethodBadge method={ep.method} />
                                    <span className="mono text-sm">{ep.url}</span>
                                  </div>
                                  <button
                                    className="btn-ghost btn-icon btn-sm"
                                    onClick={(e) => { e.stopPropagation(); setSelected(null); }}
                                    type="button"
                                  >
                                    <X size={14} />
                                  </button>
                                </div>
                                <div className="grid grid-4 gap-4">
                                  <div>
                                    <div className="detail-label">Status Code</div>
                                    <div className="detail-value">{ep.status_code || 'Unknown'}</div>
                                  </div>
                                  <div>
                                    <div className="detail-label">Content Type</div>
                                    <div className="detail-value">{ep.content_type || 'Unknown'}</div>
                                  </div>
                                  <div>
                                    <div className="detail-label">Source</div>
                                    <div className="detail-value">
                                      <span className="badge badge-neutral">{ep.discovery_source}</span>
                                    </div>
                                  </div>
                                  <div>
                                    <div className="detail-label">First Seen</div>
                                    <div className="detail-value"><RelativeTime date={ep.first_seen} /></div>
                                  </div>
                                </div>
                                {ep.parent_url && (
                                  <div style={{ marginTop: 'var(--sp-3)' }}>
                                    <div className="detail-label">Parent URL</div>
                                    <div className="detail-value mono">{ep.parent_url}</div>
                                  </div>
                                )}
                              </div>

                              {selected && selected.observations.length > 0 && (
                                <div className="detail-section">
                                  <div className="detail-label mb-2">
                                    Observations ({selected.observations.length})
                                  </div>
                                  <table>
                                    <thead>
                                      <tr>
                                        <th>Method</th>
                                        <th>URL</th>
                                        <th>Status</th>
                                        <th>Content Type</th>
                                        <th>Timestamp</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {selected.observations.map((obs) => (
                                        <tr key={obs.id}>
                                          <td><MethodBadge method={obs.request_method} /></td>
                                          <td className="mono truncate" style={{ maxWidth: 300 }}>{obs.request_url}</td>
                                          <td>{obs.response_status || <span className="text-muted">--</span>}</td>
                                          <td className="text-secondary truncate" style={{ maxWidth: 150 }}>
                                            {obs.content_type || <span className="text-muted">--</span>}
                                          </td>
                                          <td><RelativeTime date={obs.timestamp} /></td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
