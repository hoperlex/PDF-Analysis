'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type { NormCurrentSnapshot, NormsSnapshotId } from '@/shared/api';
import { queryKeys, setCurrentNormSnapshot } from '@/shared/api';

export interface SetCurrentSnapshotCommand {
  readonly normsSnapshotId: NormsSnapshotId;
  readonly expectedCurrent: NormsSnapshotId | null;
}

/** What makes two presses one intent: the same target against the same believed current. */
export function designationIntent({ normsSnapshotId, expectedCurrent }: SetCurrentSnapshotCommand): string {
  return JSON.stringify([normsSnapshotId, expectedCurrent]);
}

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
 *
 * **One request in flight per intent** (`WEB-FOLLOWUPS-02`, `D-195`). A second press of the
 * same designation before the first answer used to send a second `POST`, answered as a replay
 * (the target is already current) or as `stale_current_snapshot`, and the screen showed the
 * later answer over a designation the administrator had just made. A press that finds the
 * same intent (target and expected current) in flight now joins the request already sent; the
 * gate reopens when it settles, so a deliberate press afterwards (another target, or the same
 * one against a newly read current) is a new request.
 */
export function useSetCurrentSnapshot() {
  const client = useQueryClient();
  const flightRef = useRef<{
    readonly intent: string;
    readonly promise: Promise<NormCurrentSnapshot>;
  } | null>(null);

  const send = async ({ normsSnapshotId, expectedCurrent }: SetCurrentSnapshotCommand) =>
    (await setCurrentNormSnapshot({
      body: { norms_snapshot_id: normsSnapshotId, expected_current: expectedCurrent },
    })).data;

  return useMutation<NormCurrentSnapshot, unknown, SetCurrentSnapshotCommand>({
    mutationFn: (command) => {
      const intent = designationIntent(command);
      const held = flightRef.current;
      if (held !== null && held.intent === intent) return held.promise;
      const promise: Promise<NormCurrentSnapshot> = send(command).finally(() => {
        if (flightRef.current?.promise === promise) flightRef.current = null;
      });
      flightRef.current = { intent, promise };
      return promise;
    },
    retry: false,
    onSettled: () => {
      void client.invalidateQueries({ queryKey: queryKeys.norms.all() });
    },
  });
}
