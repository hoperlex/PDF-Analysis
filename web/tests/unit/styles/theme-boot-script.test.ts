/**
 * `P7-1` — the stored light/dark choice reaches `<html data-theme>` before the first paint.
 *
 * `ThemeToggle` reads the choice in an effect, after hydration, so a visitor whose choice
 * differs from their system's saw one frame of the wrong theme. The root layout now carries a
 * blocking inline script (`shared/lib/theme-boot-script.ts`) that does the same read and the
 * same write earlier. Four things are held here, because each can drift without a visible
 * symptom in a unit run:
 *
 *   1. **The script is the module's own behaviour, earlier.** Its generated source is run
 *      against a fake `window`/`document` for every stored value and compared with
 *      `readThemeChoice` + `applyThemeChoice` on a document that starts without the attribute.
 *   2. **It cannot fail the page.** A storage that throws, a missing storage and a missing
 *      `window` end quietly with no attribute — the system preference decides, which is the
 *      module's documented answer for "no stored choice".
 *   3. **Nothing in the input can leave the script**: a key with a quote or `</script>` in it
 *      stays inside its literal and never closes the element. And the script never writes.
 *   4. **The layout is the only place that carries it**, and `suppressHydrationWarning` is on
 *      `<html>` alone: the `D-329` rule (no server markup the client disagrees with) is not
 *      loosened anywhere inside `<body>`. Screens are rendered without the root layout, so
 *      neither the rendered-language guard nor the styling census ever sees the script.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it, vi } from 'vitest';

import type { ThemeStorage } from '@/_app';
import {
  AppFrame,
  AppProviders,
  THEME_ATTRIBUTE,
  THEME_CHOICES,
  THEME_STORAGE_KEY,
  applyThemeChoice,
  readThemeChoice,
} from '@/_app';
import { themeBootScript } from '@/shared/lib/theme-boot-script';

import { WEB_ROOT, walkFiles } from '../../guards/lib/repo';

vi.mock('next/headers', () => ({ cookies: async () => ({ get: () => undefined }) }));

const { default: RootLayout } = await import('@/app/layout');

const SOURCE = themeBootScript({
  storageKey: THEME_STORAGE_KEY,
  attribute: THEME_ATTRIBUTE,
  choices: THEME_CHOICES,
});

/** A document element that remembers its attributes, and starts with none. */
function fakeRoot(): { attributes: Map<string, string>; setAttribute: (n: string, v: string) => void; removeAttribute: (n: string) => void } {
  const attributes = new Map<string, string>();
  return {
    attributes,
    setAttribute: (name, value) => void attributes.set(name, value),
    removeAttribute: (name) => void attributes.delete(name),
  };
}

function runScript(source: string, win: unknown): Map<string, string> {
  const root = fakeRoot();
  new Function('window', 'document', source)(win, { documentElement: root });
  return root.attributes;
}

function storageHolding(value: string | null): ThemeStorage {
  return { getItem: () => value, setItem: () => undefined };
}

describe('the script does what ThemeToggle does, before paint', () => {
  const STORED: readonly (string | null)[] = ['light', 'dark', 'system', 'blue', 'LIGHT', '', ' dark', null];

  for (const stored of STORED) {
    it(`stored ${JSON.stringify(stored)}: the same attribute as readThemeChoice + applyThemeChoice`, () => {
      const viaScript = runScript(SOURCE, { localStorage: storageHolding(stored) });
      const root = fakeRoot();
      applyThemeChoice(root, readThemeChoice(storageHolding(stored)));
      expect([...viaScript]).toEqual([...root.attributes]);
    });
  }

  it('writes the choice under the attribute and key the component uses, and for light and dark only', () => {
    expect([...runScript(SOURCE, { localStorage: storageHolding('dark') })]).toEqual([[THEME_ATTRIBUTE, 'dark']]);
    expect([...runScript(SOURCE, { localStorage: storageHolding('light') })]).toEqual([[THEME_ATTRIBUTE, 'light']]);
    expect(THEME_CHOICES.filter((choice) => runScript(SOURCE, { localStorage: storageHolding(choice) }).size > 0)).toEqual([
      'light',
      'dark',
    ]);
    const asked: string[] = [];
    runScript(SOURCE, { localStorage: { getItem: (key: string) => (asked.push(key), null) } });
    expect(asked).toEqual([THEME_STORAGE_KEY]);
  });

  it('is not vacuous: a script with the wrong key reads nothing and applies nothing', () => {
    const wrong = themeBootScript({ storageKey: 'other-key', attribute: THEME_ATTRIBUTE, choices: THEME_CHOICES });
    const win = { localStorage: { getItem: (key: string) => (key === THEME_STORAGE_KEY ? 'dark' : null) } };
    expect(runScript(SOURCE, win).size).toBe(1);
    expect(runScript(wrong, win).size).toBe(0);
  });
});

