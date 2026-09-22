'use client';

/**
 * The theme control in the application bar.
 *
 * Three buttons rather than a switch, because the choice has three values and the third —
 * "follow the system" — is the default. A two-state switch would make the default
 * unreachable once the user had touched it, which is the behaviour that leaves a dark-mode
 * machine showing a light application for good.
 *
 * WHY IT STARTS AT `system` AND MOVES IN AN EFFECT. This component is rendered inside a
 * server-rendered frame. The server has no `localStorage`, so the markup it produces cannot
 * depend on one; a first client render that read storage would disagree with that markup and
 * React would discard the tree. So the first render on both sides is `system` — which is the
 * right answer for every visitor who has never chosen — and the stored choice is applied in
 * an effect.
 *
 * WHAT THIS COSTS, NAMED RATHER THAN HIDDEN: a visitor who chose the OPPOSITE of their
 * system preference sees one frame of the system's theme before the effect runs. Closing it
 * needs a blocking inline script in `web/src/app/layout.tsx`, which is outside this task's
 * allowed paths. Everyone else — no choice stored, or a choice that agrees with the system —
 * sees no flash at all, because the media query has already resolved before the first paint.
 */

import { useEffect, useState } from 'react';

import { Icon } from '@/shared/ui';

import type { ThemeChoice } from './theme';
import {

  THEME_LABELS,
  applyThemeChoice,
  readThemeChoice,
  themeStorage,
  writeThemeChoice,
} from './theme';

export function ThemeToggle() {
  const [choice, setChoice] = useState<ThemeChoice>('system');

  useEffect(() => {
    const stored = readThemeChoice(themeStorage());
    setChoice(stored);
    applyThemeChoice(document.documentElement, stored);
  }, []);

  const pick = (next: ThemeChoice): void => {
    setChoice(next);
    writeThemeChoice(themeStorage(), next);
    applyThemeChoice(document.documentElement, next);
  };

  return (
    <div className="am-theme" role="group" aria-label="Оформление">
      {/*
        * TWO buttons, sun and moon, asked for by the owner 2026-09-22.
        *
        * `THEME_CHOICES` still has three members and `system` is still the default: it is the
        * state you are in until you press one of these, `readThemeChoice` returns it, and the
        * OS preference is honoured the whole time. What it no longer is, is a BUTTON.
        *
        * THE CONSEQUENCE, NAMED RATHER THAN DISCOVERED: once a reviewer picks light or dark,
        * there is no way back to "follow the system" from the interface. That is the cost of
        * two controls instead of three and it is the owner's call; reversing it is one entry
        * in the array below.
        *
        * Icon-only, so each carries an `aria-label`. Those labels are Russian and the
        * rendered-language guard reads `aria-label`, so this cannot silently become English.
        */}
      {(['light', 'dark'] as const).map((value) => (
        <button
          key={value}
          type="button"
          className="am-theme__option"
          /*
           * The machine value, kept beside the icon. The browser journey and the PA-01
           * criterion-4 evidence select on this attribute, so the wording is free to change.
           */
          data-theme-choice={value}
          aria-pressed={value === choice}
          aria-label={THEME_LABELS[value]}
          title={THEME_LABELS[value]}
          onClick={() => pick(value)}
        >
          <Icon name={value} />
        </button>
      ))}
    </div>
  );
}
