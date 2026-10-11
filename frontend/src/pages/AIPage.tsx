import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Bot, Loader2, Sparkles, Eye, EyeOff, Save, CheckCircle2, Copy, RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { api } from '../services/api';
import { PageHeader, LoadingState, ErrorState, useToast, useAsync } from '../components/ui';

interface Provider {
  id: string;
  name: string;
  description: string;
  api_base: string;
  needs_key: boolean;
  default_model: string;
  model_examples: string[];
}

const PROVIDERS: Provider[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    description: 'GPT-4o, GPT-4o-mini, o1',
    api_base: 'https://api.openai.com/v1',
    needs_key: true,
    default_model: 'gpt-4o-mini',
    model_examples: ['gpt-4o-mini', 'gpt-4o', 'o1-mini', 'o3-mini'],
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    description: 'Gemini 2.0 Flash, 1.5 Pro',
    api_base: 'https://generativelanguage.googleapis.com/v1beta/openai',
    needs_key: true,
    default_model: 'gemini-2.0-flash',
    model_examples: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    description: 'Claude, Gemini, Llama, Mistral & 200+ models',
    api_base: 'https://openrouter.ai/api/v1',
    needs_key: true,
    default_model: 'anthropic/claude-3.5-sonnet',
    model_examples: ['anthropic/claude-3.5-sonnet', 'openai/gpt-4o', 'google/gemini-2.0-flash', 'meta-llama/llama-3.3-70b-instruct'],
  },
  {
    id: 'ollama',
    name: 'Ollama (Local)',
    description: 'Self-hosted local models — no API key needed',
    api_base: 'http://localhost:11434/v1',
    needs_key: false,
    default_model: 'llama3.2',
    model_examples: ['llama3.2', 'llama3.1', 'mistral', 'qwen2.5-coder', 'deepseek-r1'],
  },
];

function detectProvider(api_base: string): string {
  if (api_base.includes('openai.com')) return 'openai';
  if (api_base.includes('googleapis.com')) return 'gemini';
  if (api_base.includes('openrouter.ai')) return 'openrouter';
  if (api_base.includes('localhost') || api_base.includes('127.0.0.1') || api_base.includes('ollama')) return 'ollama';
  return 'custom';
}

const SUGGESTED_PROMPTS = [
  "Summarize the application's attack surface",
  "Explain the highest-priority attack paths",
  "Identify endpoints with insufficient authorization",
];

