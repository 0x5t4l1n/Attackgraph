import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Project } from '../services/api';
import { Plus, Trash2, ExternalLink } from 'lucide-react';

export default function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    api
      .listProjects()
      .then(setProjects)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleDelete = (id: string, name: string) => {
    if (!confirm(`Delete project "${name}"? This cannot be undone.`)) return;
    api
      .deleteProject(id)
      .then(load)
      .catch((e: Error) => setError(e.message));
  };

  return (
    <div>
      <div className="page-header">
        <h1>Projects</h1>
        <Link to="/new">
          <button className="btn-primary" type="button">
            <Plus size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />
            New Project
          </button>
        </Link>
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--danger)', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading">Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <p>No projects yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="grid grid-2">
          {projects.map((p) => (
            <div key={p.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <Link to={`/projects/${p.id}`} style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                    {p.name} <ExternalLink size={12} style={{ verticalAlign: 'middle' }} />
                  </Link>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                    {p.target_url}
                  </div>
                </div>
                <button
                  className="btn-danger"
                  style={{ padding: '0.25rem 0.5rem' }}
                  onClick={() => handleDelete(p.id, p.name)}
                  type="button"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              {p.description && (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
                  {p.description}
                </div>
              )}
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
                Created {new Date(p.created_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
