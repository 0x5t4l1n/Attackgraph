import { Settings, Moon, Sun, Monitor, Server, Shield, Info } from 'lucide-react';
import { PageHeader, useToast } from '../components/ui';
import { useTheme } from '../contexts/ThemeContext';
import { api } from '../services/api';
import { useAsync } from '../components/ui';

type ThemeMode = 'dark' | 'light' | 'system';
const THEME_OPTIONS: { value: ThemeMode; icon: React.ComponentType<{ size?: number }>; label: string; desc: string }[] = [
  { value: 'dark', icon: Moon, label: 'Dark', desc: 'Cybersecurity workstation dark theme' },
  { value: 'light', icon: Sun, label: 'Light', desc: 'Clean light theme for bright environments' },
  { value: 'system', icon: Monitor, label: 'System', desc: 'Follow your OS preference' },
];

export default function SettingsPage() {
  const { mode, setMode } = useTheme();
  const { toast } = useToast();

  const { data: config } = useAsync(() => api.getAIConfig(), []);
  const { data: settings } = useAsync(() => api.getSettings(), []);

  const handleCopyInfo = () => {
    const info = JSON.stringify({ settings, config }, null, 2);
    navigator.clipboard.writeText(info);
    toast('success', 'Configuration copied to clipboard');
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Settings"
        icon={<Settings size={20} />}
        subtitle="Application configuration and preferences"
      />

      {/* Appearance */}
      <div className="card">
        <div className="card-header">
          <span className="card-header-title">Appearance</span>
        </div>
        <div className="card-body flex flex-col gap-4">
          <div>
            <div className="input-label" style={{ marginBottom: 12 }}>Theme</div>
            <div className="grid grid-3 gap-3">
              {THEME_OPTIONS.map(({ value, icon: Icon, label, desc }) => (
                <button
                  key={value}
                  onClick={() => setMode(value)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    gap: 8,
                    padding: '14px 16px',
                    background: mode === value ? 'var(--bg-active)' : 'var(--bg-surface)',
                    border: `2px solid ${mode === value ? 'var(--accent)' : 'var(--border-default)'}`,
                    borderRadius: 'var(--radius-lg)',
                    cursor: 'pointer',
                    transition: 'var(--transition-base)',
                    textAlign: 'left',
                    width: '100%',
                  }}
                >
                  <span style={{ color: mode === value ? 'var(--accent)' : 'var(--text-muted)' }}><Icon size={20} /></span>
                  <div>
                    <div className="text-sm font-semibold" style={{ color: mode === value ? 'var(--accent)' : 'var(--text-primary)', marginBottom: 2 }}>{label}</div>
                    <div className="text-xs text-muted">{desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* AI Configuration summary */}
      <div className="card">
        <div className="card-header">
          <span className="card-header-title flex items-center gap-2"><Shield size={14} /> AI Assistant</span>
        </div>
        <div className="card-body flex flex-col gap-3">
          <p className="text-sm text-muted">Configure AI providers on the AI Assistant page.</p>
          {config && (
            <div className="grid grid-3 gap-3">
              <div>
                <div className="detail-label">Status</div>
                <div className="detail-value">
                  <span className={`badge ${config.enabled ? 'badge-success' : 'badge-neutral'}`}>
                    {config.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </div>
              <div>
                <div className="detail-label">Model</div>
                <div className="detail-value mono">{config.model || '—'}</div>
              </div>
              <div>
                <div className="detail-label">API Key</div>
                <div className="detail-value">
                  <span className={`badge ${config.api_key_set ? 'badge-success' : 'badge-neutral'}`}>
                    {config.api_key_set ? 'Configured' : 'Not set'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Backend info */}
      {settings && (
        <div className="card">
          <div className="card-header">
            <span className="card-header-title flex items-center gap-2"><Server size={14} /> Backend Configuration</span>
            <button className="btn-ghost btn-sm flex items-center gap-1" onClick={handleCopyInfo}>
              <Info size={12} />
              Copy
            </button>
          </div>
          <div className="card-body flex flex-col gap-3">
            <div className="grid grid-3 gap-3">
              <div>
                <div className="detail-label">CORS Origins</div>
                <div className="detail-value text-xs mono">{(settings as { server?: { cors_origins?: string[] } }).server?.cors_origins?.join(', ') || '—'}</div>
              </div>
              <div>
                <div className="detail-label">Max Crawl Pages</div>
                <div className="detail-value">{(settings as { crawler?: { max_pages?: number } }).crawler?.max_pages || '—'}</div>
              </div>
              <div>
                <div className="detail-label">Max Depth</div>
                <div className="detail-value">{(settings as { crawler?: { max_depth?: number } }).crawler?.max_depth || '—'}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* About */}
      <div className="card">
        <div className="card-header">
          <span className="card-header-title flex items-center gap-2"><Info size={14} /> About</span>
        </div>
        <div className="card-body">
          <div className="grid grid-3 gap-3">
            <div>
              <div className="detail-label">Version</div>
              <div className="detail-value mono">0.1.0</div>
            </div>
            <div>
              <div className="detail-label">Frontend</div>
              <div className="detail-value mono">React 19 + Vite</div>
            </div>
            <div>
              <div className="detail-label">Backend</div>
              <div className="detail-value mono">FastAPI + SQLite</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
