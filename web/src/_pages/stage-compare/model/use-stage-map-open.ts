'use client';

/**
 * Whether the sheet map of «Сравнение стадий» is open, read from and written to the address (`UI-B-93`, `?map=closed`). Folding the map
 * is a choice about the look of the screen, not a step of the comparison, so it replaces the entry and Back does not walk through folds.
 * The mechanics are `useAddressState`'s.
 */

import { useAddressState } from '@/shared/lib';

import { readMapOpen, writeMapOpen } from './address';

export function useStageMapOpen(): readonly [boolean, (open: boolean) => void] {
  const [open, go] = useAddressState(readMapOpen, writeMapOpen);
  return [open, (next) => go(next, 'replace')] as const;
}