export default function AIPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { toast } = useToast();

  // Summarize state
  const [summary, setSummary] = useState<string | null>(null);
  const [summarizing, setSummarizing] = useState(false);

  // Config form state
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [apiBase, setApiBase] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [configDirty, setConfigDirty] = useState(false);

  const { data: config, loading, error, reload } = useAsync(async () => {
    const cfg = await api.getAIConfig();
    const provider = detectProvider(cfg.api_base);
    setSelectedProvider(provider);
    setApiBase(cfg.api_base);
    setModel(cfg.model);
    setApiKey('');
    return cfg;
  }, []);

  const handleProviderSelect = (provider: Provider) => {
    setSelectedProvider(provider.id);
    setApiBase(provider.api_base);
    setModel(provider.default_model);
    setApiKey('');
    setConfigDirty(true);
  };

  const handleSave = async (enable: boolean) => {
    setSaving(true);
    try {
      const update: Record<string, unknown> = {
        enabled: enable,
        api_base: apiBase,
        model,
      };
      if (apiKey) update.api_key = apiKey;
      await api.updateAIConfig(update);
      toast('success', `AI ${enable ? 'enabled' : 'disabled and config saved'}`);
      setConfigDirty(false);
      setApiKey('');
      reload();
    } catch (e: unknown) {
      toast('error', e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleSummarize = async () => {
    setSummarizing(true);
    setSummary(null);
    try {
      const r = await api.aiSummarize(projectId!);
      setSummary(r.summary);
    } catch (e: unknown) {
      toast('error', e instanceof Error ? e.message : 'AI request failed');
    } finally {
      setSummarizing(false);
    }
  };

  if (loading) return <LoadingState message="Loading AI configuration..." />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const currentProvider = PROVIDERS.find(p => p.id === selectedProvider);
  const isEnabled = config?.enabled ?? false;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="AI Assistant"
        icon={<Bot size={20} />}
        actions={
          <div className="flex items-center gap-2">
            <span
              className="status-dot"
              style={{
                background: isEnabled ? 'var(--success)' : 'var(--text-muted)',
                boxShadow: isEnabled ? '0 0 6px var(--success)' : 'none',
              }}
            />
            <span className="text-sm text-muted">{isEnabled ? `Connected · ${config?.model}` : 'Disabled'}</span>
          </div>
        }
      />

      {/* Provider selector */}
      <div className="card">
        <div className="card-header"><span className="card-header-title">Provider</span></div>
        <div className="card-body flex flex-col gap-3">
          <div className="grid grid-4 gap-2">
            {PROVIDERS.map(p => (
              <button
                key={p.id}
                onClick={() => handleProviderSelect(p)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  padding: '10px 12px',
                  gap: 4,
                  background: selectedProvider === p.id ? 'var(--bg-raised)' : 'var(--bg-surface)',
                  border: `1.5px solid ${selectedProvider === p.id ? 'var(--accent)' : 'var(--border)'}`,
                  borderRadius: 'var(--radius)',
                  cursor: 'pointer',
                  transition: 'var(--transition)',
                  textAlign: 'left',
                  width: '100%',
                }}
              >
                {selectedProvider === p.id && isEnabled && (
                  <CheckCircle2 size={12} style={{ color: 'var(--success)', alignSelf: 'flex-end', marginBottom: -16, position: 'relative', top: 0 }} />
                )}
                <span className="text-sm" style={{ fontWeight: 600, color: selectedProvider === p.id ? 'var(--accent)' : 'var(--text-primary)' }}>{p.name}</span>
                <span className="text-xs text-muted">{p.description}</span>
              </button>
            ))}
          </div>

          {/* Config fields */}
          <div className="flex flex-col gap-3" style={{ marginTop: 4 }}>
            <div className="input-group">
              <label className="input-label">API Base URL</label>
              <input
                type="url"
                value={apiBase}
                onChange={e => { setApiBase(e.target.value); setConfigDirty(true); }}
                placeholder="https://api.openai.com/v1"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
              />
              {selectedProvider === 'ollama' && (
                <div className="input-hint">Default for Ollama. Change if running on a different host/port.</div>
              )}
            </div>

            {(currentProvider?.needs_key !== false) && (
              <div className="input-group">
                <label className="input-label">
                  API Key
                  {config?.api_key_set && <span className="badge badge-success" style={{ marginLeft: 8, fontSize: 10 }}>saved</span>}
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={e => { setApiKey(e.target.value); setConfigDirty(true); }}
                    placeholder={config?.api_key_set ? '••••••••  (leave blank to keep existing)' : 'sk-...'}
                    style={{ paddingRight: 40, fontFamily: 'var(--font-mono)', fontSize: 12, width: '100%' }}
                    autoComplete="off"
                  />
                  <button
                    type="button"
                    className="btn-ghost btn-icon btn-sm"
                    onClick={() => setShowKey(!showKey)}
                    style={{ position: 'absolute', right: 4, top: '50%', transform: 'translateY(-50%)' }}
                  >
                    {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                <div className="input-hint">Stored locally on this server. Never sent to external systems except the configured provider.</div>
              </div>
            )}

            {selectedProvider === 'ollama' && (
              <div className="input-group">
                <label className="input-label" style={{ color: 'var(--text-muted)' }}>API Key</label>
                <input type="text" value="not-required" disabled style={{ color: 'var(--text-muted)', fontStyle: 'italic' }} />
                <div className="input-hint">Ollama does not require an API key.</div>
              </div>
            )}

            <div className="input-group">
              <label className="input-label">Model</label>
              <input
                type="text"
                value={model}
                onChange={e => { setModel(e.target.value); setConfigDirty(true); }}
                placeholder={currentProvider?.default_model ?? 'model-name'}
                style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
                list="model-suggestions"
              />
              {currentProvider?.model_examples && (
                <datalist id="model-suggestions">
                  {currentProvider.model_examples.map(m => <option key={m} value={m} />)}
                </datalist>
              )}
              {currentProvider?.model_examples && (
                <div className="input-hint">
                  Examples: {currentProvider.model_examples.join(', ')}
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <button
                className="btn-primary flex gap-1 items-center"
                onClick={() => handleSave(true)}
                disabled={saving || (!configDirty && isEnabled)}
              >
                {saving ? <Loader2 size={14} className="spinner" /> : <Save size={14} />}
                {isEnabled ? 'Save & Keep Enabled' : 'Save & Enable'}
              </button>
              {isEnabled && (
                <button
                  className="btn-ghost flex gap-1 items-center"
                  onClick={() => handleSave(false)}
                  disabled={saving}
                >
                  Disable AI
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Summary section — only when enabled */}
      {isEnabled && (
        <>
          <div className="card">
            <div className="card-header">
              <span className="card-header-title">Graph Summary</span>
              <span className="badge badge-neutral" style={{ fontSize: 10 }}>{config?.model}</span>
            </div>
            <div className="card-body flex flex-col gap-3">
              <p className="text-sm text-muted">Generate a natural language summary of the application's security posture based on the current graph data.</p>
              <div>
                <button
                  className="btn-primary flex gap-1 items-center"
                  onClick={handleSummarize}
                  disabled={summarizing}
                >
                  {summarizing ? <Loader2 size={14} className="spinner" /> : <Sparkles size={14} />}
                  {summarizing ? 'Analyzing…' : 'Summarize Graph'}
                </button>
              </div>
              {summarizing && (
                <div className="flex items-center gap-2 text-muted text-sm">
                  <Loader2 size={14} className="spinner" />
                  Sending graph data to {config?.model}…
                </div>
              )}
              {summary && (
                <div style={{ background: 'var(--bg-app)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                  <div className="flex items-center justify-between" style={{ padding: '10px 16px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-raised)' }}>
                    <div className="flex items-center gap-2">
                      <Sparkles size={12} style={{ color: 'var(--accent)' }} />
                      <span className="text-xs text-muted">AI Summary · {config?.model}</span>
                    </div>
                    <div className="flex gap-1">
                      <button className="btn-ghost btn-icon btn-sm" title="Copy" onClick={() => navigator.clipboard.writeText(summary)}>
                        <Copy size={12} />
                      </button>
                      <button className="btn-ghost btn-icon btn-sm" title="Regenerate" onClick={handleSummarize} disabled={summarizing}>
                        <RefreshCw size={12} className={summarizing ? 'spinner' : ''} />
                      </button>
                    </div>
                  </div>
                  <div className="md-content" style={{ padding: '16px 20px' }}>
                    <ReactMarkdown>{summary}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header"><span className="card-header-title">Suggested Analyses</span></div>
            <div className="card-body flex flex-col gap-2">
              {SUGGESTED_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  className="btn-ghost"
                  style={{ justifyContent: 'flex-start', textAlign: 'left', gap: 8 }}
                  onClick={handleSummarize}
                  disabled={summarizing}
                >
                  <Sparkles size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Info when disabled */}
      {!isEnabled && (
        <div className="card">
          <div className="card-header"><span className="card-header-title">Features without AI</span></div>
          <div className="card-body">
            <ul style={{ margin: 0, paddingLeft: 0, listStyle: 'none' }} className="flex flex-col gap-2">
              {[
                'Web crawler with scope control and robots.txt support',
                'Burp Suite and OpenAPI traffic import',
                'Application graph construction from observations',
                'Pattern-based security finding detection',
                'Attack path analysis from graph structure',
                'Test plan generation from attack paths',
                'Security assessment report export (Markdown, JSON, HTML)',
              ].map((f, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <CheckCircle2 size={14} style={{ color: 'var(--success)', flexShrink: 0 }} />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
