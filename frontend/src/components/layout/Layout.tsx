import { Outlet, NavLink, useParams } from 'react-router-dom';
import {
  Shield, Globe, Upload, Network, AlertTriangle,
  Route, ClipboardList, FileText, Home, Bot,
} from 'lucide-react';

interface NavItem {
  to: string;
  icon: React.ComponentType<{ size?: number }>;
  label: string;
  end?: boolean;
}

export default function Layout() {
  const { projectId } = useParams();

  const mainNav: NavItem[] = [
    { to: '/', icon: Home, label: 'Projects' },
  ];

  const projectNav: NavItem[] = projectId
    ? [
        { to: `/projects/${projectId}`, icon: Shield, label: 'Overview', end: true },
        { to: `/projects/${projectId}/crawl`, icon: Globe, label: 'Crawler' },
        { to: `/projects/${projectId}/import`, icon: Upload, label: 'Import' },
        { to: `/projects/${projectId}/endpoints`, icon: Network, label: 'Endpoints' },
        { to: `/projects/${projectId}/graph`, icon: Network, label: 'Graph' },
        { to: `/projects/${projectId}/findings`, icon: AlertTriangle, label: 'Findings' },
        { to: `/projects/${projectId}/attack-paths`, icon: Route, label: 'Attack Paths' },
        { to: `/projects/${projectId}/test-plans`, icon: ClipboardList, label: 'Test Plans' },
        { to: `/projects/${projectId}/reports`, icon: FileText, label: 'Reports' },
        { to: `/projects/${projectId}/ai`, icon: Bot, label: 'AI Assistant' },
      ]
    : [];

  const linkStyle = (isActive: boolean): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.5rem 1rem',
    color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
    background: isActive ? 'rgba(88,166,255,0.1)' : 'transparent',
    fontSize: '0.85rem',
    borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
  });

  return (
    <>
      <nav
        style={{
          width: 220,
          background: 'var(--bg-secondary)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          padding: '1rem 0',
          flexShrink: 0,
          height: '100vh',
          position: 'sticky',
          top: 0,
          overflowY: 'auto',
        }}
      >
        <div
          style={{
            padding: '0 1rem 1rem',
            borderBottom: '1px solid var(--border)',
            marginBottom: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Shield size={20} color="var(--accent)" />
            <span style={{ fontWeight: 700, fontSize: '1rem' }}>AttackGraph</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            v0.1.0
          </div>
        </div>

        {mainNav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            style={({ isActive }) => linkStyle(isActive)}
          >
            <item.icon size={16} /> {item.label}
          </NavLink>
        ))}

        {projectNav.length > 0 && (
          <>
            <div
              style={{
                padding: '0.75rem 1rem 0.25rem',
                fontSize: '0.7rem',
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Project
            </div>
            {projectNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                style={({ isActive }) => linkStyle(isActive)}
              >
                <item.icon size={16} /> {item.label}
              </NavLink>
            ))}
          </>
        )}
      </nav>
      <main style={{ flex: 1, padding: '1.5rem 2rem', overflow: 'auto', maxHeight: '100vh' }}>
        <Outlet />
      </main>
    </>
  );
}
