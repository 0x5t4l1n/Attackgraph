import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Bot } from 'lucide-react';

export default function AIPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [aiEnabled, setAiEnabled] = useState(false);
  const [model, setModel] = useState<string | null>(null);
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.aiStatus().then(s => { setAiEnabled(s.enabled); setModel(s.model); }).catch(() => {});
  }, []);

  const summarize = async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      const result = await api.aiSummarize(projectId);
      setSummary(result.summary);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1><Bot size={20} style={{ verticalAlign: 'middle', marginRight: 8 }} />AI Assistant</h1>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginBottom: '0.75rem' }}>Status</h3>
        <div style={{ display: 'flex', gap: '2rem' }}>
          <div>
            <span style={{ color: 'var(--text-secondary)' }}>AI Enabled: </span>
            <span className={`badge ${aiEnabled ? 'badge-low' : 'badge-hypothesis'}`}>
              {aiEnabled ? 'Yes' : 'No'}
            </span>
          </div>
          {model && (
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Model: </span>
              <span>{model}</span>
            </div>
          )}
        </div>
        {!aiEnabled && (
          <p style={{ color: 'var(--text-muted)', marginTop: '0.75rem', fontSize: '0.85rem' }}>
            AI features are disabled. Configure an OpenAI-compatible API endpoint in the backend settings to enable AI-powered analysis.
            All core features work without AI.
          </p>
        )}
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginBottom: '0.75rem' }}>Graph Summary</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
          Generate an AI-powered summary of the application graph, highlighting key entry points, sensitive operations, and security-relevant patterns.
        </p>
        <button className="btn-primary" onClick={summarize} disabled={loading}>
          {loading ? 'Summarizing...' : 'Summarize Graph'}
        </button>
      </div>

      {error && <div className="card" style={{ color: 'var(--danger)', marginBottom: '1rem' }}>{error}</div>}

      {summary && (
        <div className="card">
          <h3 style={{ marginBottom: '0.75rem' }}>Summary</h3>
          <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{summary}</div>
        </div>
      )}
    </div>
  );
}
