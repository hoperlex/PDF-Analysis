/**
 * The theme choice: what it can be, where it is kept, and how it reaches the document.
 *
 * Everything here is a pure function over an interface small enough to hand a fake, which
 * is why it is a module and not three lines inside the component. The suite runs under
 * `environment: 'node'` — there is no `window`, no `localStorage` and no `document` — so a
 * component that read the browser globals directly would be a component no test in this
 * repository could exercise. `tests/unit/styles/theme.test.ts` drives every branch below
 * with an object literal.
 *
 * WHAT A CHOICE IS. Three values and not two. `light` and `dark` are the two palettes in
 * `globals.css`; `system` is the absence of a choice, and it is the DEFAULT rather than a
 * third appearance — it removes the attribute and lets `@media (prefers-color-scheme: dark)`
 * decide. A two-value toggle cannot express "follow the system", which means a first visit
 * has to guess, and guessing is what a media query exists to avoid.
 *
 * WHAT IS STORED IS THE CHOICE, NOT THE APPEARANCE. Storing the resolved `dark` for a user
 * who picked `system` on a dark machine would freeze that resolution: they change their
 * system to light and the application stays dark, with nothing on screen explaining why.
 * The stored value is the answer to "what did you ask for", and the media query re-resolves
 * it on every visit.
 */

/** The key under which the choice is kept. Prefixed: browser storage is per origin, not per app. */
export const THEME_STORAGE_KEY = 'am-theme';

/** The attribute the palette blocks in `globals.css` select on. */
export const THEME_ATTRIBUTE = 'data-theme';

export const THEME_CHOICES = ['system', 'light', 'dark'] as const;
export type ThemeChoice = (typeof THEME_CHOICES)[number];

/**
 * The label each choice carries.
 *
 * Russian, because the interface is Russian. The MACHINE value stays in
 * `data-theme-choice` on the control and in `data-theme` on the document element, so the
 * browser journey and the PA-01 criterion-4 evidence read the value and not the wording —
 * translating this record moves no test.
 */
export const THEME_LABELS: Readonly<Record<ThemeChoice, string>> = {
  system: 'Как в системе',
  light: 'Светлая',
  dark: 'Тёмная',
};

export function isThemeChoice(value: unknown): value is ThemeChoice {
  return typeof value === 'string' && (THEME_CHOICES as readonly string[]).includes(value);
}

/** The narrowest slice of `Storage` this module needs, so a test can pass an object. */
export interface ThemeStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

/** The narrowest slice of an element this module needs. */
export interface ThemeRoot {
  setAttribute(name: string, value: string): void;
  removeAttribute(name: string): void;
}

/**
 * `localStorage`, or `null` where it cannot be had.
 *
 * It throws rather than returns on a browser configured to refuse storage, and it does not
 * exist at all during a server render. Both are the same case here: no stored choice, and
 * the system preference decides — which is a working application, not a degraded one, so
 * this is a genuine absence and not a silent fallback.
 */
export function themeStorage(): ThemeStorage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** The stored choice, or `system` when there is none and when what is stored is not one. */
export function readThemeChoice(storage: ThemeStorage | null): ThemeChoice {
  if (storage === null) return 'system';
  let stored: string | null;
  try {
    stored = storage.getItem(THEME_STORAGE_KEY);
  } catch {
    return 'system';
  }
  return isThemeChoice(stored) ? stored : 'system';
}

/** Keep the choice. A storage that refuses the write costs the persistence, not the theme. */
export function writeThemeChoice(storage: ThemeStorage | null, choice: ThemeChoice): void {
  if (storage === null) return;
  try {
    storage.setItem(THEME_STORAGE_KEY, choice);
  } catch {
    /* A full or refused quota is not a reason to leave the screen in the wrong theme. */
  }
}

/**
 * Put the choice on the document element, which is what the palette blocks select on.
 *
 * `system` REMOVES the attribute rather than writing a third value: there is no
 * `[data-theme='system']` block and there must not be one, because the whole point is to
 * let the media query answer.
 */
export function applyThemeChoice(root: ThemeRoot, choice: ThemeChoice): void {
  if (choice === 'system') root.removeAttribute(THEME_ATTRIBUTE);
  else root.setAttribute(THEME_ATTRIBUTE, choice);
}
