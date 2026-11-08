/**
 * «Разбор» mounted under an address that follows what the page writes (`D-401`).
 *
 * The page reads `?finding=` through `useSearchParams()` and writes it with `history.replaceState(null, …)`. The one-pass harness has no
 * router, so a live mount would never see its own write. This is the smallest stand that closes the gap, the same one
 * `knowledge-base/routed-address.ts` makes for «База знаний»: `SearchParamsContext` and `PathnameContext` (what Next's hooks read) held in
 * component state, and a `window` whose `location.search` and `history.replaceState`/`pushState` are the same address -- a write sets the
 * state and the page renders again. Only the address is replaced; the page, its queries and its widgets are the real ones.
 *
 * The window is the one `mountLive` makes and takes away on unmount, so nothing is left behind for the next file (vitest runs every file in
 * one process).
 */

import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

const held = { search: '', pathname: '/', writes: [] as string[], write: null as ((query: string) => void) | null };

/** The query string the page last wrote, or the one it was mounted at. */
export const currentSearch = (): string => held.search;

/** Every address the page wrote, in order (the query string only, as the page handed it over). */
export const writtenAddresses = (): readonly string[] => held.writes;

/** What the page handed to `replaceState`/`pushState` as the state: `null` is the form Next syncs to `useSearchParams` (`D-341`). */
export const writtenStates: unknown[] = [];

/** `replace` or `push`, for each write in order: a filter is not a place to go Back to, so it replaces. */
export const writtenHow: string[] = [];

/**
 * What `window.history.state` is in a running app: Next's own marker (`__NA`). A page that hands this on as the state of its write is
 * the page `D-341` found, and the state it records here is this object, not `null`.
 */
const NEXT_STATE = { __NA: true };

const recorder = (how: 'push' | 'replace') => (state: unknown, _title: string, href: string): void => {
  const at = href.indexOf('?');
  const query = at < 0 ? '' : href.slice(at + 1);
  writtenHow.push(how);
  writtenStates.push(state);
  held.writes.push(query);
  held.search = query;
  held.write?.(query);
};

function installOnWindow(): void {
  const target = (globalThis as unknown as { window?: Record<string, unknown> }).window;
  if (target === undefined) return;
  Object.defineProperty(target, 'location', {
    configurable: true,
    value: {
      get search(): string {
        return held.search === '' ? '' : `?${held.search}`;
      },
      get pathname(): string {
        return held.pathname;
      },
    },
  });
  Object.defineProperty(target, 'history', { configurable: true, value: { state: NEXT_STATE, pushState: recorder('push'), replaceState: recorder('replace') } });
}

/** Forget what an earlier case wrote. */
export function resetRoutedAddress(): void {
  held.search = '';
  held.writes.length = 0;
  writtenStates.length = 0;
  writtenHow.length = 0;
}

export function RoutedReviewAddress({ pathname, query, children }: { readonly pathname: string; readonly query: string; readonly children?: ReactNode }) {
  const [state, setState] = useState({ from: query, search: query });
  if (state.from !== query) setState({ from: query, search: query });
  installOnWindow();
  held.pathname = pathname;
  held.search = state.from === query ? state.search : query;
  held.write = (next) => setState({ from: query, search: next });
  const params = useMemo(() => new URLSearchParams(held.search), [state.search, state.from, query]);
  return createElement(
    PathnameContext.Provider,
    { value: pathname },
    createElement(SearchParamsContext.Provider, { value: params as never }, children),
  );
}
