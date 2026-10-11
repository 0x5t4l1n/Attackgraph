import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { X, AlertCircle, CheckCircle2, AlertTriangle, Info, Loader2 } from 'lucide-react';

// ================================================================
// Toast System
// ================================================================

type ToastType = 'success' | 'error' | 'warning' | 'info';
interface Toast { id: number; type: ToastType; message: string; }
interface ToastCtx { toast: (type: ToastType, message: string) => void; }

const ToastContext = createContext<ToastCtx>({ toast: () => {} });
export const useToast = () => useContext(ToastContext);

let toastId = 0;
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((type: ToastType, message: string) => {
    const id = ++toastId;
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const icons = { success: CheckCircle2, error: AlertCircle, warning: AlertTriangle, info: Info };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="toast-container">
        {toasts.map(t => {
          const Icon = icons[t.type];
          return (
            <div key={t.id} className={`toast toast-${t.type}`}>
              <Icon size={16} style={{ color: `var(--${t.type === 'error' ? 'danger' : t.type})`, flexShrink: 0 }} />
              <span style={{ flex: 1 }}>{t.message}</span>
              <button className="btn-ghost btn-icon btn-sm" onClick={() => setToasts(prev => prev.filter(x => x.id !== t.id))}>
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

// ================================================================
// Confirm Dialog
// ================================================================

interface ConfirmOpts { title: string; message: string; confirmLabel?: string; danger?: boolean; }
interface ConfirmCtx { confirm: (opts: ConfirmOpts) => Promise<boolean>; }

const ConfirmContext = createContext<ConfirmCtx>({ confirm: () => Promise.resolve(false) });
export const useConfirm = () => useContext(ConfirmContext);

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<(ConfirmOpts & { resolve: (v: boolean) => void }) | null>(null);

  const confirm = useCallback((opts: ConfirmOpts) => {
    return new Promise<boolean>(resolve => setState({ ...opts, resolve }));
  }, []);

  const close = (value: boolean) => {
    state?.resolve(value);
    setState(null);
  };

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {state && (
        <div className="modal-overlay" onClick={() => close(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">{state.title}</div>
            <div className="modal-body">{state.message}</div>
            <div className="modal-actions">
              <button onClick={() => close(false)}>Cancel</button>
              <button className={state.danger ? 'btn-danger' : 'btn-primary'} onClick={() => close(true)}>
                {state.confirmLabel || 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

// ================================================================
// Empty State
// ================================================================

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon && <div className="empty-state-icon">{icon}</div>}
      <div className="empty-state-title">{title}</div>
      {description && <div className="empty-state-desc">{description}</div>}
      {action}
    </div>
  );
}

// ================================================================
// Loading
// ================================================================

export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="loading-spinner">
      <Loader2 size={16} className="spinner" style={{ animation: 'spin 0.6s linear infinite' }} />
      <span>{message}</span>
    </div>
  );
}

export function Skeleton({ width, height = 16 }: { width?: number | string; height?: number | string }) {
  return <div className="skeleton" style={{ width: width || '100%', height, minHeight: height }} />;
}

// ================================================================
// Error State
// ================================================================

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 p-6">
      <AlertCircle size={24} style={{ color: 'var(--danger)', opacity: 0.6 }} />
      <span className="text-sm text-secondary">{message}</span>
      {onRetry && <button className="btn-sm" onClick={onRetry}>Retry</button>}
    </div>
  );
}

// ================================================================
// Stat Card
// ================================================================

interface StatCardProps {
  value: number | string;
  label: string;
  color?: string;
  small?: boolean;
}

export function StatCard({ value, label, color, small }: StatCardProps) {
  return (
    <div className={`stat-card${small ? ' stat-card-sm' : ''}`}>
      <div className="stat-value" style={color ? { color } : undefined}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

// ================================================================
// Badges
// ================================================================

const severityColors: Record<string, string> = {
  critical: 'badge-critical',
  high: 'badge-danger',
  medium: 'badge-warning',
  low: 'badge-success',
  info: 'badge-info',
};

export function SeverityBadge({ severity }: { severity: string }) {
  return <span className={`badge ${severityColors[severity] || 'badge-neutral'}`}>{severity}</span>;
}

const statusColors: Record<string, string> = {
  hypothesis: 'badge-hypothesis',
  unvalidated: 'badge-warning',
  confirmed: 'badge-danger',
  false_positive: 'badge-neutral',
  inconclusive: 'badge-neutral',
  completed: 'badge-success',
  running: 'badge-info',
  pending: 'badge-neutral',
  failed: 'badge-danger',
  cancelled: 'badge-warning',
  approved: 'badge-accent',
};

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${statusColors[status] || 'badge-neutral'}`}>{status.replace(/_/g, ' ')}</span>;
}

export function MethodBadge({ method }: { method: string }) {
  const m = method.toLowerCase();
  return <span className={`method-badge method-${m}`}>{method}</span>;
}

// ================================================================
// Page Header
// ================================================================

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, icon, actions }: PageHeaderProps) {
  return (
    <div className="page-header">
      <div className="page-header-left">
        {icon}
        <div>
          <h1 className="page-title">{title}</h1>
          {subtitle && <div className="page-subtitle">{subtitle}</div>}
        </div>
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </div>
  );
}

// ================================================================
// Search Input
// ================================================================

export function SearchInput({ value, onChange, placeholder = 'Search...' }: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="search"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{ width: 220 }}
    />
  );
}

// ================================================================
// Relative Time
// ================================================================

export function RelativeTime({ date }: { date: string | null }) {
  if (!date) return <span className="text-muted">--</span>;
  // Backend stores naive UTC — append Z so JS parses as UTC, not local time
  const normalized = /[Z+\-]\d*$/.test(date) ? date : date + 'Z';
  const d = new Date(normalized);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  let text: string;
  if (mins < 1) text = 'just now';
  else if (mins < 60) text = `${mins}m ago`;
  else if (hours < 24) text = `${hours}h ago`;
  else if (days < 30) text = `${days}d ago`;
  else text = d.toLocaleDateString();

  return <time dateTime={d.toISOString()} title={d.toLocaleString()} className="text-muted">{text}</time>;
}

// ================================================================
// useAsync hook
// ================================================================

interface AsyncState<T> { data: T | null; loading: boolean; error: string | null; }

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null });
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const load = useCallback(() => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    fn()
      .then(data => { if (mountedRef.current) setState({ data, loading: false, error: null }); })
      .catch(e => { if (mountedRef.current) setState({ data: null, loading: false, error: e.message || 'Unknown error' }); });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { load(); }, [load]);

  return { ...state, reload: load };
}
