import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  api,
  type Project,
  type Endpoint,
  type Finding,
  type AttackPath,
  type CrawlSession,
} from '../services/api';
import {
  Globe,
  AlertTriangle,
  Route,
  Play,
  Cpu,
  Network,
  ArrowRight,
} from 'lucide-react';
import {
  PageHeader,
  StatCard,
  SeverityBadge,
  StatusBadge,
  LoadingState,
  ErrorState,
  RelativeTime,
  useAsync,
  useToast,
} from '../components/ui';

interface OverviewData {
  project: Project;
  endpoints: Endpoint[];
  findings: Finding[];
  attackPaths: AttackPath[];
  crawlSessions: CrawlSession[];
}

export default function ProjectOverview() {
  const { projectId } = useParams<{ projectId: string }>();
  const { toast } = useToast();
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const { data, loading, error, reload } = useAsync<OverviewData>(
    async () => {
      if (!projectId) throw new Error('No project ID');
      const [project, endpoints, findings, attackPaths, crawlSessions] =
        await Promise.all([
          api.getProject(projectId),
          api.listEndpoints(projectId).catch(() => [] as Endpoint[]),
          api.listFindings(projectId).catch(() => [] as Finding[]),
          api.listAttackPaths(projectId).catch(() => [] as AttackPath[]),
          api.listCrawlSessions(projectId).catch(() => [] as CrawlSession[]),
        ]);
      return { project, endpoints, findings, attackPaths, crawlSessions };
    },
    [projectId],
  );

  const doAction = async (label: string, fn: () => Promise<unknown>) => {
    setBusyAction(label);
    try {
      await fn();
      toast('success', `${label} completed successfully`);
      reload();
    } catch (e: unknown) {
      toast('error', e instanceof Error ? e.message : `${label} failed`);
    } finally {
      setBusyAction(null);
    }
  };

  if (loading) return <LoadingState message="Loading project..." />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <ErrorState message="Project not found" />;

  const { project, endpoints, findings, attackPaths, crawlSessions } = data;

  const sevCounts: Record<string, number> = {};
  for (const f of findings) {
    sevCounts[f.severity] = (sevCounts[f.severity] || 0) + 1;
  }
  const sevOrder = ['critical', 'high', 'medium', 'low', 'info'];
  const sortedSeverities = Object.entries(sevCounts).sort(
    (a, b) => sevOrder.indexOf(a[0]) - sevOrder.indexOf(b[0]),
  );

  const recentSessions = [...crawlSessions]
    .sort(
      (a, b) =>
        new Date(b.started_at ?? 0).getTime() -
        new Date(a.started_at ?? 0).getTime(),
    )
    .slice(0, 3);

  return (
    <div>
      <PageHeader
        title={project.name}
        subtitle={project.target_url}
        icon={<Globe size={20} />}
      />

      {/* Stats */}
      <div className="grid grid-4 mb-6">
        <StatCard
          value={endpoints.length}
          label="Endpoints"
          color="var(--accent)"
        />
        <StatCard
          value={findings.length}
          label="Findings"
          color={findings.length > 0 ? 'var(--warning)' : undefined}
        />
        <StatCard
          value={attackPaths.length}
          label="Attack Paths"
          color={attackPaths.length > 0 ? 'var(--danger)' : undefined}
        />
        <StatCard
          value={project.allowed_hosts?.length ?? 0}
          label="Hosts in Scope"
        />
      </div>

      {/* Severity Distribution */}
      {findings.length > 0 && (
        <div className="card mb-4">
          <div className="card-header">
            <span className="card-header-title">Finding Severity Distribution</span>
          </div>
          <div className="card-body flex flex-wrap gap-3">
            {sortedSeverities.map(([sev, count]) => (
              <div key={sev} className="flex items-center gap-2">
                <SeverityBadge severity={sev} />
                <span className="text-sm font-semibold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="card mb-4">
        <div className="card-header">
          <span className="card-header-title">Actions</span>
        </div>
        <div className="card-body flex flex-wrap gap-2">
          <Link to={`/projects/${projectId}/crawl`}>
            <button className="btn-primary" type="button">
              <Play size={14} />
              Start Crawl
            </button>
          </Link>
          <button
            className="btn-ghost"
            disabled={busyAction !== null}
            onClick={() => doAction('Graph Build', () => api.buildGraph(projectId!))}
            type="button"
          >
            <Network size={14} />
            {busyAction === 'Graph Build' ? 'Building...' : 'Build Graph'}
          </button>
          <button
            className="btn-ghost"
            disabled={busyAction !== null}
            onClick={() => doAction('Analysis', () => api.runAnalysis(projectId!))}
            type="button"
          >
            <Cpu size={14} />
            {busyAction === 'Analysis' ? 'Analyzing...' : 'Run Analysis'}
          </button>
        </div>
      </div>

      {/* Recent Crawl Sessions */}
      {recentSessions.length > 0 && (
        <div className="card mb-4">
          <div className="card-header">
            <span className="card-header-title">Recent Crawl Sessions</span>
            <Link to={`/projects/${projectId}/crawl`} className="text-xs">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Pages</th>
                <th>Started</th>
                <th>Completed</th>
              </tr>
            </thead>
            <tbody>
              {recentSessions.map((s) => (
                <tr key={s.id}>
                  <td><StatusBadge status={s.status} /></td>
                  <td className="text-sm">{s.pages_crawled} / {s.pages_discovered}</td>
                  <td><RelativeTime date={s.started_at} /></td>
                  <td><RelativeTime date={s.completed_at} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Quick Navigation */}
      <div className="card">
        <div className="card-header">
          <span className="card-header-title">Quick Navigation</span>
        </div>
        <div className="card-body flex flex-wrap gap-4">
          <Link to={`/projects/${projectId}/crawl`} className="flex items-center gap-2 text-sm">
            <Play size={14} /> Crawler
          </Link>
          <Link to={`/projects/${projectId}/endpoints`} className="flex items-center gap-2 text-sm">
            <Network size={14} /> Endpoints
          </Link>
          <Link to={`/projects/${projectId}/findings`} className="flex items-center gap-2 text-sm">
            <AlertTriangle size={14} /> Findings
          </Link>
          <Link to={`/projects/${projectId}/attack-paths`} className="flex items-center gap-2 text-sm">
            <Route size={14} /> Attack Paths
          </Link>
        </div>
      </div>
    </div>
  );
}
