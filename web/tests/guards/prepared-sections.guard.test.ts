/**
 * The four sections `R-23`'s addendum ruled prepared, held to the four rules it set.
 *
 * `OWNER_RULINGS_2026-09-17.md` §3.11 says preparation is four things and no more: a
 * place in the navigation, a `RoutePlaceholder` carrying a real `promise`, the data shape
 * written down and checked against the contract, and **no invented numbers**. The third
 * is prose and lives in `docs/program/W43-PREP.md`; the other three are properties of
 * rendered markup, and this file is what makes them fail when they stop holding.
 *
 * ## Why each check renders rather than reads source
 *
 * `D-53` is the standing reason: three sessions reported the interface translated by
 * scanning source, and three were wrong, because the string a reviewer reads does not
 * exist until React composes it. The same applies to a placeholder's wording — `promise`
 * is a *prop*, the default sentence lives in the component, and which of the two a screen
 * shows is a fact about the render. So every assertion below is taken from markup.
 *
 * ## What each check can be wrong about, and the mutation that proves it can fail
 *
 * Each check is a pure function over strings, exercised twice: once against a deliberately
 * broken input, which is what proves it *can* go red, and once against this tree, which is
 * what proves it is wired to the application rather than to a fixture. That shape is
 * `styling-layer.test.ts`'s and it is copied on purpose — a guard added with a screen and
 * never shown to fail is the thing seven consecutive waves were spent learning about.
 *
 * ## What this file deliberately does NOT do
 *
 * It does not add these four screens to `rendered-language.guard.test.ts`'s `SCREENS` or
 * to `tests/unit/styles/screens.ts`. Wave 43 is the first wave to add a screen since wave
 * 41 repaired the language guard's coverage and wave 42 widened the contrast census, and
 * `W43-PLAN.md` puts the question *"do the instruments reach the new screens"* to the
 * judge precisely because a stream that seeds its own screens into a coverage instrument
 * destroys the measurement. Which instruments reach these screens untold is reported, not
 * arranged.
 */

import { createElement } from 'react';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';

import { renderToStaticMarkup } from 'react-dom/server';
import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

import { AppFrame } from '@/_app';
import { BlocksPage } from '@/_pages/blocks';
import { LogsPage } from '@/_pages/logs';
import { OptimisationPage } from '@/_pages/optimisation';
import { WorkersPage } from '@/_pages/workers';
import { RoutePlaceholder } from '@/shared/ui';
import BlocksRoute from '@/app/blocks/page';
import LogsRoute from '@/app/logs/page';
import OptimisationRoute from '@/app/optimisation/page';
import WorkersRoute from '@/app/workers/page';

// ------------------------------------------------------------------ rendering machinery

function stubRouter(): AppRouterInstance {
  return {
    push: () => {}, replace: () => {}, back: () => {}, forward: () => {},
    refresh: () => {}, prefetch: () => {},
  } as unknown as AppRouterInstance;
}

/** `next/link` reads the router from context even on a server pass. */
function render(element: ReactElement): string {
  return renderToStaticMarkup(
    createElement(AppRouterContext.Provider, { value: stubRouter() }, element),
  );
}

/**
 * The text nodes a reviewer would read off this markup.
 *
 * Attributes are excluded on purpose and it is the difference between this check and a
 * grep: `data-route="/blocks"` is machinery a developer reads in the DOM, and a rule about
 * what a *reviewer* is shown must not judge it.
 */
