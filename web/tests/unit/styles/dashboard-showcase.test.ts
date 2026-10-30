import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { DARK_MEDIA_SELECTOR, DARK_SELECTOR, contrastRatio, parseTokens, parseTokensIn } from './contrast';

const WEB = fileURLToPath(new URL('../../..', import.meta.url));
const CSS = readFileSync(join(WEB, 'src', 'app', 'globals.css'), 'utf8');
const TOKEN_NAMES = [
  '--am-showcase-bg',
  '--am-showcase-card',
  '--am-showcase-card-alt',
  '--am-showcase-ink',
  '--am-showcase-muted',
  '--am-showcase-soft',
  '--am-showcase-line',
  '--am-showcase-accent',
  '--am-showcase-accent-strong',
  '--am-showcase-accent-soft',
] as const;

describe('the dashboard showcase uses one complete palette for each appearance', () => {
  const light = parseTokens(CSS);
  const dark = parseTokensIn(CSS, DARK_SELECTOR);
  const systemDark = parseTokensIn(CSS, DARK_MEDIA_SELECTOR);

  it('defines every showcase colour in both appearances and matches system dark to explicit dark', () => {
    for (const name of TOKEN_NAMES) {
      expect(light.get(name), `${name} missing in light`).toMatch(/^#[0-9a-f]{6}$/i);
      expect(dark.get(name), `${name} missing in dark`).toMatch(/^#[0-9a-f]{6}$/i);
      expect(systemDark.get(name), `${name} differs under system dark`).toBe(dark.get(name));
    }
  });

  it.each([
    ['light', light],
    ['dark', dark],
  ] as const)('%s has readable text, accents and visible card borders', (_appearance, palette) => {
    const colour = (name: (typeof TOKEN_NAMES)[number]): string => {
      const value = palette.get(name);
      if (value === undefined) throw new Error(`Missing ${name}`);
      return value;
    };
    for (const surface of ['--am-showcase-card', '--am-showcase-card-alt'] as const) {
      for (const ink of ['--am-showcase-ink', '--am-showcase-muted', '--am-showcase-soft'] as const) {
        expect(contrastRatio(colour(ink), colour(surface)), `${ink} on ${surface}`).toBeGreaterThanOrEqual(4.5);
      }
    }
    expect(contrastRatio(colour('--am-showcase-accent'), colour('--am-showcase-card'))).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colour('--am-showcase-accent-strong'), colour('--am-showcase-accent-soft'))).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colour('--am-showcase-line'), colour('--am-showcase-card'))).toBeGreaterThanOrEqual(3);
  });
});
