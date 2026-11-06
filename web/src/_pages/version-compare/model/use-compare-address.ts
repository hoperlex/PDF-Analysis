'use client';

/**
 * The open document set and tab of «Сравнение версий», read from and written to the address (`UI-B-102`). Opening a set or a
 * tab is a step in the history, so Back returns to the table; nothing else is kept in client state. The address is written through the
 * native history API, which Next keeps `useSearchParams` in step with (as «Блоки» writes `?page=`), so a step costs no server round
 * trip. Outside the app router both hooks answer `null` and the static render starts from `initial`.
 */

import { useSearchParams } from 'next/navigation';

import { readCompareAddress, writeCompareAddress } from './address';
import type { CompareAddress } from './address';

const NO_PARAMS = new URLSearchParams();

export function useCompareAddress(initial?: Partial<CompareAddress>): readonly [CompareAddress, (next: CompareAddress) => void] {
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const read = readCompareAddress(searchParams);
  const address: CompareAddress =
    read.documentUid === null && initial?.documentUid !== undefined
      ? { documentUid: initial.documentUid, tab: initial.tab ?? 'projects' }
      : read;
  const go = (next: CompareAddress) => {
    if (typeof window === 'undefined') return;
    const base = new URLSearchParams(window.location.search);
    const query = writeCompareAddress(base, next).toString();
    if (query === base.toString()) return;
    window.history.pushState(window.history.state, '', query === '' ? window.location.pathname : `${window.location.pathname}?${query}`);
  };
  return [address, go] as const;
}
