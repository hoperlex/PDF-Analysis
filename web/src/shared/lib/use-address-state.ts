'use client';

/**
 * A piece of a screen's state that lives in the address (`R-150c`): read from the query string, written back through the browser's
 * own history API.
 *
 * Two screens kept the same hook by copy («Сравнение версий» and «Сравнение стадий», lane D6), and «Очередь» needs it for its
 * filter; this is the one. What it keeps is the contract each copy had:
 *
 *   READ     `read(params)` over `useSearchParams()`, which Next keeps in step with the history API, so a step costs no server
 *            round trip. Outside the app router there are no params: the static render starts from `initial` when the screen
 *            gives one (the route read the address on the server and hands it down), else from the empty address. Inside the
 *            router the address is the only source, so a link that changes it changes the screen.
 *   WRITE    `write(params, next)` over the address AS IT IS NOW (not as it was when the handler was made: a poll may have
 *            written the run since), so a parameter this state does not own is carried through untouched.
 *   STEP     `push` (the default) is a step the reader took, so Back returns to the earlier state; `replace` is for a state the
 *            screen reached by itself, which must not add an entry. A write that changes nothing is dropped, so a poll that
 *            re-announces the same state adds no entry either.
 *
 * Pure parts stay with the screen: what the parameters mean (`read`, `write`) is the screen's, and a test calls them as plain
 * functions. This hook adds only the three things above.
 */

import { useSearchParams } from 'next/navigation';

/** What `read` and `write` need of a query string: both `URLSearchParams` and Next's read-only one have it. */
export type AddressParams = Pick<URLSearchParams, 'get' | 'toString'>;

/** `push` makes a step of the history; `replace` rewrites the current one. */
export type AddressStep = 'push' | 'replace';

const NO_PARAMS = new URLSearchParams();

export function useAddressState<T>(
  read: (params: AddressParams) => T,
  write: (params: AddressParams, next: T) => URLSearchParams,
  initial?: T,
): readonly [T, (next: T, how?: AddressStep) => void] {
  const params = useSearchParams();
  const value = params === null && initial !== undefined ? initial : read(params ?? NO_PARAMS);
  const go = (next: T, how: AddressStep = 'push') => {
    if (typeof window === 'undefined') return;
    const base = new URLSearchParams(window.location.search);
    const query = write(base, next).toString();
    if (query === base.toString()) return;
    const href = query === '' ? window.location.pathname : `${window.location.pathname}?${query}`;
    // The data is `null`, and Next copies its own history state into the new entry. Handed `window.history.state` (which carries
    // Next's `__NA` marker), Next's patch of these two functions passes the call straight through with no sync, and
    // `useSearchParams` never follows: the URL changed and the screen did not (D-341; the test holds it).
    if (how === 'push') window.history.pushState(null, '', href);
    else window.history.replaceState(null, '', href);
  };
  return [value, go] as const;
}
