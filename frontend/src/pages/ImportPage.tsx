import { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { api, type ImportSession } from '../services/api';
import { Upload } from 'lucide-react';

export default function ImportPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [imports, setImports] = useState<ImportSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');
  const burpRef = useRef<HTMLInputElement>(null);
  const oapiRef = useRef<HTMLInputElement>(null);

  const loadImports = () => {
    if (!projectId) return;
    api
      .listImports(projectId)
      .then(setImports)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(loadImports, [projectId]);

  const handleBurp = () => {
    const file = burpRef.current?.files?.[0];
    if (!file || !projectId) return;
    setMsg('Uploading Burp file...');
    api
      .importBurp(projectId, file)
      .then(() => {
        setMsg('Burp import started');
        loadImports();
      })
      .catch((e: unknown) => setMsg(`Error: ${e instanceof Error ? e.message : String(e)}`));
  };

  const handleOpenAPI = () => {
    const file = oapiRef.current?.files?.[0];
    if (!file || !projectId) return;
    setMsg('Uploading OpenAPI spec...');
    api
      .importOpenAPI(projectId, file)
      .then(() => {
        setMsg('OpenAPI import started');
        loadImports();
      })
      .catch((e: unknown) => setMsg(`Error: ${e instanceof Error ? e.message : String(e)}`));
  };

  return (
    <div>
      <div className="page-header">
        <h1>Import</h1>
      </div>

      {msg && <div className="card" style={{ marginBottom: '1rem', fontSize: '0.85rem' }}>{msg}</div>}

      <div className="grid grid-2" style={{ marginBottom: '1.5rem' }}>
        <div className="card">
          <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
            <Upload size={16} style={{ verticalAlign: 'middle', marginRight: 4 }} />
            Burp Suite XML
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
            Import HTTP history exported from Burp Suite in XML format.
          </p>
          <input ref={burpRef} type="file" accept=".xml" onChange={handleBurp} />
        </div>
        <div className="card">
          <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
            <Upload size={16} style={{ verticalAlign: 'middle', marginRight: 4 }} />
            OpenAPI / Swagger
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
            Import an OpenAPI 2.0/3.0/3.1 specification (JSON or YAML).
          </p>
          <input ref={oapiRef} type="file" accept=".json,.yaml,.yml" onChange={handleOpenAPI} />
        </div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Import History</h2>
        {loading ? (
          <div className="loading">Loading...</div>
        ) : imports.length === 0 ? (
          <div className="empty-state" style={{ padding: '1rem' }}>No imports yet</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>File</th>
                <th>Status</th>
                <th>Items</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {imports.map((imp) => (
                <tr key={imp.id}>
                  <td><span className="badge badge-info">{imp.source_type}</span></td>
                  <td>{imp.filename}</td>
                  <td style={{ color: imp.status === 'completed' ? 'var(--success)' : imp.status === 'failed' ? 'var(--danger)' : 'var(--text-secondary)' }}>
                    {imp.status}
                  </td>
                  <td>{imp.items_imported} imported, {imp.items_skipped} skipped</td>
                  <td style={{ fontSize: '0.8rem' }}>{imp.started_at ? new Date(imp.started_at).toLocaleString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <button onClick={loadImports} style={{ marginTop: '0.5rem' }} type="button">Refresh</button>
      </div>
    </div>
  );
}
