/**
 * Guard: an address the browser loads is built in the transport seam, and a widget is handed
 * identities, never an address (`W55B-FIX`, `W55B-JUDGE-Y` Y-2).
 *
 * `web/docs/PC01_UI_SEAM.md` §4: a slice never constructs a URL; §3.4: a widget does not take
 * one. The portal crop's address was built in `entities/block` and handed to the «Блоки»
 * widgets as a `cropSrc` callback; it now lives in `src/shared/api/crop-address.ts` and the
 * widgets take the version's identity. Two rules, scanned over the real tree and over
 * fixtures that break each, so the guard is shown to fire:
 *
 *   base-url    the configured API base is read (`getApiBaseUrl(`) only in `src/shared/`;
 *   url-prop    the «Блоки» widget declares no prop whose name ends in `Src` or `Url`.
 *
 * `url-prop` is scoped to `widgets/portal-blocks`, the widget Y-2 named. Two other widgets
 * take a `documentUrl` (an object URL of a `Blob` the generated client read, not an API
 * address); they predate this wave and are outside its repair.
 */

import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { WEB_ROOT, readText, repoRelative, walkFiles } from './lib/repo';

interface Source {
  readonly path: string;
  readonly text: string;
}

const SRC = join(WEB_ROOT, 'src');

function violations(sources: readonly Source[]): string[] {
  const found: string[] = [];
  for (const { path, text } of sources) {
    if (!path.startsWith('web/src/shared/') && /\bgetApiBaseUrl\(/.test(text)) {
      found.push(`${path}: base-url`);
    }
    if (path.startsWith('web/src/widgets/portal-blocks/')) {
      for (const match of text.matchAll(/^\s*readonly\s+([A-Za-z]+(?:Src|Url))\??\s*:/gm)) {
        found.push(`${path}: url-prop ${match[1] ?? ''}`);
      }
    }
  }
  return found;
}

const tree: Source[] = walkFiles(SRC, (p) => /\.(ts|tsx)$/.test(p)).map((path) => ({
  path: repoRelative(path),
  text: readText(path),
}));

describe('addresses are the seam’s', () => {
  it('scans the tree, including the seam and the «Блоки» widget', () => {
    const paths = tree.map((source) => source.path);
    expect(paths).toContain('web/src/shared/api/crop-address.ts');
    expect(paths).toContain('web/src/widgets/portal-blocks/ui/portal-block-card.tsx');
    expect(paths).not.toContain('web/src/entities/block/api/crop-url.ts');
  });

  it('finds no slice reading the base and no widget taking an address', () => {
    expect(violations(tree)).toEqual([]);
  });

  it('goes red on each rule', () => {
    expect(
      violations([
        { path: 'web/src/entities/block/api/crop-url.ts', text: 'return `${getApiBaseUrl()}${path}`;' },
        { path: 'web/src/widgets/portal-blocks/ui/x.tsx', text: '  readonly cropSrc: (b: B) => string;' },
        { path: 'web/src/widgets/portal-blocks/ui/y.tsx', text: '  readonly imageUrl?: string;' },
      ]),
    ).toEqual([
      'web/src/entities/block/api/crop-url.ts: base-url',
      'web/src/widgets/portal-blocks/ui/x.tsx: url-prop cropSrc',
      'web/src/widgets/portal-blocks/ui/y.tsx: url-prop imageUrl',
    ]);
  });
});
