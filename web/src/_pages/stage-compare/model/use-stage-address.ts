'use client';

/**
 * The pair, run and step of «Сравнение стадий», read from and written to the address (`UI-B-93`). `push` makes a step of the history
 * (Back returns to the earlier step); `replace` is for a state the screen reached by itself. The mechanics are `useAddressState`'s,
 * shared with «Сравнение версий» and «Очередь»; this file only says what the three parameters are.
 */

import { useAddressState } from '@/shared/lib';

import { readStageAddress, writeStageAddress } from './address';
import type { StageAddress } from './address';

export function useStageAddress(): readonly [StageAddress, (next: StageAddress, how?: 'push' | 'replace') => void] {
  return useAddressState(readStageAddress, writeStageAddress);
}
