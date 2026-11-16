'use client';

/**
 * The theme control in the application bar: ONE button that switches to the other theme.
 *
 * Until it is pressed nothing is chosen and the screen follows the operating system (the
 * stored value is `system`, the document carries no `data-theme`, the media query in
 * `globals.css` decides). A press switches to the OPPOSITE of the theme showing now and keeps
 * that as an explicit choice. The glyph and the tooltip name the theme the press switches TO
 * — the sun and «Светлая тема» in the dark theme, the moon and «Тёмная тема» in the light one
 * — as the original application does.
 *
 * THE COST, NAMED RATHER THAN DISCOVERED. From this one control there is no way back to
 * "follow the system": after the first press the choice is explicit for good. `system` is the
 * state before the first press, not a position of the control. That is the owner's ruling
 * (`Г2-B`, 2026-11-16) and it is how the original behaves; reversing it means a second
 * control, not a change here.
 *
 * WHY IT STARTS UNRESOLVED AND MOVES IN AN EFFECT. This component is rendered inside a
 * server-rendered frame. The server has no `localStorage` and no screen, so the markup it
 * produces cannot depend on either; a first client render that read them would disagree with
 * that markup and React would discard the tree. So the first render on both sides is
 * `system` with the operating system's preference unknown, and the stored choice and the
 * preference are read in an effect.
 *
 * WHAT THE FIRST PAINT DOES NOT WAIT FOR (`P7-1`). The PALETTE: the root layout
 * (`web/src/app/layout.tsx`) runs a blocking inline script in `<head>`
 * (`shared/lib/theme-boot-script.ts`) that reads the same storage key and sets the same
 * `data-theme` on `<html>` before the first paint. The GLYPH: both icons are in the markup
 * and `app-frame.module.css` shows one by the same selectors that choose the palette
 * (`:root[data-theme='dark']`, and `:root:not([data-theme='light'])` under the dark media
 * query), so it is right on the first frame and follows the system preference live. What the
 * effect still decides is the control's NAME — the tooltip and `aria-label` — which is text
 * and cannot be chosen by a stylesheet; until it runs the control is called «Сменить тему».
 * The script touches only the attribute on `<html>`, which `<html suppressHydrationWarning>`
 * covers; this component's markup is unchanged and still equals the server's.
 */

import { useEffect, useState } from 'react';

import { Icon } from '@/shared/ui';

import type { ThemeChoice } from './theme';
import {
  applyThemeChoice,
  oppositeThemeAppearance,
  readThemeChoice,
  resolveThemeAppearance,
  switchTheme,
  systemDarkQuery,
  themeStorage,
  themeSwitchLabel,
} from './theme';

export function ThemeToggle() {
  const [choice, setChoice] = useState<ThemeChoice>('system');
  // `null` until the effect has asked the system; see the header for why not earlier.
  const [systemDark, setSystemDark] = useState<boolean | null>(null);

  useEffect(() => {
    const stored = readThemeChoice(themeStorage());
    setChoice(stored);
    applyThemeChoice(document.documentElement, stored);

    // The system's preference, and its changes: while the choice is `system` the stylesheet
    // already follows the system by itself, and this keeps the control's name in step.
    const query = systemDarkQuery();
    setSystemDark(query === null ? false : query.matches);
    if (query === null) return undefined;
    const onChange = (event: { readonly matches: boolean }): void => setSystemDark(event.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  const visible = resolveThemeAppearance(choice, systemDark);
  const label = themeSwitchLabel(visible);

  const press = (): void => {
    // The preference is read again here, not taken from state, so a press always switches
    // away from what is on screen even if a change event has not been delivered yet.
    setChoice(
      switchTheme(document.documentElement, themeStorage(), choice, systemDarkQuery()?.matches ?? false),
    );
  };

  return (
    <div className="am-theme">
      {/*
        * One real `<button>`: reachable and operable from the keyboard with no handler of its
        * own. Icon-only, so the name is `aria-label` (Russian: the rendered-language guard reads
        * it, so it cannot silently become English) and the same text is the tooltip. It is an
        * ACTION button, not a toggle in the ARIA sense: the name already says what the press
        * does, so there is no `aria-pressed` (a pressed state AND a name that flips with it
        * would be announced twice, and contradictorily).
        *
        * `data-theme-choice` is the machine value the next press writes. It is absent until the
        * appearance is known, because the server cannot say it. The browser journey and the
        * PA-01 criterion-4 evidence select on this name, so the wording is free to change.
        *
        * Both glyphs are in the markup on purpose: the stylesheet shows the one that stands for
        * the OTHER theme (see the header). `Icon` is decorative here: the button names itself.
        */}
      <button
        type="button"
        className="am-theme__option"
        data-theme-choice={visible === null ? undefined : oppositeThemeAppearance(visible)}
        aria-label={label}
        title={label}
        onClick={press}
      >
        <span className="am-theme__icon am-theme__icon--sun">
          <Icon name="light" />
        </span>
        <span className="am-theme__icon am-theme__icon--moon">
          <Icon name="dark" />
        </span>
      </button>
    </div>
  );
}
