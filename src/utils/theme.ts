import type { ThemeMode } from './types/analysis';

export function applyTheme(theme: ThemeMode = 'light') {
  const root = document.documentElement;
  let resolved: 'light' | 'dark' = 'light';
  if (theme === 'system') {
    resolved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } else {
    resolved = theme;
  }
  root.setAttribute('data-theme', resolved);
  root.style.colorScheme = resolved;
}
