import type { ReactNode } from 'react';

/** Small original line drawings for the product menu; the shared Feather set is unchanged. */
const glyphs = {
  projects: <path d="M3 7V5a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Zm0 3h18" />,
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="1.4" /><rect x="14" y="3" width="7" height="7" rx="1.4" /><rect x="3" y="14" width="7" height="7" rx="1.4" /><rect x="14" y="14" width="7" height="7" rx="1.4" /></>,
  optimisation: <><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="9" cy="6" r="2" /><circle cx="16" cy="12" r="2" /><circle cx="11" cy="18" r="2" /></>,
  dispatcher: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2M7 3l-2 2" /></>,
  versions: <><path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5" /></>,
  stages: <><rect x="3" y="4" width="7" height="16" rx="1.5" /><rect x="14" y="4" width="7" height="16" rx="1.5" /><path d="m10 9 4 3-4 3" /></>,
  knowledge: <><path d="M12 5c-2-2-6-2-9-1v15c3-1 7-1 9 1 2-2 6-2 9-1V4c-3-1-7-1-9 1Zm0 0v15" /></>,
  blocks: <><rect x="4" y="4" width="7" height="7" rx="1.3" /><rect x="13" y="4" width="7" height="7" rx="1.3" /><rect x="4" y="13" width="7" height="7" rx="1.3" /><rect x="13" y="13" width="7" height="7" rx="1.3" /></>,
  norms: <><path d="M6 3h9l4 4v14H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm9 0v4h4M8 12h8M8 16h6" /></>,
  logs: <><path d="M7 5h14M7 12h14M7 19h14" /><circle cx="3.5" cy="5" r=".8" /><circle cx="3.5" cy="12" r=".8" /><circle cx="3.5" cy="19" r=".8" /></>,
  workers: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-2a6 6 0 0 1 12 0v2H3ZM17 5a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 5" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M19 5l-2 2M7 17l-2 2" /></>,
  queue: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M8 9h8M8 13h8M8 17h5" /></>,
  users: <><circle cx="9" cy="8" r="3" /><circle cx="17" cy="9" r="2.5" /><path d="M2 20a7 7 0 0 1 14 0H2Zm14-5a5 5 0 0 1 6 5h-4" /></>,
  registrations: <><circle cx="9" cy="8" r="3" /><path d="M2 20a7 7 0 0 1 14 0H2Zm16-13v8m-4-4h8" /></>,
} satisfies Record<string, ReactNode>;

type GlyphName = keyof typeof glyphs;

const byLabel: Readonly<Record<string, GlyphName>> = {
  'Проекты': 'projects',
  'Дашборд': 'dashboard',
  'Оптимизация разделов': 'optimisation',
  'Диспетчер': 'dispatcher',
  'Сравнение версий': 'versions',
  'Сравнение стадий': 'stages',
  'База знаний': 'knowledge',
  'Блоки': 'blocks',
  'Нормы': 'norms',
  'Журнал выполнения': 'logs',
  'Исполнители': 'workers',
  'Настройки анализа': 'settings',
  'Очередь': 'queue',
  'Пользователи': 'users',
  'Заявки на регистрацию': 'registrations',
};

export const NAVIGATION_GLYPH_LABELS = Object.keys(byLabel);

export function NavigationGlyph({ label }: { readonly label: string }) {
  const glyph = byLabel[label];
  if (glyph === undefined) {
    // A newly registered row remains recognisable until its own icon is drawn.
    return <span data-nav-glyph="fallback" aria-hidden="true">{Array.from(label).slice(0, 2).join('').toUpperCase()}</span>;
  }
  return (
    <svg data-nav-glyph={glyph} viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {glyphs[glyph]}
    </svg>
  );
}
