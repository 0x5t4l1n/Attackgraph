import { useState } from 'react';
import { Outlet, NavLink, useParams } from 'react-router-dom';
import logoUrl from '../../assets/logo.png';
import {
  Shield, Home, Globe, Upload, GitGraph,
  AlertTriangle, Route, ClipboardList, FileText, Bot,
  Settings, PanelLeftClose, PanelLeftOpen, Crosshair,
  Sun, Moon, Monitor,
} from 'lucide-react';
// Shield is used in project nav for Overview link
import { useTheme } from '../../contexts/ThemeContext';

type ThemeMode = 'dark' | 'light' | 'system';

interface NavItem {
  to: string;
  icon: React.ComponentType<{ size?: number }>;
  label: string;
  end?: boolean;
}

const THEME_OPTIONS: { value: ThemeMode; icon: React.ComponentType<{ size?: number }>; label: string }[] = [
  { value: 'dark', icon: Moon, label: 'Dark' },
  { value: 'light', icon: Sun, label: 'Light' },
  { value: 'system', icon: Monitor, label: 'System' },
];

export default function Layout() {
  const { projectId } = useParams();
  const [collapsed, setCollapsed] = useState(false);
  const { mode, setMode } = useTheme();

  const globalNav: NavItem[] = [
    { to: '/', icon: Home, label: 'Projects', end: true },
  ];

  const projectNav: NavItem[] = projectId
    ? [
        { to: `/projects/${projectId}`, icon: Shield, label: 'Overview', end: true },
        { to: `/projects/${projectId}/crawl`, icon: Globe, label: 'Crawler' },
        { to: `/projects/${projectId}/import`, icon: Upload, label: 'Traffic Import' },
        { to: `/projects/${projectId}/endpoints`, icon: Crosshair, label: 'Endpoints' },
        { to: `/projects/${projectId}/graph`, icon: GitGraph, label: 'Application Graph' },
        { to: `/projects/${projectId}/findings`, icon: AlertTriangle, label: 'Findings' },
        { to: `/projects/${projectId}/attack-paths`, icon: Route, label: 'Attack Paths' },
        { to: `/projects/${projectId}/test-plans`, icon: ClipboardList, label: 'Test Plans' },
        { to: `/projects/${projectId}/reports`, icon: FileText, label: 'Reports' },
        { to: `/projects/${projectId}/ai`, icon: Bot, label: 'AI Assistant' },
      ]
    : [];

  return (
    <>
      <nav className={`sidebar${collapsed ? ' collapsed' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-info">
            <img src={logoUrl} alt="AttackGraph" style={{ width: 28, height: 28, borderRadius: 4, flexShrink: 0 }} />
            <div className="sidebar-brand-text">
              <span className="sidebar-brand-name">AttackGraph</span>
              <span className="sidebar-brand-version">v0.1.0</span>
            </div>
          </div>
          <button
            className="btn-ghost btn-icon btn-sm"
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>

        <div className="sidebar-section">
          {globalNav.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
              title={collapsed ? item.label : undefined}
            >
              <item.icon size={16} />
              <span className="sidebar-link-label">{item.label}</span>
            </NavLink>
          ))}
        </div>

        {projectNav.length > 0 && (
          <div className="sidebar-section">
            <div className="sidebar-section-title">Project</div>
            {projectNav.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
                title={collapsed ? item.label : undefined}
              >
                <item.icon size={16} />
                <span className="sidebar-link-label">{item.label}</span>
              </NavLink>
            ))}
          </div>
        )}

        <div className="sidebar-footer">
          {!collapsed && (
            <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
              {THEME_OPTIONS.map(({ value, icon: Icon, label }) => (
                <button
                  key={value}
                  className={`btn-ghost btn-sm flex-1${mode === value ? ' active' : ''}`}
                  style={{
                    color: mode === value ? 'var(--accent)' : 'var(--text-muted)',
                    background: mode === value ? 'var(--bg-active)' : 'transparent',
                    border: 'none',
                    padding: '5px 4px',
                    gap: 3,
                    fontSize: 11,
                  }}
                  onClick={() => setMode(value)}
                  title={label}
                >
                  <Icon size={13} />
                  {label}
                </button>
              ))}
            </div>
          )}
          {collapsed && THEME_OPTIONS.map(({ value, icon: Icon, label }) => mode === value ? (
            <button
              key={value}
              className="btn-ghost btn-icon btn-sm w-full"
              style={{ color: 'var(--text-muted)' }}
              onClick={() => setMode(THEME_OPTIONS[(THEME_OPTIONS.findIndex(t => t.value === value) + 1) % 3].value)}
              title={`Theme: ${label}`}
            >
              <Icon size={14} />
            </button>
          ) : null)}
          <NavLink to="/settings" className="sidebar-link" title={collapsed ? 'Settings' : undefined}>
            <Settings size={16} />
            <span className="sidebar-link-label">Settings</span>
          </NavLink>
        </div>
      </nav>

      <div className="main-content">
        <div className="page">
          <Outlet />
        </div>
      </div>
    </>
  );
}
