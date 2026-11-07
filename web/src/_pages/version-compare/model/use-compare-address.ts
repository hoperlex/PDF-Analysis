'use client';

/**
 * The open document set and tab of «Сравнение версий», read from and written to the address (`UI-B-102`). Opening a set or a
 * tab is a step in the history, so Back returns to the table; nothing else is kept in client state. The mechanics (the native
 * history API, a write that changes nothing dropped, the empty address outside the app router) are `useAddressState`'s, shared with
 * «Сравнение стадий» and «Очередь»; this file only says what the two parameters are and where a static render starts.
 */

import { useAddressState } from '@/shared/lib';

import { readCompareAddress, writeCompareAddress } from './address';
import type { CompareAddress } from './address';

export function useCompareAddress(initial?: Partial<CompareAddress>): readonly [CompareAddress, (next: CompareAddress) => void] {
  const [read, go] = useAddressState(readCompareAddress, writeCompareAddress);
  const address: CompareAddress =
    read.documentUid === null && initial?.documentUid !== undefined
      ? { documentUid: initial.documentUid, tab: initial.tab ?? 'projects' }
      : read;
  return [address, (next: CompareAddress) => go(next)] as const;
}
