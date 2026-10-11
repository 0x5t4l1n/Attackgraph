import { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  type Node,
  type Edge,
  type NodeTypes,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { GitGraph, RefreshCw } from 'lucide-react';
import { api, type GraphNode, type GraphData } from '../services/api';
import { PageHeader, StatCard, EmptyState, LoadingState, ErrorState, MethodBadge, useToast, useAsync } from '../components/ui';

const NODE_COLORS: Record<string, string> = {
  page: 'var(--accent)',
  endpoint: 'var(--success)',
  form: 'var(--warning)',
  parameter: 'var(--text-muted)',
  redirect: 'var(--info)',
  resource: 'var(--text-secondary)',
};

function CustomNode({ data }: { data: { label: string; method?: string; type: string; observed: boolean; confidence: number } }) {
  const color = NODE_COLORS[data.type] || 'var(--text-muted)';
  return (
    <div style={{
      background: 'var(--bg-raised)',
      border: `1.5px ${data.observed ? 'solid' : 'dashed'} ${color}`,
      borderRadius: 'var(--radius)',
      padding: '6px 10px',
      minWidth: 120,
      fontSize: 11,
      color: 'var(--text-primary)',
    }}>
      <Handle type="target" position={Position.Top} style={{ background: color, width: 6, height: 6 }} />
      {data.method && <span style={{ marginRight: 6, fontSize: 10, color, fontWeight: 700 }}>{data.method}</span>}
      <span style={{ fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}>{data.label}</span>
      <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>{data.type} · {Math.round(data.confidence * 100)}%</div>
      <Handle type="source" position={Position.Bottom} style={{ background: color, width: 6, height: 6 }} />
    </div>
  );
}

const nodeTypes: NodeTypes = { custom: CustomNode };

const TYPE_ORDER = ['page', 'endpoint', 'form', 'parameter', 'redirect', 'resource'];

function buildLayout(rawNodes: GraphNode[]): Node[] {
  const grouped: Record<string, GraphNode[]> = {};
  for (const n of rawNodes) {
    (grouped[n.type] ??= []).push(n);
  }
  const result: Node[] = [];
  let colIdx = 0;
  for (const type of [...TYPE_ORDER, ...Object.keys(grouped).filter(t => !TYPE_ORDER.includes(t))]) {
    const group = grouped[type];
    if (!group) continue;
    group.forEach((n, rowIdx) => {
      result.push({
        id: n.id,
        type: 'custom',
        position: { x: colIdx * 220, y: rowIdx * 90 },
        data: { label: n.label, method: n.method, type: n.type, observed: n.observed, confidence: n.confidence },
      });
    });
    colIdx++;
  }
  return result;
}

function buildEdges(graph: GraphData): Edge[] {
  return graph.edges.map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    style: { stroke: e.observed ? 'var(--border-strong)' : 'var(--border)', strokeDasharray: e.observed ? undefined : '4 2' },
    labelStyle: { fill: 'var(--text-muted)', fontSize: 10 },
  }));
}

