import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

export default function NewProject() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [description, setDescription] = useState('');
  const [allowedHosts, setAllowedHosts] = useState('');
  const [excludePaths, setExcludePaths] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    const hosts = allowedHosts
      .split(',')
      .map((h) => h.trim())
      .filter(Boolean);
    const excluded = excludePaths
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean);

    api
      .createProject({
        name,
        target_url: targetUrl,
        description,
        allowed_hosts: hosts.length > 0 ? hosts : undefined,
        exclude_paths: excluded.length > 0 ? excluded : undefined,
      })
      .then((project) => navigate(`/projects/${project.id}`))
      .catch((e: Error) => setError(e.message))
      .finally(() => setSubmitting(false));
  };

  return (
    <div style={{ maxWidth: 600 }}>
      <div className="page-header">
        <h1>New Project</h1>
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--danger)', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card">
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Project Name *
          </label>
          <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="My Web App" />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Target URL *
          </label>
          <input value={targetUrl} onChange={(e) => setTargetUrl(e.target.value)} required placeholder="https://example.com" type="url" />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="Optional description..."
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Allowed Hosts (comma-separated)
          </label>
          <input
            value={allowedHosts}
            onChange={(e) => setAllowedHosts(e.target.value)}
            placeholder="example.com, api.example.com"
          />
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Leave empty to auto-extract from target URL
          </div>
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Excluded Paths (comma-separated)
          </label>
          <input
            value={excludePaths}
            onChange={(e) => setExcludePaths(e.target.value)}
            placeholder="/logout, /admin/delete"
          />
        </div>

        <button type="submit" className="btn-primary" disabled={submitting || !name || !targetUrl}>
          {submitting ? 'Creating...' : 'Create Project'}
        </button>
      </form>
    </div>
  );
}
