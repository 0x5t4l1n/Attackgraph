import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type Project, type Endpoint, type Finding, type AttackPath } from '../services/api';
import { Globe, AlertTriangle, Route, Play, Cpu, Network } from 'lucide-react';

export default function ProjectOverview() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [attackPaths, setAttackPaths] = useState<AttackPath[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    Promise.all([
      api.getProject(projectId),
      api.listEndpoints(projectId).catch(() => []),
      api.listFindings(projectId).catch(() => []),
      api.listAttackPaths(projectId).catch(() => []),
    ])
      .then(([p, ep, f, ap]) => {
        setProject(p);
        setEndpoints(ep);
        setFindings(f);
        setAttackPaths(ap);
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  const doAction = (label: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    setActionMsg(`Running ${label}...`);
    fn()
      .then(() => setActionMsg(`${label} complete`))
      .catch((e: Error) => setActionMsg(`Error: ${e.message}`))
      .finally(() => setBusy(false));
  };

  if (loading) return <div className="loading">Loading project...</div>;
  if (!project) return <div className="empty-state">Project not found</div>;

  const sevCounts: Record<string, number> = {};
  for (const f of findings) {
    sevCounts[f.severity] = (sevCounts[f.severity] || 0) + 1;
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{project.name}</h1>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{project.target_url}</div>
        </div>
      </div>

      <div className="grid grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-value">{endpoints.length}</div>
          <div className="stat-label">Endpoints</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-value">{findings.length}</div>
          <div className="stat-label">Findings</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-value">{attackPaths.length}</div>
          <div className="stat-label">Attack Paths</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-value">{project.allowed_hosts?.length || 0}</div>
          <div className="stat-label">Hosts in Scope</div>
        </div>
      </div>

      <div className="grid grid-3" style={{ marginBottom: '1.5rem' }}>
        <button
          className="btn-primary"
          disabled={busy}
          onClick={() =>
            doAction('Crawl', () => api.startCrawl(projectId!, { max_depth: 3, max_pages: 200 }))
          }
          type="button"
        >
          <Globe size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} /> Start Quick Crawl
        </button>
        <button
          disabled={busy}
          onClick={() => doAction('Graph Build', () => api.buildGraph(projectId!))}
          type="button"
        >
          <Network size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} /> Build Graph
        </button>
        <button
          disabled={busy}
          onClick={() => doAction('Analysis', () => api.runAnalysis(projectId!))}
          type="button"
        >
          <Cpu size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} /> Run Analysis
        </button>
      </div>

      {actionMsg && (
        <div className="card" style={{ marginBottom: '1rem', fontSize: '0.85rem' }}>
          {actionMsg}
        </div>
      )}

      {findings.length > 0 && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Finding Severity Distribution</h2>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {Object.entries(sevCounts).map(([sev, count]) => (
              <span key={sev} className={`badge badge-${sev}`}>
                {sev}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Quick Navigation</h2>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <Link to={`/projects/${projectId}/crawl`}>
            <Play size={14} style={{ verticalAlign: 'middle' }} /> Crawler
          </Link>
          <Link to={`/projects/${projectId}/endpoints`}>
            <Network size={14} style={{ verticalAlign: 'middle' }} /> Endpoints
          </Link>
          <Link to={`/projects/${projectId}/findings`}>
            <AlertTriangle size={14} style={{ verticalAlign: 'middle' }} /> Findings
          </Link>
          <Link to={`/projects/${projectId}/attack-paths`}>
            <Route size={14} style={{ verticalAlign: 'middle' }} /> Attack Paths
          </Link>
        </div>
      </div>
    </div>
  );
}
