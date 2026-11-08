/**
 * A knowledge-base page mounted under an address that follows what the page writes (`D-372`).
 *
 * The page keeps its type, view, category and verdict in the address (`useAddressState`): it reads `useSearchParams()` and writes through
 * the history API. The one-pass harness has no router, so a live mount of the page would never see its own write. This is the smallest
 * stand that closes the gap: `SearchParamsContext` and `PathnameContext` (what Next's hooks read) held in component state, and a
 * `window` whose `location.search` and `history.replaceState`/`pushState` are the same address -- a write sets the state and the page
 * renders again. Only the address is replaced; the page, its queries and its widgets are the real ones.
 *
 * The window is the one `mountLive` makes and takes away on unmount, so nothing is left behind for the next file (vitest runs every file
 * in one process).
 */

import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

const held = { search: '', write: null as ((query: string) => void) | null };

/** The query string the page last wrote, or the one it was mounted at. */
export const currentSearch = (): string => held.search;

const record = (_state: unknown, _title: string, href: string): void => {
  const at = href.indexOf('?');
  const query = at < 0 ? '' : href.slice(at + 1);
  held.search = query;
  held.write?.(query);
};

/**
 * Give the window `mountLive` made (`document.defaultView`, a plain object that goes with the mount) a `location` and a `history`
 * that are this address. Done while the page renders, because the window exists only from the mount: a stub made earlier is
 * replaced by it.
 */
function installOnWindow(): void {
  const target = (globalThis as unknown as { window?: Record<string, unknown> }).window;
  if (target === undefined) return;
  Object.defineProperty(target, 'location', {
    configurable: true,
    value: {
      get search(): string {
        return held.search === '' ? '' : `?${held.search}`;
      },
      pathname: '/knowledge-base',
    },
  });
  Object.defineProperty(target, 'history', { configurable: true, value: { state: null, pushState: record, replaceState: record } });
}

/** `query` is where the screen opens; a different `query` on a later render is a navigation (a link, the header's choice). */
export function RoutedAddress({ query, children }: { readonly query: string; readonly children?: ReactNode }) {
  const [state, setState] = useState({ from: query, search: query });
  if (state.from !== query) setState({ from: query, search: query });
  installOnWindow();
  held.search = state.from === query ? state.search : query;
  held.write = (next) => setState({ from: query, search: next });
  const params = useMemo(() => new URLSearchParams(held.search), [state.search, state.from, query]);
  return createElement(
    PathnameContext.Provider,
    { value: '/knowledge-base' },
    createElement(SearchParamsContext.Provider, { value: params as never }, children),
  );
}
