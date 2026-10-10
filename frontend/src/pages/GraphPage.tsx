import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { api, type GraphData, type GraphNode as GN } from '../services/api';

const NODE_COLORS: Record<string, string> = {
  endpoint: '#58a6ff',
  host: '#3fb950',
  parameter: '#d29922',
  auth_mechanism: '#f85149',
  role: '#d2a8ff',
  workflow: '#79c0ff',
  sensitive_op: '#ff7b72',
  data_resource: '#a5d6ff',
  page: '#7ee787',
  operation: '#ffa657',
};

function layoutNodes(nodes: GN[]): Node[] {
  const byType: Record<string, GN[]> = {};
  for (const n of nodes) {
    const t = n.type || 'other';
    if (!byType[t]) byType[t] = [];
    byType[t].push(n);
  }

  const result: Node[] = [];
  let colX = 0;

  for (const [type, group] of Object.entries(byType)) {
    for (let i = 0; i < group.length; i++) {
      const n = group[i];
      result.push({
        id: n.id,
        position: { x: colX, y: i * 80 },
        data: {
          label: n.label.length > 40 ? n.label.slice(0, 37) + '...' : n.label,
        },
        style: {
          background: NODE_COLORS[type] || '#8b949e',
          color: '#0d1117',
          border: n.observed ? '2px solid #e6edf3' : '2px dashed #6e7681',
          borderRadius: 6,
          padding: '6px 10px',
          fontSize: 11,
          fontWeight: 600,
          maxWidth: 200,
        },
      });
    }
    colX += 280;
  }
  return result;
}

export default function GraphPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState('');
  const [filterType, setFilterType] = useState('');
  const [selectedNode, setSelectedNode] = useState<GN | null>(null);

  const loadGraph = useCallback(() => {
    if (!projectId) return;
    setLoading(true);
    api
      .getGraph(projectId)
      .then(setGraphData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(loadGraph, [loadGraph]);

  const handleBuild = () => {
    if (!projectId) return;
    setBuilding(true);
    api
      .buildGraph(projectId)
      .then(() => loadGraph())
      .catch((e: Error) => setError(e.message))
      .finally(() => setBuilding(false));
  };

  if (loading) return <div className="loading">Loading graph...</div>;
  if (error) return <div className="card" style={{ borderColor: 'var(--danger)' }}>{error}</div>;

  const allNodes = graphData?.nodes || [];
  const filteredNodes = filterType ? allNodes.filter((n) => n.type === filterType) : allNodes;
  const filteredIds = new Set(filteredNodes.map((n) => n.id));
  const rfNodes = layoutNodes(filteredNodes);
  const rfEdges: Edge[] = (graphData?.edges || [])
    .filter((e) => filteredIds.has(e.source) && filteredIds.has(e.target))
    .map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label || undefined,
      style: {
        stroke: e.observed ? '#58a6ff' : '#6e7681',
        strokeDasharray: e.observed ? undefined : '5 5',
      },
      animated: e.type === 'attack_path',
    }));

  const nodeTypes = [...new Set(allNodes.map((n) => n.type))].sort();
  const stats = graphData?.statistics || {};

  const handleNodeClick = (_: unknown, node: Node) => {
    const gn = allNodes.find((n) => n.id === node.id);
    if (gn) setSelectedNode(gn);
  };

  return (
    <div>
      <div className="page-header">
        <h1>Application Graph</h1>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)} style={{ width: 'auto' }}>
            <option value="">All Types</option>
            {nodeTypes.map((t) => (
              <option key={t} value={t}>{t} ({allNodes.filter((n) => n.type === t).length})</option>
            ))}
          </select>
          <button onClick={handleBuild} disabled={building} type="button">
            {building ? 'Building...' : 'Rebuild Graph'}
          </button>
        </div>
      </div>

      <div className="grid grid-4" style={{ marginBottom: '1rem' }}>
        <div className="card" style={{ textAlign: 'center', padding: '0.75rem' }}>
          <div className="stat-value" style={{ fontSize: '1.5rem' }}>{stats.total_nodes as number ?? 0}</div>
          <div className="stat-label">Nodes</div>
        </div>
        <div className="card" style={{ textAlign: 'center', padding: '0.75rem' }}>
          <div className="stat-value" style={{ fontSize: '1.5rem' }}>{stats.total_edges as number ?? 0}</div>
          <div className="stat-label">Edges</div>
        </div>
        <div className="card" style={{ textAlign: 'center', padding: '0.75rem' }}>
          <div className="stat-value" style={{ fontSize: '1.5rem' }}>{stats.observed_nodes as number ?? 0}</div>
          <div className="stat-label">Observed</div>
        </div>
        <div className="card" style={{ textAlign: 'center', padding: '0.75rem' }}>
          <div className="stat-value" style={{ fontSize: '1.5rem' }}>{stats.inferred_nodes as number ?? 0}</div>
          <div className="stat-label">Inferred</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem' }}>
        <div style={{ height: 500, flex: 1, border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
          {rfNodes.length === 0 ? (
            <div className="empty-state">No graph data. Crawl or import data, then build the graph.</div>
          ) : (
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              onNodeClick={handleNodeClick}
              fitView
              colorMode="dark"
            >
              <Background color="#30363d" gap={20} />
              <Controls />
              <MiniMap
                nodeColor={(n) => (n.style?.background as string) || '#8b949e'}
                maskColor="rgba(13,17,23,0.7)"
              />
            </ReactFlow>
          )}
        </div>

        {selectedNode && (
          <div className="card" style={{ width: 320, flexShrink: 0, maxHeight: 500, overflowY: 'auto' }}>
            <h2 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Node Details</h2>
            <div style={{ fontSize: '0.85rem' }}>
              <div style={{ marginBottom: '0.3rem' }}><strong>Label:</strong> {selectedNode.label}</div>
              <div style={{ marginBottom: '0.3rem' }}><strong>Type:</strong> <span className="badge badge-info">{selectedNode.type}</span></div>
              {selectedNode.url && <div style={{ marginBottom: '0.3rem', fontFamily: 'monospace', wordBreak: 'break-all', fontSize: '0.8rem' }}>{selectedNode.url}</div>}
              <div style={{ marginBottom: '0.3rem' }}><strong>Source:</strong> {selectedNode.evidence_source}</div>
              <div style={{ marginBottom: '0.3rem' }}><strong>Confidence:</strong> {(selectedNode.confidence * 100).toFixed(0)}%</div>
              <div style={{ marginBottom: '0.3rem' }}><strong>Observed:</strong> {selectedNode.observed ? 'Yes' : 'No (inferred)'}</div>
              {Object.keys(selectedNode.properties).length > 0 && (
                <pre style={{ background: 'var(--bg-primary)', padding: '0.5rem', borderRadius: 4, fontSize: '0.75rem', overflow: 'auto', marginTop: '0.5rem' }}>
                  {JSON.stringify(selectedNode.properties, null, 2)}
                </pre>
              )}
            </div>
            <button onClick={() => setSelectedNode(null)} style={{ marginTop: '0.75rem', width: '100%' }} type="button">Close</button>
          </div>
        )}
      </div>
    </div>
  );
}
