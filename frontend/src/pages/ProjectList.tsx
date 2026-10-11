import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api, type Project } from '../services/api';
import { Plus, Trash2, FolderOpen } from 'lucide-react';
import {
  PageHeader,
  SearchInput,
  EmptyState,
  LoadingState,
  ErrorState,
  RelativeTime,
  useAsync,
  useToast,
  useConfirm,
} from '../components/ui';

export default function ProjectList() {
  const [search, setSearch] = useState('');
  const { toast } = useToast();
  const { confirm } = useConfirm();

  const { data: projects, loading, error, reload } = useAsync(
    () => api.listProjects(),
    [],
  );

  const filtered = useMemo(() => {
    if (!projects) return [];
    if (!search.trim()) return projects;
    const q = search.toLowerCase();
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.target_url.toLowerCase().includes(q),
    );
  }, [projects, search]);

  const handleDelete = async (p: Project) => {
    const ok = await confirm({
      title: 'Delete Project',
      message: `Permanently delete "${p.name}" and all its data? This cannot be undone.`,
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!ok) return;

    try {
      await api.deleteProject(p.id);
      toast('success', `Project "${p.name}" deleted`);
      reload();
    } catch (e: unknown) {
      toast('error', e instanceof Error ? e.message : 'Failed to delete project');
    }
  };

  if (loading) return <LoadingState message="Loading projects..." />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div>
      <PageHeader
        title="Projects"
        subtitle={`${projects?.length ?? 0} project${projects?.length === 1 ? '' : 's'}`}
        actions={
          <Link to="/new">
            <button className="btn-primary" type="button">
              <Plus size={14} />
              New Project
            </button>
          </Link>
        }
      />

      {projects && projects.length > 0 && (
        <div className="toolbar">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Filter by name or target..."
          />
        </div>
      )}

      {!projects || projects.length === 0 ? (
        <EmptyState
          icon={<FolderOpen size={40} />}
          title="No projects yet"
          description="Create a project to start mapping attack surfaces and discovering vulnerabilities."
          action={
            <Link to="/new">
              <button className="btn-primary" type="button">
                <Plus size={14} />
                New Project
              </button>
            </Link>
          }
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No matching projects"
          description="Try adjusting your search terms."
        />
      ) : (
        <div className="grid grid-2">
          {filtered.map((p) => (
            <div key={p.id} className="card card-clickable">
              <div className="card-body">
                <div className="flex justify-between items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <Link to={`/projects/${p.id}`} className="font-semibold text-lg">
                      {p.name}
                    </Link>
                    <div className="font-mono text-sm text-muted truncate">
                      {p.target_url}
                    </div>
                  </div>
                  <button
                    className="btn-danger btn-icon btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(p);
                    }}
                    title="Delete project"
                    type="button"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                {p.description && (
                  <div className="text-sm text-secondary truncate mb-2">
                    {p.description}
                  </div>
                )}
                <div className="text-xs text-muted">
                  Created <RelativeTime date={p.created_at} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
