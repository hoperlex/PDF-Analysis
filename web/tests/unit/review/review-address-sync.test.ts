/**
 * The «Разбор» filters, the list/table switch and the chosen finding live in the address (`?verdict=`, `?severity=`,
 * `?view=`, `?finding=`) and the page READS them back through `useSearchParams`. Next patches `history.pushState` and
 * `history.replaceState` so that `useSearchParams` follows a write — but the patch passes a call straight through, with no
 * sync, when its first argument carries Next's own marker (`__NA` / `_N`), and `window.history.state` always does. A page
 * that wrote its address with `replaceState(window.history.state, …)` therefore changed the URL bar and nothing else: the
 * pressed button stayed pressed, the table never came, and the next write rebuilt the query from the stale parameters
 * (browser journey on a throwaway stand, 2026-11-07: `?view=table` then `?verdict=rejected` replaced it, both buttons
 * unchanged). Static rendering cannot see this — it has no history and no patch.
 *
 * The cure is the documented form: `null` as the data, as `workers`, `logs`, `work-schedule` and `section-optimisation` write.
 * The same writer in `version-compare` and `stage-compare` is reported in `DEBT_REGISTER.md` (D-338), not changed here.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';

const SOURCE = readFileSync(join(WEB_ROOT, 'src/_pages/review/ui/review-page.tsx'), 'utf8');

describe('«Разбор» writes its address in a form Next syncs to useSearchParams', () => {
  it('never hands window.history.state to pushState or replaceState', () => {
    expect(SOURCE).not.toMatch(/history\.(push|replace)State\(\s*(window\.)?history\.state/);
  });

  it('writes with null as the data', () => {
    expect(SOURCE).toMatch(/history\.replaceState\(\s*null\s*,/);
  });
});
