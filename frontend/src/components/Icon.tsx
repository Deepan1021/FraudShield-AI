import type { ReactElement } from 'react';

const PATHS: Record<string, ReactElement> = {
  dashboard: <><rect x="3" y="3" width="7" height="9" rx="1" /><rect x="14" y="3" width="7" height="5" rx="1" /><rect x="14" y="12" width="7" height="9" rx="1" /><rect x="3" y="16" width="7" height="5" rx="1" /></>,
  analyze: <><path d="M12 2 4 5.500V11c0 5 3.400 8.600 8 10 4.600-1.400 8-5 8-10V5.500z" /><path d="m9 12 2 2 4-4" /></>,
  history: <><path d="M3 12a9 9 0 1 0 3-6.700L3 8" /><path d="M3 3v5h5M12 7v5l3 2" /></>,
  analytics: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
  rules: <><path d="M4 6h16M4 12h10M4 18h16" /><circle cx="18" cy="12" r="2" /></>,
  kb: <><ellipse cx="12" cy="6" rx="8" ry="3" /><path d="M4 6v6c0 1.700 3.600 3 8 3s8-1.300 8-3V6M4 12v6c0 1.700 3.600 3 8 3s8-1.300 8-3v-6" /></>,
  reports: <><path d="M6 2h8l5 5v15H6z" /><path d="M14 2v5h5M9 13h7M9 17h7" /></>,
  audit: <><path d="M9 11l3 3 8-8" /><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M19.400 15a1.700 1.700 0 0 0 .3 1.800l.1.1a2 2 0 1 1-2.800 2.800l-.1-.1a1.700 1.700 0 0 0-1.800-.3 1.700 1.700 0 0 0-1 1.500V21a2 2 0 1 1-4 0v-.1a1.700 1.700 0 0 0-1-1.500 1.700 1.700 0 0 0-1.800.3l-.1.1a2 2 0 1 1-2.800-2.800l.1-.1a1.700 1.700 0 0 0 .3-1.800 1.700 1.700 0 0 0-1.500-1H3a2 2 0 1 1 0-4h.1a1.700 1.700 0 0 0 1.500-1 1.700 1.700 0 0 0-.3-1.800l-.1-.1a2 2 0 1 1 2.800-2.800l.1.1a1.700 1.700 0 0 0 1.800.3h0a1.700 1.700 0 0 0 1-1.500V3a2 2 0 1 1 4 0v.1a1.700 1.700 0 0 0 1 1.500h0a1.700 1.700 0 0 0 1.800-.3l.1-.1a2 2 0 1 1 2.800 2.800l-.1.1a1.700 1.700 0 0 0-.3 1.800v0a1.700 1.700 0 0 0 1.500 1H21a2 2 0 1 1 0 4h-.1a1.700 1.700 0 0 0-1.500 1z" /></>,
  about: <><circle cx="12" cy="12" r="9" /><path d="M12 8h.01M11 12h1v5h1" /></>,
  menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
  download: <><path d="M12 3v12m0 0-4-4m4 4 4-4M4 21h16" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m21 21-4.300-4.300" /></>,
  chevron: <><path d="m9 6 6 6-6 6" /></>,
  alert: <><path d="M12 3 2 20h20z" /><path d="M12 10v5M12 18h.01" /></>,
};

export function Icon({ name, size = 18, className = '' }: { name: string; size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className}>
      {PATHS[name] ?? null}
    </svg>
  );
}
