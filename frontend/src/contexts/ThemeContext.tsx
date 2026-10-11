import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

type ThemeMode = 'dark' | 'light' | 'system';

interface ThemeCtx {
  mode: ThemeMode;
  setMode: (m: ThemeMode) => void;
  effective: 'dark' | 'light';
}

const ThemeContext = createContext<ThemeCtx>({ mode: 'dark', setMode: () => {}, effective: 'dark' });

export const useTheme = () => useContext(ThemeContext);

function getSystemTheme(): 'dark' | 'light' {
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function applyTheme(effective: 'dark' | 'light') {
  const html = document.documentElement;
  if (effective === 'light') {
    html.setAttribute('data-theme', 'light');
  } else {
    html.removeAttribute('data-theme');
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('attackgraph-theme') as ThemeMode | null;
    return saved || 'dark';
  });

  const effective: 'dark' | 'light' = mode === 'system' ? getSystemTheme() : mode;

  useEffect(() => {
    applyTheme(effective);
  }, [effective]);

  // Apply immediately on mount (no flash)
  useEffect(() => {
    const saved = localStorage.getItem('attackgraph-theme') as ThemeMode | null;
    const initial = saved || 'dark';
    const eff: 'dark' | 'light' = initial === 'system' ? getSystemTheme() : (initial as 'dark' | 'light');
    applyTheme(eff);
  }, []);

  // Listen to system preference changes
  useEffect(() => {
    if (mode !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: light)');
    const handler = () => applyTheme(getSystemTheme());
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [mode]);

  const setMode = (m: ThemeMode) => {
    setModeState(m);
    localStorage.setItem('attackgraph-theme', m);
  };

  return (
    <ThemeContext.Provider value={{ mode, setMode, effective }}>
      {children}
    </ThemeContext.Provider>
  );
}