export default function GraphPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { toast } = useToast();
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [building, setBuilding] = useState(false);
  const [typeFilter, setTypeFilter] = useState('all');

  const { data: graph, loading, error, reload } = useAsync(
    () => api.getGraph(projectId!),
    [projectId],
  );

  const handleBuild = useCallback(async () => {
    setBuilding(true);
    try {
      const r = await api.buildGraph(projectId!);
      toast('success', `Graph built: ${r.nodes} nodes, ${r.edges} edges`);
      reload();
    } catch (e: unknown) {
      toast('error', e instanceof Error ? e.message : 'Build failed');
    } finally {
      setBuilding(false);
    }
  }, [projectId, toast, reload]);

  const onNodeClick = useCallback((_: unknown, node: Node) => {
    if (!graph) return;
    const raw = graph.nodes.find(n => n.id === node.id) ?? null;
    setSelectedNode(raw);
  }, [graph]);

  if (loading) return <LoadingState message="Loading graph..." />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const stats = graph?.statistics ?? {};
  const filteredNodes = (graph?.nodes ?? []).filter(n => typeFilter === 'all' || n.type === typeFilter);
  const nodeTypes2 = [...new Set((graph?.nodes ?? []).map(n => n.type))];

  const flowNodes = buildLayout(filteredNodes);
  const flowEdges = buildEdges({ ...graph!, nodes: filteredNodes });

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Application Graph"
        icon={<GitGraph size={20} />}
        actions={
          <div className="flex gap-2 items-center">
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
              <option value="all">All Types</option>
              {nodeTypes2.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <button className="btn-primary flex gap-1 items-center" onClick={handleBuild} disabled={building}>
              <RefreshCw size={14} className={building ? 'spinner' : ''} />
              {building ? 'Building…' : 'Rebuild Graph'}
            </button>
          </div>
        }
      />

      <div className="grid grid-4 gap-3">
        <StatCard value={filteredNodes.length} label="Nodes" />
        <StatCard value={(graph?.edges ?? []).length} label="Edges" />
        <StatCard value={filteredNodes.filter(n => n.observed).length} label="Observed" />
        <StatCard value={filteredNodes.filter(n => !n.observed).length} label="Inferred" />
      </div>

      {filteredNodes.length === 0 ? (
        <EmptyState
          icon={<GitGraph size={32} />}
          title="No graph data"
          description="Run a crawl then click Rebuild Graph to generate the application graph."
          action={<button className="btn-primary" onClick={handleBuild}>Build Graph</button>}
        />
      ) : (
        <div style={{ height: 'calc(100vh - 320px)', minHeight: 400, background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            fitView
            style={{ background: 'var(--bg-surface)' }}
          >
            <MiniMap style={{ background: 'var(--bg-raised)' }} nodeColor={(n) => NODE_COLORS[(n.data as { type: string }).type] || 'var(--border)'} />
            <Controls style={{ background: 'var(--bg-raised)', border: '1px solid var(--border)' }} />
            <Background color="var(--border)" gap={20} />
          </ReactFlow>
        </div>
      )}

      {selectedNode && (
        <div className="detail-panel">
          <div className="detail-panel-header">
            <span className="text-sm text-muted">Selected Node</span>
            <button className="btn-ghost btn-icon btn-sm" onClick={() => setSelectedNode(null)}>✕</button>
          </div>
          <div className="detail-section">
            <div className="detail-label">Label</div>
            <div className="detail-value mono">{selectedNode.label}</div>
          </div>
          <div className="detail-section">
            <div className="detail-label">Type</div>
            <div className="detail-value">{selectedNode.type}</div>
          </div>
          {selectedNode.method && (
            <div className="detail-section">
              <div className="detail-label">Method</div>
              <div className="detail-value"><MethodBadge method={selectedNode.method} /></div>
            </div>
          )}
          {selectedNode.url && (
            <div className="detail-section">
              <div className="detail-label">URL</div>
              <div className="detail-value mono text-xs">{selectedNode.url}</div>
            </div>
          )}
          <div className="detail-section">
            <div className="detail-label">Evidence</div>
            <div className="detail-value">{selectedNode.evidence_source} · {Math.round(selectedNode.confidence * 100)}% confidence</div>
          </div>
          <div className="detail-section">
            <div className="detail-label">Observed</div>
            <div className="detail-value">{selectedNode.observed ? 'Yes' : 'No (inferred)'}</div>
          </div>
        </div>
      )}

      {stats && Object.keys(stats).length > 0 && (
        <div className="card">
          <div className="card-header"><span className="card-header-title">Statistics</span></div>
          <div className="card-body">
            <div className="grid grid-4 gap-2">
              {Object.entries(stats).map(([k, v]) => (
                <div key={k} className="detail-section">
                  <div className="detail-label">{k.replace(/_/g, ' ')}</div>
                  <div className="detail-value">{String(v)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
