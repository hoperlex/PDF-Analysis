/**
 * Every icon in the set is still, exactly, the Feather icon the notice says it is.
 *
 * `D-52` is a **provenance** row, not a styling one: the legacy tree pasted Feather's work
 * and shipped no licence, and `web/NOTICE` exists to stop this tree repeating that. A
 * notice naming sixteen Feather files is a statement about what the code contains, and a
 * statement about code goes stale the moment somebody nudges a path. Then the notice is
 * not merely out of date -- it is **wrong about what was copied**, which is the failure
 * mode `D-52` was opened over.
 *
 * So this compares what `Icon` renders against `icon-feather-source.ts`, which holds
 * Feather's own documents as they were fetched. Two differences are tolerated and both are
 * serialisation, not geometry: React writes `<path …></path>` where Feather's files write
 * `<path …/>`, and the fetched files carry no newlines inside an element but this one's
 * formatter wraps long attribute lists. Nothing else is normalised -- every coordinate,
 * every command letter and every attribute order has to match.
 *
 * Note what this does **not** check: that Feather upstream still publishes these bytes.
 * That is not this repository's business. What was copied is fixed; the obligation is to
 * name it correctly.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { IconName } from '@/shared/ui';
import { FEATHER_SOURCE, ICON_NAMES, Icon } from '@/shared/ui';

import { FEATHER_SVG } from './icon-feather-source';

/** The children of an `<svg>`, with React's and Feather's serialisations reconciled. */
function geometry(document: string): string {
  return document
    .replace(/^<svg[^>]*>/, '')
    .replace(/<\/svg>\s*$/, '')
    // React closes an empty element with a closing tag; Feather self-closes it.
    .replace(/>\s*<\/(?:path|line|polyline|polygon|circle|rect|ellipse)>/g, '/>')
    .replace(/\s+/g, ' ')
    .replace(/\s*\/>/g, '/>')
    .trim();
}

function rendered(name: IconName): string {
  return geometry(renderToStaticMarkup(createElement(Icon, { name })));
}

describe('the geometry is Feather’s, unchanged', () => {
  it.each(ICON_NAMES)('%s is Feather’s icon of the name the notice gives', (name) => {
    const source = FEATHER_SVG[FEATHER_SOURCE[name]];
    expect(source, `no frozen source for ${FEATHER_SOURCE[name]}`).toBeDefined();
    expect(rendered(name)).toBe(geometry(source as string));
  });

  it('froze one source document per icon and no orphans', () => {
    expect(Object.keys(FEATHER_SVG).sort()).toEqual(
      [...new Set(ICON_NAMES.map((name) => FEATHER_SOURCE[name]))].sort(),
    );
  });

  // The comparison, shown failing. A one-unit nudge to a single coordinate is the smallest
  // edit that makes the notice wrong, and it is exactly what a "just tidy the path" commit
  // looks like.
  it('fails on a single moved coordinate', () => {
    const moved = geometry(FEATHER_SVG['check'] as string).replace('20 6', '20 7');
    expect(moved).not.toBe(rendered('accept'));
  });

  it('fails when an icon is compared with the wrong Feather file', () => {
    expect(rendered('accept')).not.toBe(geometry(FEATHER_SVG['x'] as string));
  });

  /**
   * Feather's own files carry the convention on the root element, which is where
   * `shared/ui/icon.tsx` puts it too. If that ever stops being true of the source, the
   * component's single set of root attributes stops being a faithful packaging of it.
   */
  it('confirms the root attributes the component reproduces', () => {
    for (const [name, document] of Object.entries(FEATHER_SVG)) {
      const root = /<svg[^>]*>/.exec(document)?.[0] ?? '';
      expect(root, name).toContain('viewBox="0 0 24 24"');
      expect(root, name).toContain('fill="none"');
      expect(root, name).toContain('stroke="currentColor"');
      expect(root, name).toContain('stroke-width="2"');
      expect(root, name).toContain('stroke-linecap="round"');
      expect(root, name).toContain('stroke-linejoin="round"');
    }
  });
});
