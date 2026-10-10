import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { FileText, Download } from 'lucide-react';

export default function ReportsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [format, setFormat] = useState('markdown');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      const result = await api.getReport(projectId, format);
      setContent(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const download = () => {
    const ext = format === 'json' ? 'json' : format === 'html' ? 'html' : 'md';
    const mime = format === 'json' ? 'application/json' : format === 'html' ? 'text/html' : 'text/markdown';
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attackgraph-report.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="page-header">
        <h1><FileText size={20} style={{ verticalAlign: 'middle', marginRight: 8 }} />Reports</h1>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <select value={format} onChange={e => setFormat(e.target.value)} style={{ width: 'auto' }}>
            <option value="markdown">Markdown</option>
            <option value="json">JSON</option>
            <option value="html">HTML</option>
          </select>
          <button className="btn-primary" onClick={generate} disabled={loading}>
            {loading ? 'Generating...' : 'Generate Report'}
          </button>
          {content && (
            <button onClick={download}>
              <Download size={14} style={{ marginRight: 4 }} /> Download
            </button>
          )}
        </div>
      </div>

      {error && <div className="card" style={{ color: 'var(--danger)', marginBottom: '1rem' }}>{error}</div>}

      {content && (
        <div className="card">
          {format === 'html' ? (
            <iframe srcDoc={content} style={{ width: '100%', height: '600px', border: 'none', borderRadius: 6, background: '#0d1117' }} />
          ) : (
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem', maxHeight: '600px', overflow: 'auto', color: 'var(--text-secondary)' }}>
              {content}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
