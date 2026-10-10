import { useEffect, useState, type FormEvent } from 'react';
import { useParams } from 'react-router-dom';
import { api, type CrawlSession } from '../services/api';

export default function CrawlerPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [sessions, setSessions] = useState<CrawlSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [maxDepth, setMaxDepth] = useState(3);
  const [maxConcurrent, setMaxConcurrent] = useState(5);
  const [maxPages, setMaxPages] = useState(500);
  const [rateLimit, setRateLimit] = useState(10);
  const [respectRobots, setRespectRobots] = useState(true);
  const [allowPrivate, setAllowPrivate] = useState(false);

  const loadSessions = () => {
    if (!projectId) return;
    api
      .listCrawlSessions(projectId)
      .then(setSessions)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadSessions, [projectId]);

  const handleStart = (e: FormEvent) => {
    e.preventDefault();
    if (!projectId) return;
    setSubmitting(true);
    setError('');
    api
      .startCrawl(projectId, {
        max_depth: maxDepth,
        max_concurrent: maxConcurrent,
        max_pages: maxPages,
        rate_limit_rps: rateLimit,
        respect_robots_txt: respectRobots,
        allow_private_networks: allowPrivate,
      })
      .then(() => {
        loadSessions();
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setSubmitting(false));
  };

  const handleCancel = (sessionId: string) => {
    if (!projectId) return;
    api.cancelCrawl(projectId, sessionId).then(loadSessions).catch(() => {});
  };

  const statusColor = (s: string) => {
    switch (s) {
      case 'completed': return 'var(--success)';
      case 'running': return 'var(--accent)';
      case 'failed': return 'var(--danger)';
      case 'cancelled': return 'var(--warning)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Crawler</h1>
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--danger)', marginBottom: '1rem' }}>{error}</div>
      )}

      <div className="grid grid-2" style={{ marginBottom: '1.5rem' }}>
        <form onSubmit={handleStart} className="card">
          <h2 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Crawl Configuration</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Max Depth</label>
              <input type="number" value={maxDepth} onChange={(e) => setMaxDepth(+e.target.value)} min={1} max={10} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Max Concurrent</label>
              <input type="number" value={maxConcurrent} onChange={(e) => setMaxConcurrent(+e.target.value)} min={1} max={20} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Max Pages</label>
              <input type="number" value={maxPages} onChange={(e) => setMaxPages(+e.target.value)} min={1} max={10000} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Rate Limit (req/s)</label>
              <input type="number" value={rateLimit} onChange={(e) => setRateLimit(+e.target.value)} min={0.1} max={100} step={0.1} />
            </div>
          </div>
          <div style={{ marginTop: '0.75rem' }}>
            <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <input type="checkbox" checked={respectRobots} onChange={(e) => setRespectRobots(e.target.checked)} style={{ width: 'auto' }} />
              Respect robots.txt
            </label>
            <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.4rem' }}>
              <input type="checkbox" checked={allowPrivate} onChange={(e) => setAllowPrivate(e.target.checked)} style={{ width: 'auto' }} />
              Allow private networks (localhost, 127.x, 10.x)
            </label>
          </div>
          <button type="submit" className="btn-primary" style={{ marginTop: '1rem', width: '100%' }} disabled={submitting}>
            {submitting ? 'Starting...' : 'Start Crawl'}
          </button>
        </form>

        <div className="card">
          <h2 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Crawl Sessions</h2>
          {loading ? (
            <div className="loading">Loading...</div>
          ) : sessions.length === 0 ? (
            <div className="empty-state" style={{ padding: '1rem' }}>No crawl sessions yet</div>
          ) : (
            <div style={{ maxHeight: 400, overflowY: 'auto' }}>
              {sessions.map((s) => (
                <div key={s.id} style={{ borderBottom: '1px solid var(--border)', padding: '0.75rem 0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: statusColor(s.status), fontWeight: 600, fontSize: '0.85rem' }}>
                      {s.status.toUpperCase()}
                    </span>
                    {s.status === 'running' && (
                      <button style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }} onClick={() => handleCancel(s.id)} type="button">
                        Cancel
                      </button>
                    )}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                    {s.pages_crawled} pages crawled, {s.pages_discovered} discovered
                  </div>
                  {s.started_at && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {new Date(s.started_at).toLocaleString()}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          <button onClick={loadSessions} style={{ marginTop: '0.5rem', width: '100%' }} type="button">
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}
