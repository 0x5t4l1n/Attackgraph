export interface Project {
  id: string;
  name: string;
  description: string;
  target_url: string;
  allowed_hosts: string[];
  allowed_schemes: string[];
  exclude_paths: string[];
  created_at: string;
  updated_at: string;
  status: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  target_url: string;
  allowed_hosts?: string[];
  allowed_schemes?: string[];
  exclude_paths?: string[];
}

export interface CrawlConfig {
  max_depth?: number;
  max_concurrent?: number;
  max_pages?: number;
  request_timeout?: number;
  rate_limit_rps?: number;
  respect_robots_txt?: boolean;
  auth_cookies?: Record<string, string> | null;
  auth_headers?: Record<string, string> | null;
}

export interface CrawlSession {
  id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  pages_discovered: number;
  pages_crawled: number;
  errors: string[];
  config: Record<string, unknown> | null;
}

export interface ImportSession {
  id: string;
  source_type: string;
  filename: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  items_imported: number;
  items_skipped: number;
  errors: string[];
}

export interface Endpoint {
  id: string;
  url: string;
  normalized_url: string;
  method: string;
  status_code: number | null;
  content_type: string | null;
  discovery_source: string;
  parent_url: string | null;
  first_seen: string;
}

export interface ObservationSummary {
  id: string;
  source_type: string;
  request_method: string;
  request_url: string;
  response_status: number | null;
  content_type: string | null;
  timestamp: string;
  redacted: boolean;
}

export interface EndpointDetail extends Endpoint {
  last_seen: string;
  observations: ObservationSummary[];
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  url?: string | null;
  method?: string | null;
  properties: Record<string, unknown>;
  evidence_source: string;
  confidence: number;
  observed: boolean;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label: string;
  properties: Record<string, unknown>;
  evidence_source: string;
  confidence: number;
  observed: boolean;
}

export interface GraphData {
  project_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics: Record<string, unknown>;
}

export interface Finding {
  id: string;
  title: string;
  description: string;
  affected_endpoints: string[];
  evidence_refs: string[];
  severity: string;
  confidence: number;
  validation_status: string;
  detection_rule: string;
  reasoning: string;
  assumptions: string[];
  reproduction_steps: string;
  remediation: string;
  created_at: string;
  updated_at?: string;
}

export interface AttackPath {
  id: string;
  entry_point: string;
  target_operation: string;
  intermediate_steps: Array<{ node_id: string; label: string; type: string }>;
  preconditions: string[];
  observations: string[];
  unverified_assumptions: string[];
  potential_impact: string;
  confidence: number;
  priority_score: number;
  recommended_steps: string[];
  created_at: string;
}

export interface TestPlan {
  id: string;
  attack_path_id: string | null;
  hypothesis: string;
  evidence: string[];
  required_accounts: string[];
  preconditions: string[];
  test_procedure: string;
  expected_secure_behavior: string;
  potential_insecure_outcomes: string[];
  cleanup_steps: string[];
  evidence_to_capture: string[];
  limitations: string[];
  status: string;
  created_at: string;
}

const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  listProjects: () => request<Project[]>('/projects'),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (data: ProjectCreate) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  deleteProject: (id: string) =>
    request<{ detail: string }>(`/projects/${id}`, { method: 'DELETE' }),

  startCrawl: (projectId: string, config: CrawlConfig) =>
    request<{ session_id: string; status: string }>(`/projects/${projectId}/crawl`, {
      method: 'POST',
      body: JSON.stringify(config),
    }),
  listCrawlSessions: (projectId: string) =>
    request<CrawlSession[]>(`/projects/${projectId}/crawl/sessions`),
  getCrawlSession: (projectId: string, sessionId: string) =>
    request<CrawlSession>(`/projects/${projectId}/crawl/sessions/${sessionId}`),
  cancelCrawl: (projectId: string, sessionId: string) =>
    request<{ detail: string }>(`/projects/${projectId}/crawl/sessions/${sessionId}/cancel`, {
      method: 'POST',
    }),

  importBurp: async (projectId: string, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${BASE}/projects/${projectId}/import/burp`, {
      method: 'POST',
      body: fd,
    });
    return res.json() as Promise<{ import_id: string; status: string }>;
  },
  importOpenAPI: async (projectId: string, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${BASE}/projects/${projectId}/import/openapi`, {
      method: 'POST',
      body: fd,
    });
    return res.json() as Promise<{ import_id: string; status: string }>;
  },
  listImports: (projectId: string) =>
    request<ImportSession[]>(`/projects/${projectId}/imports`),

  listEndpoints: (projectId: string) =>
    request<Endpoint[]>(`/projects/${projectId}/endpoints`),
  getEndpoint: (projectId: string, endpointId: string) =>
    request<EndpointDetail>(`/projects/${projectId}/endpoints/${endpointId}`),

  getGraph: (projectId: string) => request<GraphData>(`/projects/${projectId}/graph`),
  buildGraph: (projectId: string) =>
    request<{ detail: string; nodes: number; edges: number }>(
      `/projects/${projectId}/graph/build`,
      { method: 'POST' },
    ),

  runAnalysis: (projectId: string) =>
    request<{ detail: string; findings: number; attack_paths: number }>(
      `/projects/${projectId}/analyze`,
      { method: 'POST' },
    ),
  listFindings: (projectId: string) =>
    request<Finding[]>(`/projects/${projectId}/findings`),
  getFinding: (projectId: string, findingId: string) =>
    request<Finding>(`/projects/${projectId}/findings/${findingId}`),
  updateFinding: (
    projectId: string,
    findingId: string,
    data: { validation_status?: string; severity?: string },
  ) =>
    request<{ detail: string }>(`/projects/${projectId}/findings/${findingId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  listAttackPaths: (projectId: string) =>
    request<AttackPath[]>(`/projects/${projectId}/attack-paths`),
  getAttackPath: (projectId: string, pathId: string) =>
    request<AttackPath>(`/projects/${projectId}/attack-paths/${pathId}`),

  listTestPlans: (projectId: string) =>
    request<TestPlan[]>(`/projects/${projectId}/test-plans`),
  getTestPlan: (projectId: string, planId: string) =>
    request<TestPlan>(`/projects/${projectId}/test-plans/${planId}`),
  updateTestPlan: (projectId: string, planId: string, data: { status?: string }) =>
    request<{ detail: string }>(`/projects/${projectId}/test-plans/${planId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  getReport: async (projectId: string, format: string): Promise<string> => {
    const res = await fetch(`${BASE}/projects/${projectId}/reports/${format}`);
    if (format === 'json') return JSON.stringify(await res.json(), null, 2);
    return res.text();
  },

  aiStatus: () => request<{ enabled: boolean; model: string | null }>('/ai/status'),
  aiSummarize: (projectId: string) =>
    request<{ summary: string }>(`/projects/${projectId}/ai/summarize`, { method: 'POST' }),

  getSettings: () => request<Record<string, unknown>>('/settings'),
};
