'use client';

/**
 * The pair, run and step of «Сравнение стадий», read from and written to the address (`UI-B-93`). The address is written through the
 * native history API, which Next keeps `useSearchParams` in step with, so a step costs no server round trip, as the page of «Блоки»
 * writes `?page=`. `push` makes a step of the history (Back returns to the earlier step); `replace` is for a state the screen reached
 * by itself. A write that changes nothing is dropped, so a poll that re-announces the same run adds no entry. Outside the app router
 * the hooks answer `null` and the static render starts from the empty address.
 */

import { useSearchParams } from 'next/navigation';

import { readStageAddress, writeStageAddress } from './address';
import type { StageAddress } from './address';

const NO_PARAMS = new URLSearchParams();

export function useStageAddress(): readonly [StageAddress, (next: StageAddress, how?: 'push' | 'replace') => void] {
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const address = readStageAddress(searchParams);
  const go = (next: StageAddress, how: 'push' | 'replace' = 'push') => {
    if (typeof window === 'undefined') return;
    // The base is the address as it is now, not as it was when the handler was made: a poll may have written the run since.
    const base = new URLSearchParams(window.location.search);
    const query = writeStageAddress(base, next).toString();
    if (query === base.toString()) return;
    const href = query === '' ? window.location.pathname : `${window.location.pathname}?${query}`;
    if (how === 'push') window.history.pushState(window.history.state, '', href);
    else window.history.replaceState(window.history.state, '', href);
  };
  return [address, go] as const;
}