describe('the script never fails the page', () => {
  it('ends with no attribute when storage throws on read', () => {
    const throwing = { localStorage: { getItem: () => { throw new Error('SecurityError'); } } };
    expect(() => runScript(SOURCE, throwing)).not.toThrow();
    expect(runScript(SOURCE, throwing).size).toBe(0);
  });

  it('ends with no attribute when reaching storage throws, or there is none', () => {
    const refusing = {
      get localStorage(): never {
        throw new Error('SecurityError');
      },
    };
    expect(runScript(SOURCE, refusing).size).toBe(0);
    expect(runScript(SOURCE, {}).size).toBe(0);
    expect(runScript(SOURCE, undefined).size).toBe(0);
  });

  it('reads and never writes', () => {
    expect(SOURCE).not.toMatch(/setItem|removeItem|clear\(|document\.cookie|fetch|XMLHttpRequest/);
    expect(SOURCE).not.toContain('removeAttribute');
  });
});

describe('nothing in the input leaves the script', () => {
  const hostile = themeBootScript({
    storageKey: `k"</script><script>alert(1)//`,
    attribute: `data-x"+(1)+"`,
    choices: ['dark', `a</script>b`],
  });

  it('writes no `<` at all, so no input can close the element', () => {
    expect(hostile).not.toContain('<');
    expect(hostile).not.toMatch(/<\/script/i);
    expect(SOURCE).not.toContain('<');
  });

  it('keeps a quote inside its literal: the generated source still parses and reads the whole key', () => {
    const asked: string[] = [];
    runScript(hostile, { localStorage: { getItem: (key: string) => (asked.push(key), 'dark') } });
    expect(asked).toEqual([`k"</script><script>alert(1)//`]);
    const root = runScript(hostile, { localStorage: { getItem: () => 'dark' } });
    expect([...root]).toEqual([[`data-x"+(1)+"`, 'dark']]);
  });
});

describe('the root layout carries the script, and the flag is on <html> only', () => {
  it('puts the exact script in <head>, before the body, and marks <html> alone', async () => {
    const html = await RootLayout({ children: 'screen' });
    expect(html.type).toBe('html');
    expect(html.props.suppressHydrationWarning).toBe(true);

    const [head, body] = html.props.children as [
      { type: unknown; props: { children: { type: unknown; props: { dangerouslySetInnerHTML: { __html: string } } } } },
      { type: unknown; props: Record<string, unknown> },
    ];
    expect(head.type).toBe('head');
    expect(head.props.children.type).toBe('script');
    expect(head.props.children.props.dangerouslySetInnerHTML.__html).toBe(SOURCE);
    expect(body.type).toBe('body');
    expect(body.props.suppressHydrationWarning).toBeUndefined();
  });

  it('nests provider, frame and screen as before: the script changed nothing below <body>', async () => {
    const html = await RootLayout({ children: 'screen' });
    const [, body] = html.props.children as [unknown, { props: { children: { type: unknown; props: { children: { type: unknown; props: { children: unknown } } } } } }];
    expect(body.props.children.type).toBe(AppProviders);
    expect(body.props.children.props.children.type).toBe(AppFrame);
    expect(body.props.children.props.children.props.children).toBe('screen');
  });

  const SRC = join(WEB_ROOT, 'src');
  const sources = walkFiles(SRC, (path) => /\.(ts|tsx)$/.test(path));

  /** Code only: the comments that explain a rule are not a use of it. */
  const code = (file: string): string =>
    readFileSync(file, 'utf8').replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');

  it('has exactly one inline script and one suppressHydrationWarning in the whole tree: the root layout', () => {
    const inline = sources.filter((file) => /dangerouslySetInnerHTML\s*=/.test(code(file)));
    const suppressed = sources.filter((file) => /suppressHydrationWarning/.test(code(file)));
    const layout = join(SRC, 'app', 'layout.tsx');
    expect(inline).toEqual([layout]);
    expect(suppressed).toEqual([layout]);
    // On the one element, and not as a blanket: the attribute appears once in the layout.
    expect(code(layout).match(/suppressHydrationWarning/g)).toHaveLength(1);
    expect(code(layout)).toMatch(/<html[^>]*suppressHydrationWarning/);
  });

  it('is imported by the root layout alone, so no screen\'s markup can contain it', () => {
    const users = sources.filter((file) => /themeBootScript/.test(code(file)) && !file.endsWith('theme-boot-script.ts') && !file.endsWith(join('shared', 'lib', 'index.ts')));
    expect(users).toEqual([join(SRC, 'app', 'layout.tsx')]);
  });
});
