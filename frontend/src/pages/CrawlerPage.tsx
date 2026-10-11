import { useState, useEffect, useCallback, useRef, type FormEvent } from 'react';
import { useParams } from 'react-router-dom';
import { Radar, Play, XCircle, RefreshCw, AlertTriangle } from 'lucide-react';
import { api, type CrawlSession } from '../services/api';
import {
  PageHeader,
  StatusBadge,
  RelativeTime,
  EmptyState,
  LoadingState,
  ErrorState,
  useToast,
} from '../components/ui';

export default function CrawlerPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { toast } = useToast();

  const [sessions, setSessions] = useState<CrawlSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [maxDepth, setMaxDepth] = useState(3);
  const [maxConcurrent, setMaxConcurrent] = useState(5);
  const [maxPages, setMaxPages] = useState(500);
  const [rateLimit, setRateLimit] = useState(10);
  const [respectRobots, setRespectRobots] = useState(true);
  const [allowPrivate, setAllowPrivate] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadSessions = useCallback(() => {
    if (!projectId) return;
    api
      .listCrawlSessions(projectId)
      .then((data) => {
        setSessions(data);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  // Initial load
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Auto-poll running sessions every 3 seconds
  useEffect(() => {
    const hasRunning = sessions.some((s) => s.status === 'running' || s.status === 'pending');
    if (hasRunning) {
      pollRef.current = setInterval(loadSessions, 3000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [sessions, loadSessions]);

  const handleStart = (e: FormEvent) => {
    e.preventDefault();
    if (!projectId) return;
    setSubmitting(true);
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
        toast('success', 'Crawl started successfully');
        loadSessions();
      })
      .catch((e: Error) => {
        toast('error', `Failed to start crawl: ${e.message}`);
      })
      .finally(() => setSubmitting(false));
  };

  const handleCancel = (sessionId: string) => {
    if (!projectId) return;
    api
      .cancelCrawl(projectId, sessionId)
      .then(() => {
        toast('info', 'Crawl session cancelled');
        loadSessions();
      })
      .catch((e: Error) => {
        toast('error', `Failed to cancel: ${e.message}`);
      });
  };

  return (
    <div>
      <PageHeader
        title="Crawler"
        subtitle="Configure and launch web crawl sessions"
        icon={<Radar size={20} />}
        actions={
          <button className="btn-ghost btn-sm" onClick={loadSessions}>
            <RefreshCw size={14} />
            Refresh
          </button>
        }
      />

      <div className="grid grid-2">
        {/* Config Form */}
        <form onSubmit={handleStart} className="card">
          <div className="card-header">
            <span className="card-header-title">Crawl Configuration</span>
          </div>
          <div className="card-body flex flex-col gap-4">
            <div className="grid grid-2">
              <div className="input-group">
                <label className="input-label">Max Depth</label>
                <input
                  type="number"
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(+e.target.value)}
                  min={1}
                  max={10}
                />
                <span className="input-hint">How deep to follow links</span>
              </div>
              <div className="input-group">
                <label className="input-label">Max Concurrent</label>
                <input
                  type="number"
                  value={maxConcurrent}
                  onChange={(e) => setMaxConcurrent(+e.target.value)}
                  min={1}
                  max={20}
                />
                <span className="input-hint">Parallel requests</span>
              </div>
              <div className="input-group">
                <label className="input-label">Max Pages</label>
                <input
                  type="number"
                  value={maxPages}
                  onChange={(e) => setMaxPages(+e.target.value)}
                  min={1}
                  max={10000}
                />
                <span className="input-hint">Total page limit</span>
              </div>
              <div className="input-group">
                <label className="input-label">Rate Limit (req/s)</label>
                <input
                  type="number"
                  value={rateLimit}
                  onChange={(e) => setRateLimit(+e.target.value)}
                  min={0.1}
                  max={100}
                  step={0.1}
                />
                <span className="input-hint">Requests per second</span>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-sm text-secondary">
                <input
                  type="checkbox"
                  checked={respectRobots}
                  onChange={(e) => setRespectRobots(e.target.checked)}
                />
                Respect robots.txt
              </label>
              <label className="flex items-center gap-2 text-sm text-secondary">
                <input
                  type="checkbox"
                  checked={allowPrivate}
                  onChange={(e) => setAllowPrivate(e.target.checked)}
                />
                Allow private networks (localhost, 127.x, 10.x)
              </label>
            </div>

            <button type="submit" className="btn-primary btn-lg w-full" disabled={submitting}>
              <Play size={16} />
              {submitting ? 'Starting...' : 'Start Crawl'}
            </button>
          </div>
        </form>

        {/* Sessions List */}
        <div className="card">
          <div className="card-header">
            <span className="card-header-title">Crawl Sessions</span>
            {sessions.length > 0 && (
              <span className="badge badge-neutral">{sessions.length}</span>
            )}
          </div>
          <div className="card-body p-0">
            {loading ? (
              <LoadingState message="Loading sessions..." />
            ) : error ? (
              <ErrorState message={error} onRetry={loadSessions} />
            ) : sessions.length === 0 ? (
              <EmptyState
                icon={<Radar size={32} />}
                title="No crawl sessions"
                description="Configure and start a crawl to discover endpoints on the target application."
              />
            ) : (
              <div className="overflow-auto" style={{ maxHeight: 480 }}>
                {sessions.map((session) => (
                  <div key={session.id} className="flex flex-col gap-2 p-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={session.status} />
                        {session.status === 'running' && (
                          <span className="status-dot status-dot-info status-dot-pulse" />
                        )}
                      </div>
                      {(session.status === 'running' || session.status === 'pending') && (
                        <button
                          className="btn-danger btn-sm"
                          onClick={() => handleCancel(session.id)}
                          type="button"
                        >
                          <XCircle size={12} />
                          Cancel
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-primary font-medium">
                        {session.pages_crawled}
                        <span className="text-muted"> / {session.pages_discovered} pages</span>
                      </span>
                      {session.pages_discovered > 0 && (
                        <div className="progress-bar flex-1" style={{ maxWidth: 120 }}>
                          <div
                            className="progress-bar-fill"
                            style={{
                              width: `${Math.min(100, (session.pages_crawled / session.pages_discovered) * 100)}%`,
                            }}
                          />
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <RelativeTime date={session.started_at} />
                      {session.errors.length > 0 && (
                        <span className="flex items-center gap-1 text-warning">
                          <AlertTriangle size={12} />
                          {session.errors.length} error{session.errors.length !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
