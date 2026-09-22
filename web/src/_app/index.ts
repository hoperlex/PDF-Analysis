/**
 * Public API of `_app`. The root layout in `app/` imports from here and from nothing
 * deeper.
 */

export type { AppProvidersProps } from './providers';
export { AppProviders } from './providers';

export type { AppFrameProps } from './app-frame';
export { AppFrame } from './app-frame';

export { ThemeToggle } from './theme-toggle';

export type { ThemeChoice, ThemeRoot, ThemeStorage } from './theme';
export {
  THEME_ATTRIBUTE,
  THEME_CHOICES,
  THEME_LABELS,
  THEME_STORAGE_KEY,
  applyThemeChoice,
  isThemeChoice,
  readThemeChoice,
  themeStorage,
  writeThemeChoice,
} from './theme';

export { createQueryClient } from './query-client';
