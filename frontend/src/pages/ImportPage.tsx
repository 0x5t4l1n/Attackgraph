import { useState, useCallback, useRef, type DragEvent } from 'react';
import { useParams } from 'react-router-dom';
import { FileUp, FileCode, Upload } from 'lucide-react';
import { api, type ImportSession } from '../services/api';
import {
  PageHeader,
  StatusBadge,
  RelativeTime,
  EmptyState,
  LoadingState,
  ErrorState,
  useToast,
  useAsync,
} from '../components/ui';

function DropZone({
  title,
  description,
  accept,
  onFile,
  icon,
}: {
  title: string;
  description: string;
  accept: string;
  onFile: (file: File) => void;
  icon: React.ReactNode;
}) {
  const [active, setActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActive(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActive(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActive(false);
    const file = e.dataTransfer.files[0];
    if (file) onFile(file);
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange = () => {
    const file = inputRef.current?.files?.[0];
    if (file) onFile(file);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div
      className={`drop-zone${active ? ' active' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        hidden
      />
      <div className="drop-zone-icon">{icon}</div>
      <div className="drop-zone-text">{title}</div>
      <div className="drop-zone-hint">{description}</div>
    </div>
  );
}

export default function ImportPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { toast } = useToast();

  const {
    data: imports,
    loading,
    error,
    reload,
  } = useAsync<ImportSession[]>(
    () => (projectId ? api.listImports(projectId) : Promise.resolve([])),
    [projectId],
  );

  const [uploading, setUploading] = useState<string | null>(null);

  const handleBurpFile = useCallback(
    (file: File) => {
      if (!projectId) return;
      setUploading('burp');
      api
        .importBurp(projectId, file)
        .then(() => {
          toast('success', `Burp import started: ${file.name}`);
          reload();
        })
        .catch((e: unknown) => {
          toast('error', `Burp import failed: ${e instanceof Error ? e.message : String(e)}`);
        })
        .finally(() => setUploading(null));
    },
    [projectId, toast, reload],
  );

  const handleOpenAPIFile = useCallback(
    (file: File) => {
      if (!projectId) return;
      setUploading('openapi');
      api
        .importOpenAPI(projectId, file)
        .then(() => {
          toast('success', `OpenAPI import started: ${file.name}`);
          reload();
        })
        .catch((e: unknown) => {
          toast('error', `OpenAPI import failed: ${e instanceof Error ? e.message : String(e)}`);
        })
        .finally(() => setUploading(null));
    },
    [projectId, toast, reload],
  );

  return (
    <div>
      <PageHeader
        title="Traffic Import"
        subtitle="Import HTTP traffic from Burp Suite or API specifications"
        icon={<Upload size={20} />}
      />

      {/* Upload Cards */}
      <div className="grid grid-2 mb-6">
        <div className="card">
          <div className="card-header">
            <span className="card-header-title flex items-center gap-2">
              <FileUp size={14} />
              Burp Suite XML
            </span>
            {uploading === 'burp' && (
              <span className="badge badge-info">Uploading...</span>
            )}
          </div>
          <div className="card-body">
            <DropZone
              title="Drop Burp Suite XML file here"
              description="Or click to browse. Accepts .xml files exported from Burp Suite HTTP history."
              accept=".xml"
              onFile={handleBurpFile}
              icon={<FileUp size={32} />}
            />
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-header-title flex items-center gap-2">
              <FileCode size={14} />
              OpenAPI / Swagger
            </span>
            {uploading === 'openapi' && (
              <span className="badge badge-info">Uploading...</span>
            )}
          </div>
          <div className="card-body">
            <DropZone
              title="Drop OpenAPI spec here"
              description="Or click to browse. Accepts OpenAPI 2.0/3.0/3.1 in JSON or YAML format."
              accept=".json,.yaml,.yml"
              onFile={handleOpenAPIFile}
              icon={<FileCode size={32} />}
            />
          </div>
        </div>
      </div>

      {/* Import History */}
      <div className="card">
        <div className="card-header">
          <span className="card-header-title">Import History</span>
          {imports && imports.length > 0 && (
            <span className="badge badge-neutral">{imports.length}</span>
          )}
        </div>
        {loading ? (
          <LoadingState message="Loading import history..." />
        ) : error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : !imports || imports.length === 0 ? (
          <EmptyState
            icon={<Upload size={32} />}
            title="No imports yet"
            description="Import Burp Suite traffic or OpenAPI specifications to populate endpoints."
          />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>File</th>
                <th>Status</th>
                <th>Imported</th>
                <th>Skipped</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {imports.map((imp) => (
                <tr key={imp.id}>
                  <td>
                    <span className="badge badge-info">{imp.source_type}</span>
                  </td>
                  <td className="mono truncate" style={{ maxWidth: 240 }}>
                    {imp.filename}
                  </td>
                  <td>
                    <StatusBadge status={imp.status} />
                  </td>
                  <td className="text-success font-medium">{imp.items_imported}</td>
                  <td className="text-muted">{imp.items_skipped}</td>
                  <td>
                    <RelativeTime date={imp.started_at} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