export function visibleText(markup: string): string[] {
  const out: string[] = [];
  for (const match of markup.matchAll(/>([^<>]+)</g)) {
    const text = (match[1] ?? '')
      .replace(/&#x([0-9a-fA-F]+);/g, (_, h: string) => String.fromCharCode(parseInt(h, 16)))
      .replace(/&#(\d+);/g, (_, d: string) => String.fromCharCode(Number(d)))
      .replace(/&amp;/g, '&')
      .trim();
    if (text.length > 0) out.push(text);
  }
  return out;
}

// ------------------------------------------------------------------------- the subjects

const SECTIONS = [
  { name: 'blocks', route: '/blocks', title: 'Блоки', screen: BlocksPage, routeFile: BlocksRoute },
  {
    name: 'optimisation',
    route: '/optimisation',
    title: 'Оптимизация',
    screen: OptimisationPage,
    routeFile: OptimisationRoute,
  },
  { name: 'logs', route: '/logs', title: 'Журнал выполнения', screen: LogsPage, routeFile: LogsRoute },
  {
    name: 'workers',
    route: '/workers',
    title: 'Исполнители',
    screen: WorkersPage,
    routeFile: WorkersRoute,
  },
] as const;

/**
 * The generic sentence the component falls back to, taken from the component itself.
 *
 * Read by rendering rather than by importing a constant or matching the source, because
 * `OPERATING_CONSTRAINTS.md` §12 is about a query that shares an assumption with its
 * subject: a test that imported the default would keep passing if the default and all
 * four promises were changed to the same new string.
 */
const GENERIC = longest(
  visibleText(render(createElement(RoutePlaceholder, { screen: 'x', route: '/x' }))),
);

/**
 * The longest visible string on a `RoutePlaceholder`, which is its promise.
 *
 * The screen's other strings are the title, the fixed subtitle and the fixed headline,
 * and all three are shorter than a sentence about what will be here -- which the
 * pairwise-distinctness case below re-asserts as a floor rather than assuming.
 */
export function longest(strings: readonly string[]): string {
  return strings.reduce((a, b) => (b.length > a.length ? b : a), '');
}

// -------------------------------------------------------------- 1. no invented numbers

/** Every visible string carrying a digit. `R-23`: an empty screen beats a plausible one. */
export function withDigits(strings: readonly string[]): string[] {
  return strings.filter((s) => /\d/.test(s));
}

describe('R-23: no invented number reaches a reviewer from a prepared section', () => {
  it('can fail: the plausible screen the ruling forbids', () => {
    expect(withDigits(['Блоков на странице: 28 249', 'Блоки'])).toEqual([
      'Блоков на странице: 28 249',
    ]);
    // A count of zero is still a count, and it is the one a stub is most tempted to write.
    expect(withDigits(['Исполнителей: 0'])).toEqual(['Исполнителей: 0']);
  });

  it.each(SECTIONS)('$name shows no number at all', ({ screen }) => {
    const text = visibleText(render(createElement(screen)));
    expect(text.length, 'the screen rendered nothing, so this assertion is vacuous').toBeGreaterThan(2);
    expect(withDigits(text)).toEqual([]);
  });
});

// ------------------------------------------------- 2. a promise, and one nobody shares

describe('R-23: each section promises something of its own, and none of them is the default', () => {
  it('can fail: four screens sharing the component default', () => {
    const generic = 'Раздел появится в одной из следующих версий.';
    expect(unpromised([generic, generic], generic)).toEqual([generic, generic]);
    expect(unpromised(['Своё обещание', generic], generic)).toEqual([generic]);
    // And the reader that picks the promise out of a screen's strings.
    expect(longest(['Блоки', 'Раздел пока недоступен', generic])).toBe(generic);
  });

  it('none of the four falls back to the generic sentence', () => {
    expect(GENERIC.length, 'the component rendered no default sentence to compare against')
      .toBeGreaterThan(80);
    for (const { name, screen } of SECTIONS) {
      const text = visibleText(render(createElement(screen)));
      expect(unpromised(text, GENERIC), `${name} shows the generic sentence`).toEqual([]);
    }
  });

  it('the four promises are pairwise distinct', () => {
    // Longest visible string on each screen: on a RoutePlaceholder that is the promise.
    const promises = SECTIONS.map(({ screen }) =>
      longest(visibleText(render(createElement(screen)))),
    );
    for (const promise of promises) expect(promise.length).toBeGreaterThan(80);
    expect(new Set(promises).size).toBe(SECTIONS.length);
  });
});

/** The strings that are the component's own fallback rather than a promise of their own. */
export function unpromised(rendered: readonly string[], generic: string): string[] {
  return rendered.filter((s) => s === generic);
}

// ------------------------------------- 3. a stub may not claim something false about the system

/**
 * The words that promise a section is on its way.
 *
 * `«пока»` and `«ещё»` are the whole of it, and they are the component's own two fixed
 * sentences. `R-18` says a stub may not claim something false about the system;
 * `PROTOTYPE_PROFILE.md` §7.2 defers remote/distributed workers and the `Job/Attempt`
 * framework, so on `/workers` a *yet* is exactly such a claim.
 */
export function futurePromises(strings: readonly string[]): string[] {
  return strings.filter((s) => /Раздел пока недоступен|Этот раздел ещё не готов/.test(s));
}

describe('R-18: the workers stub does not say a thing is coming that nobody decided to build', () => {
  it('can fail: the default wording, which is what this screen would render untold', () => {
    expect(futurePromises(['Раздел пока недоступен', 'Исполнители'])).toEqual([
      'Раздел пока недоступен',
    ]);
    expect(futurePromises(['Этот раздел ещё не готов.'])).toEqual(['Этот раздел ещё не готов.']);
  });

  it('workers renders neither of the component\'s two "yet" sentences', () => {
    const text = visibleText(render(createElement(WorkersPage)));
    expect(futurePromises(text)).toEqual([]);
    // Non-vacuous: it says something in their place rather than nothing.
    expect(text.some((s) => s.includes('в альфе'))).toBe(true);
  });

  it('the other three still carry them, so the exemption is one screen and not a hole', () => {
    // The ratchet's other direction. If this ever fails, either a section was newly
    // deferred -- in which case say so here -- or the component's default moved.
    for (const { name, screen } of SECTIONS.filter((s) => s.name !== 'workers')) {
      const text = visibleText(render(createElement(screen)));
      expect(futurePromises(text).length, `${name} no longer says the section is coming`)
        .toBeGreaterThan(0);
    }
  });
});

// -------------------------------------------------------- 4. a place in the navigation

/** The `href`s of the frame's top-level nav links. */
export function navTargets(markup: string): string[] {
  return [...markup.matchAll(/<a\b[^>]*\bhref="([^"]+)"[^>]*>/g)].map((m) => m[1] as string);
}

describe('R-23: each prepared section has a place in the navigation', () => {
  it('can fail: a frame that links to none of them', () => {
    expect(navTargets('<a href="/projects">Проекты</a>')).toEqual(['/projects']);
    expect(navTargets('<a href="/projects">П</a>')).not.toContain('/blocks');
  });

  it('the frame links to all four addresses', () => {
    const targets = navTargets(render(createElement(AppFrame, { children: null })));
    // Non-vacuous in both factors: the two links that predate this wave must still be
    // there, otherwise "contains /blocks" could pass on a frame that lost everything else.
    expect(targets).toContain('/knowledge-base');
    expect(targets).toContain('/account/password');
    for (const { route } of SECTIONS) expect(targets).toContain(route);
  });

  it('each address is served by a route file that renders its own screen and no other', () => {
    for (const { title, routeFile, screen } of SECTIONS) {
      const viaRoute = render(createElement(routeFile));
      expect(viaRoute).toBe(render(createElement(screen)));
      expect(visibleText(viaRoute)).toContain(title);
    }
  });

  it('the four screens are four different screens', () => {
    const titles = SECTIONS.map(({ screen }) => visibleText(render(createElement(screen)))[0]);
    expect(new Set(titles).size).toBe(SECTIONS.length);
  });
});
