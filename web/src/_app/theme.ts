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
 * has to guess, and guessing is what a media query exists to avoid. The CONTROL is one
 * button that flips between the two looks (`theme-toggle.tsx`); the STORED value is still one
 * of three, because "no press yet" is a state of its own and the default.
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
 * The two appearances the screen can actually have, as opposed to the three things a person
 * can ask for. `system` is a request, not a look: it resolves to one of these through the
 * operating system's preference, and the control needs the RESOLVED one to know what its
 * press would switch to.
 */
export type ThemeAppearance = Exclude<ThemeChoice, 'system'>;

/**
 * The label each choice carries.
 *
 * Russian, because the interface is Russian. The two appearances read as the NAME OF THE
 * THEME («Светлая тема», «Тёмная тема»): the one control that shows them (`theme-toggle.tsx`)
 * uses the name of the theme its press switches TO as its tooltip and its accessible name,
 * which is the original application's wording. The MACHINE value stays in
 * `data-theme-choice` on the control and in `data-theme` on the document element, so the
 * browser journey and the PA-01 criterion-4 evidence read the value and not the wording —
 * translating this record moves no test.
 */
export const THEME_LABELS: Readonly<Record<ThemeChoice, string>> = {
  system: 'Как в системе',
  light: 'Светлая тема',
  dark: 'Тёмная тема',
};

/**
 * What the control is called while it does not yet know which appearance is showing.
 *
 * Only the first render, which the server produces and the client must reproduce: neither
 * can read the operating system's preference (the server has no screen; the client's first
 * render must equal the server's markup). The effect resolves the appearance right after
 * hydration and the label becomes the theme's name. The GLYPH does not wait for that — it is
 * chosen by the stylesheet from the same selectors that choose the palette, so the control
 * never paints the wrong picture.
 */
export const THEME_SWITCH_LABEL = 'Сменить тему';

/** The media query the dark palette in `globals.css` answers to. */
export const SYSTEM_DARK_QUERY = '(prefers-color-scheme: dark)';

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

/**
 * The appearance showing for a choice, or `null` when it cannot be known yet.
 *
 * `light` and `dark` are themselves. `system` is the operating system's preference, which is
 * `systemPrefersDark`: `true` for dark, `false` for light, and `null` before anything has
 * read it (the server render and the client's first render), when the honest answer is "not
 * known" and not a guess that the next frame would contradict.
 */
export function resolveThemeAppearance(choice: ThemeChoice, systemPrefersDark: boolean): ThemeAppearance;
export function resolveThemeAppearance(
  choice: ThemeChoice,
  systemPrefersDark: boolean | null,
): ThemeAppearance | null;
export function resolveThemeAppearance(
  choice: ThemeChoice,
  systemPrefersDark: boolean | null,
): ThemeAppearance | null {
  if (choice !== 'system') return choice;
  if (systemPrefersDark === null) return null;
  return systemPrefersDark ? 'dark' : 'light';
}

/** The other appearance: what one press of the single control switches to. */
export function oppositeThemeAppearance(appearance: ThemeAppearance): ThemeAppearance {
  return appearance === 'dark' ? 'light' : 'dark';
}

/**
 * One press of the control: switch away from the appearance showing now, keep the choice and
 * put it on the document. Returns the choice made, which is always `light` or `dark`: a press
 * never writes `system`, which is the state before the first one.
 *
 * `systemPrefersDark` is read by the caller at the moment of the press, so what is switched
 * away from is what is on screen even for a choice of `system`.
 */
export function switchTheme(
  root: ThemeRoot,
  storage: ThemeStorage | null,
  choice: ThemeChoice,
  systemPrefersDark: boolean,
): ThemeAppearance {
  const next = oppositeThemeAppearance(resolveThemeAppearance(choice, systemPrefersDark));
  writeThemeChoice(storage, next);
  applyThemeChoice(root, next);
  return next;
}

/**
 * The name of the control for the appearance showing now: the theme it would switch TO, and
 * `THEME_SWITCH_LABEL` while the appearance is not known.
 */
export function themeSwitchLabel(visible: ThemeAppearance | null): string {
  return visible === null ? THEME_SWITCH_LABEL : THEME_LABELS[oppositeThemeAppearance(visible)];
}

/** The narrowest slice of a `MediaQueryList` the control needs, so a test can pass an object. */
export interface SystemDarkQuery {
  readonly matches: boolean;
  addEventListener(type: 'change', listener: (event: { readonly matches: boolean }) => void): void;
  removeEventListener(type: 'change', listener: (event: { readonly matches: boolean }) => void): void;
}

/**
 * The operating system's dark-mode query, or `null` where there is none to ask.
 *
 * Absent during a server render and in an embedded view without `matchMedia`. Both are the
 * case the stylesheet already answers with the light palette (a browser that cannot evaluate
 * `prefers-color-scheme` shows `:root`), so the control reading it as "not dark" agrees with
 * what is on screen: an absence, not a degraded mode.
 */
export function systemDarkQuery(): SystemDarkQuery | null {
  try {
    return typeof window === 'undefined' || typeof window.matchMedia !== 'function'
      ? null
      : window.matchMedia(SYSTEM_DARK_QUERY);
  } catch {
    return null;
  }
}
