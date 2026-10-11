import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { FolderPlus } from 'lucide-react';
import { PageHeader, useToast } from '../components/ui';

function isValidUrl(s: string): boolean {
  try {
    const u = new URL(s);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

export default function NewProject() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [name, setName] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [description, setDescription] = useState('');
  const [allowedHosts, setAllowedHosts] = useState('');
  const [excludePaths, setExcludePaths] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = 'Project name is required';
    if (!targetUrl.trim()) e.targetUrl = 'Target URL is required';
    else if (!isValidUrl(targetUrl.trim())) e.targetUrl = 'Must be a valid HTTP or HTTPS URL';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      const hosts = allowedHosts
        .split(',')
        .map((h) => h.trim())
        .filter(Boolean);
      const excluded = excludePaths
        .split(',')
        .map((p) => p.trim())
        .filter(Boolean);

      const project = await api.createProject({
        name: name.trim(),
        target_url: targetUrl.trim(),
        description: description.trim() || undefined,
        allowed_hosts: hosts.length > 0 ? hosts : undefined,
        exclude_paths: excluded.length > 0 ? excluded : undefined,
      });
      navigate(`/projects/${project.id}`);
    } catch (err: unknown) {
      toast('error', err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="New Project"
        icon={<FolderPlus size={20} />}
      />

      <div className="card">
        <form onSubmit={handleSubmit} className="card-body flex flex-col gap-4">
          <div className="input-group">
            <label className="input-label">Project Name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Web App"
            />
            {errors.name && <span className="input-error">{errors.name}</span>}
          </div>

          <div className="input-group">
            <label className="input-label">Target URL *</label>
            <input
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="https://example.com"
            />
            <span className="input-hint">Full URL including protocol (https://)</span>
            {errors.targetUrl && <span className="input-error">{errors.targetUrl}</span>}
          </div>

          <div className="input-group">
            <label className="input-label">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Optional project description..."
            />
          </div>

          <div className="input-group">
            <label className="input-label">Allowed Hosts</label>
            <input
              value={allowedHosts}
              onChange={(e) => setAllowedHosts(e.target.value)}
              placeholder="example.com, api.example.com"
            />
            <span className="input-hint">Comma-separated. Leave empty to auto-extract from target URL.</span>
          </div>

          <div className="input-group">
            <label className="input-label">Exclude Paths</label>
            <input
              value={excludePaths}
              onChange={(e) => setExcludePaths(e.target.value)}
              placeholder="/logout, /admin/delete"
            />
            <span className="input-hint">Comma-separated paths the crawler should skip.</span>
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => navigate(-1)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={submitting}
            >
              {submitting ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
