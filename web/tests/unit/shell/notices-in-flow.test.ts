/**
 * The release notices stand in the page's flow and never over it (lane D5, 2026-11-07).
 *
 * The «Что нового» card was `position: fixed` at the lower left of every screen, 448 px wide and up to 70 % of the
 * viewport high. On a 1280x720 screen it covered about 450 px of the left column, and a browser press under it landed
 * on the card instead of the control. The notices are strips at the top of `<main>` now; this keeps them there:
 * the stylesheet takes no element out of the flow, and the frame renders the gate inside `<main>`, before the screen.
 */

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const read = (relative: string) => readFileSync(new URL(relative, import.meta.url), 'utf8');

/** Declarations of `position` that take an element out of the flow, with the rule's selector. */
export function outOfFlowRules(css: string): readonly string[] {
  const bare = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const found: string[] = [];
  for (const match of bare.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (/(^|[;\s])position\s*:\s*(fixed|absolute|sticky)\b/.test(match[2] as string)) found.push((match[1] as string).trim());
  }
  return found;
}

/** Whether the gate is rendered between `<main` and `</main>` in the frame's source. */
export function gateInsideMain(source: string): boolean {
  const open = source.indexOf('<main');
  const close = source.indexOf('</main>');
  const gate = source.indexOf('<ReleaseNoticesGate');
  return open !== -1 && close !== -1 && gate > open && gate < close;
}

describe('the release notices are strips in the flow', () => {
  it('can fail: sees a fixed card and a gate outside <main>', () => {
    expect(outOfFlowRules('.card { position: fixed; left: 20px; }\n.ok { display: flex; }')).toEqual(['.card']);
    expect(outOfFlowRules('/* position: fixed */ .a { top: 0; }')).toEqual([]);
    expect(gateInsideMain('<main>{children}</main>\n<ReleaseNoticesGate />')).toBe(false);
    expect(gateInsideMain('<main><ReleaseNoticesGate />{children}</main>')).toBe(true);
  });

  it('takes no notice out of the flow in the stylesheet', () => {
    expect(outOfFlowRules(read('../../../src/_app/release-notices.module.css'))).toEqual([]);
  });

  it('renders the gate inside <main>, above the screen', () => {
    expect(gateInsideMain(read('../../../src/_app/app-frame.tsx'))).toBe(true);
  });
});
