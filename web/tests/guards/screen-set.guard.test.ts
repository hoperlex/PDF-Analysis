/**
 * `D-88`: the set of screens is derived from the route tree, and every address is either
 * rendered by both instruments or excused by a claim this file runs.
 *
 * ## What was here before, and what it cost
 *
 * `rendered-language.guard.test.ts:795` was `const SCREENS = [...]` and
 * `tests/unit/styles/screens.ts` was a hand-written import list. Neither read
 * `web/src/app`. `W43-PREP` added four screens, `W43-JUDGE-A` put a different English
 * sentence on each of them, and **the whole frontend suite stayed green — 73 files, 1047
 * tests, 0 failed.** The one instrument that caught all four is not a frontend instrument:
 * `tests/e2e/test_pc01_journey_conformance.py` derives its subject with `rglob("page.tsx")`
 * and named every one of them unprompted.
 *
 * That contrast is the row, and this file is the frontend side of it.
 *
 * ## Why the derivation lives in `tests/unit/screens/route-screens.ts` and the assertions here
 *
 * Both instruments consume the derivation, and an instrument that asserted its own
 * coverage from its own list is exactly the shape `OPERATING_CONSTRAINTS.md` §12 names —
 * `contrast.test.ts` carried a list of eighteen component names checked against
 * `screens.ts`'s list of eighteen component names, and three screens a reviewer meets were
 * outside both. The question is asked here, of the filesystem, once.
 *
 * ## What this file does NOT do
 *
 * It does not assert that any screen is correct. It asserts that every screen the product
 * offers is **reached** by the instruments that judge correctness. An unreached screen
 * makes every one of their assertions vacuous, which is the only failure mode `D-88` has
 * ever had.
 */

import { describe, expect, it } from 'vitest';

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import {
  MALFORMED_SEGMENT,
  SEEDS,
  derivedScreens,
  malformedVariants,
  optOuts,
  routeAddresses,
  staleSeeds,
  undisciplinedSegments,
  wellFormed,
} from '../unit/screens/route-screens';

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const IDENTITIES = {
  projectUid: `prj_${ULID}`,
  documentUid: `doc_${ULID}`,
  versionUid: `ver_${ULID}`,
  runId: `run_${ULID}`,
};

function stubRouter(): AppRouterInstance {
  return {
    push: () => {}, replace: () => {}, back: () => {}, forward: () => {},
    refresh: () => {}, prefetch: () => {},
  } as unknown as AppRouterInstance;
}

/**
 * One cold pass over a screen. No `try`, deliberately: a screen that throws is a defect
 * and must reach the reader as a thrown error naming the case, not as an absence.
 */
function renderCold(element: ReactElement): string {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnMount: false, retryOnMount: false } },
  });
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client },
      createElement(AppRouterContext.Provider, { value: stubRouter() }, element),
    ),
  );
}

describe('the set of screens is read off web/src/app, not out of a list', () => {
  it('finds the route tree at all, and finds dynamic segments in it', () => {
    const routes = routeAddresses();
    // Anti-vacuity in both directions: a walk that found nothing would satisfy every
    // assertion below by having no work to do, and a walk that found only static
    // addresses would silently drop the half of the tree `D-90` lives in.
    expect(routes.length, 'no page.tsx was found under web/src/app at all').toBeGreaterThan(10);
    expect(
      routes.filter((route) => route.segments.length > 0).length,
      'no dynamic segment was parsed; the derivation has stopped reading the layout',
    ).toBeGreaterThan(4);
    expect(routes.map((route) => route.address)).toContain('/projects/[project_uid]');
    // Every address resolves to a file that exists, so the derivation is the tree and not
    // a transformation of it that happens to look like one.
    expect(routes.filter((route) => !route.file.endsWith('/page.tsx'))).toEqual([]);
    expect(new Set(routes.map((route) => route.address)).size).toBe(routes.length);
  });

  it('has a seed for every address, and names the ones it does not', () => {
    const addresses = routeAddresses().map((route) => route.address);
    const seeded = new Set(SEEDS.map((seed) => seed.address));
    expect(
      addresses.filter((address) => !seeded.has(address)).sort(),
      'web/src/app serves these addresses and `SEEDS` in tests/unit/screens/route-screens.ts ' +
        'answers for none of them, so NO frontend instrument renders them: not the language ' +
        'guard, not the contrast census. Add a seed saying how the screen is rendered, or an ' +
        '`optOut` saying — with a proof this guard runs — why it renders nothing at all. ' +
        'A try/catch around the render is not an opt-out.',
    ).toEqual([]);
  });

  it('has no seed for an address the tree no longer offers', () => {
    expect(
      [...staleSeeds()].sort(),
      'these seeds name an address `web/src/app` does not serve. A ratchet that keeps a ' +
        'seed for a deleted screen goes back to proving nothing.',
    ).toEqual([]);
  });

  it('runs every opt-out claim against the route file it is about', () => {
    const excused = optOuts();
    // There is exactly one today and the number is not the assertion; that each one is
    // CHECKED is. An opt-out nobody re-runs is a comment.
    expect(excused.length, 'the opt-out list is empty; this case has stopped measuring').toBe(1);
    expect(
      excused.filter((entry) => !entry.holds).map((entry) => entry.address),
      'this address is excused from both instruments and the proof its entry carries no ' +
        'longer holds against its route file. Either the screen now renders something — in ' +
        'which case seed it — or the reason has to be rewritten to say what is true now.',
    ).toEqual([]);
    for (const { address, why } of excused) {
      expect(why.length, `${address} is excused and carries no reason a reader can act on`)
        .toBeGreaterThan(80);
    }
  });

  it('every derived screen renders real markup, and none of them throws', () => {
    const screens = derivedScreens();
    expect(screens.length, 'the derived set renders nothing').toBeGreaterThan(10);
    // A relationship, never a literal: the count is `every address minus the excused`.
    expect(screens.length).toBe(routeAddresses().length - optOuts().length);
    for (const screen of screens) {
      const markup = renderCold(screen.make(wellFormed(IDENTITIES)));
      expect(markup.length, `${screen.name} (${screen.address}) rendered nothing`)
        .toBeGreaterThan(100);
    }
    expect(new Set(screens.map((s) => s.name)).size).toBe(screens.length);
  });
});

