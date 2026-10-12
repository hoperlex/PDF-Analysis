'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { NormCurrentSnapshot, NormsSnapshotId } from '@/shared/api';
import { queryKeys, setCurrentNormSnapshot } from '@/shared/api';

/**
 * `setCurrentNormSnapshot` (`W55A-WEB-NORMS`, plan §A3.2, R-113): an administrator makes a
 * qualifying snapshot the current one, which every new run and re-audit then pins.
 *
 * The request is a compare-and-set, not a keyed command: `expectedCurrent` is the snapshot
 * the screen showed as current (`null` for none), and the server refuses a stale belief with
 * `conflict` (`stale_current_snapshot`) and answers an already-current target as a replay.
 * So a repeat of the same confirmed intent is safe and carries no idempotency key.
 * `retry: false`: nothing here repeats a write on its own.
 *
 * Every norms read is invalidated when the request SETTLES, success or not: a success
 * changes which snapshot is current, what search reads and the history; a stale refusal
 * means the screen's list is out of date and must be read again before the next attempt.
 * No number the dashboard reads changes.
 */
export function useSetCurrentSnapshot() {
  const client = useQueryClient();
  return useMutation<NormCurrentSnapshot, unknown,
    { normsSnapshotId: NormsSnapshotId; expectedCurrent: NormsSnapshotId | null }>({
    mutationFn: async ({ normsSnapshotId, expectedCurrent }) =>
      (await setCurrentNormSnapshot({
        body: { norms_snapshot_id: normsSnapshotId, expected_current: expectedCurrent },
      })).data,
    retry: false,
    onSettled: () => {
      void client.invalidateQueries({ queryKey: queryKeys.norms.all() });
    },
  });
}
