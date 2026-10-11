import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { FileText, Download, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { PageHeader, EmptyState, useToast } from '../components/ui';

type Format = 'markdown' | 'json' | 'html';

export default function ReportsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { toast } = useToast();
  const [format, setFormat] = useState<Format>('markdown');
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const result = await api.getReport(projectId!, format);
      setContent(result);
    } catch (e: unknown) {
      toast('error', e instanceof Error ? e.message : 'Report generation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!content) return;
    const ext = format === 'markdown' ? 'md' : format;
    const mime = format === 'json' ? 'application/json' : format === 'html' ? 'text/html' : 'text/markdown';
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Reports"
        icon={<FileText size={20} />}
        subtitle="Generate security assessment reports"
      />

      <div className="card">
        <div className="card-header"><span className="card-header-title">Report Configuration</span></div>
        <div className="card-body flex flex-col gap-4">
          <div>
            <div className="input-label">Format</div>
            <div className="tabs" style={{ marginTop: 4 }}>
              {([['markdown', 'Markdown'], ['json', 'JSON'], ['html', 'HTML']] as [Format, string][]).map(([f, label]) => (
                <button
                  key={f}
                  className={`tab${format === f ? ' active' : ''}`}
                  onClick={() => { setFormat(f); setContent(null); }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary flex gap-1 items-center" onClick={handleGenerate} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spinner' : ''} />
              {loading ? 'Generating…' : 'Generate Report'}
            </button>
            {content && (
              <button className="btn-ghost flex gap-1 items-center" onClick={handleDownload}>
                <Download size={14} />
                Download
              </button>
            )}
          </div>
        </div>
      </div>

      {!content && !loading && (
        <EmptyState
          icon={<FileText size={32} />}
          title="No report generated"
          description="Select a format and click Generate Report to create a security assessment report."
        />
      )}

      {content && (
        <div className="card">
          <div className="card-header"><span className="card-header-title">Preview</span></div>
          <div className="card-body" style={{ padding: 0 }}>
            {format === 'html' ? (
              <iframe
                srcDoc={content}
                style={{ width: '100%', height: 600, border: 'none', borderRadius: '0 0 var(--radius-lg) var(--radius-lg)' }}
                sandbox="allow-same-origin"
                title="Report preview"
              />
            ) : (
              <pre style={{
                margin: 0,
                padding: 16,
                maxHeight: 600,
                overflow: 'auto',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}>{content}</pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