/**
 * `D-90`: what a screen does with a malformed segment of its own, asserted per segment.
 *
 * The pairs are derived from the directory layout — a new `[segment]` brings its own pair
 * and no seed can forget it — and the **expected** behaviour is the human's answer in
 * `SEEDS`. That split is the whole point. A guard that recovered the expectation by
 * scanning the component for `looksLike…(` would go green on the mutation this exists to
 * catch, because deleting the call deletes the scan's evidence with it.
 *
 * The naive mutation — delete the `looksLikeProjectUid` call — dies at `tsc` for an unused
 * import, and that red is about the import and says nothing about the condition. The
 * mutation this case answers is the one the register records: keep the import used, drop
 * only the branch.
 */
describe('D-90: every dynamic segment says what its screen does with a malformed value', () => {
  it('answers for every segment the tree has, and for no segment it does not', () => {
    expect(
      [...undisciplinedSegments()].sort(),
      'a seed and its address disagree about which dynamic segments exist',
    ).toEqual([]);
  });

  const variants = malformedVariants(IDENTITIES);

  it('finds the (screen, segment) pairs by deriving them, not by listing them', () => {
    expect(variants.length, 'no dynamic segment produced a variant').toBeGreaterThan(8);
    expect(
      variants.filter((v) => v.expected === 'refuses').length,
      'no screen is expected to refuse anything; the answers have gone uniform',
    ).toBeGreaterThan(4);
    expect(
      variants.filter((v) => v.expected === 'defers-to-route').length,
      'no screen is expected to defer; the answers have gone uniform the other way',
    ).toBeGreaterThan(1);
  });

  it('refuses exactly the segments the seeds say it refuses, and renders the rest', () => {
    /*
     * `UnsupportedState` is the tone that says no retry will help, and it is what every
     * refusing screen renders. The class is read from the markup rather than the sentence,
     * because the sentence is prose that `rendered-language.guard.test.ts` judges and a
     * check reading it would share an assumption with the thing it measures.
     */
    const WARNING = 'am-state--warning';
    const wrong = variants
      .map((variant) => {
        const refused = renderCold(variant.make()).includes(WARNING);
        const expected = variant.expected === 'refuses';
        return refused === expected ? null : `${variant.name}: seed says ${variant.expected}`;
      })
      .filter((entry): entry is string => entry !== null)
      .sort();
    expect(
      wrong,
      'a screen and its seed disagree about what the screen does with a malformed segment. ' +
        'Either a live condition was removed from the component — which is `D-90` — or a ' +
        'condition was added without a decision. Both are changes somebody has to make ' +
        'deliberately, which is why the answer lives in `SEEDS` and not in a scan of the ' +
        'component.',
    ).toEqual([]);
  });

  it('is about the segment and not about the harness: a well-formed pass refuses nothing', () => {
    // Anti-vacuity, and the one this case needs most. If every cold render carried
    // `am-state--warning` for some unrelated reason, the `refuses` half above would pass
    // for the wrong reason and keep passing.
    const refusingScreens = new Set(
      variants.filter((v) => v.expected === 'refuses').map((v) => v.address),
    );
    for (const screen of derivedScreens()) {
      if (!refusingScreens.has(screen.address)) continue;
      const markup = renderCold(screen.make(wellFormed(IDENTITIES)));
      expect(
        markup.includes('am-state--warning'),
        `${screen.name} refuses a well-formed address, so its refusal proves nothing`,
      ).toBe(false);
    }
    // And the malformed value really is malformed by the product's own rule.
    expect(MALFORMED_SEGMENT).not.toMatch(/^(prj|doc|ver|run)_[0-9A-HJKMNP-TV-Z]{26}$/);
  });
});
