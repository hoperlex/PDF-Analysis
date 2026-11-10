'use client';

/**
 * The connected strip: the queue's pause state, the vectors' pause state, the account's roles and the two switches.
 *
 * One idempotency key serves one intent and its retries, for each of the two commands (`newIdempotencyKey`); an
 * intent is "make it paused" or "make it running", so a key is kept until that intent succeeds or is dropped.
 */

import { useRef, useState } from 'react';

import { failureMessage, newIdempotencyKey } from '@/shared/api';
import { useMe } from '@/entities/account';
import {
  canExecute, canSeePause, useExecutionDispatch, useVectorControl, vectorsPauseOf,
} from '@/entities/execution';
import { usePauseExecution, useSetVectorPaused } from '@/features/pause-execution';

import { PauseStatusView } from './pause-status-view';

interface Intent {
  readonly paused: boolean;
  readonly key: string;
}

/** The key of the intent that makes the state `paused`: the one still in hand if it is the same intent, a new one otherwise. */
function intentFor(held: Intent | null, paused: boolean): Intent {
  return held !== null && held.paused === paused ? held : { paused, key: newIdempotencyKey() };
}

/** The connected indicator. Mount it only for a session the queue is open to. */
export function PauseStatusLive() {
  const dispatch = useExecutionDispatch();
  const account = useMe();
  const roles = account.data?.roles ?? [];
  // The vectors' read is closed to a viewer and waits for the roles; the queue's read is the frame's to gate (`offersPauseStatus`).
  const mayRead = account.data !== undefined && canSeePause(roles);
  const vectors = useVectorControl(mayRead);
  const pause = usePauseExecution();
  const vectorPause = useSetVectorPaused();
  const [asking, setAsking] = useState(false);
  const dispatchIntent = useRef<Intent | null>(null);
  const vectorIntent = useRef<Intent | null>(null);

  function confirm() {
    const status = dispatch.data;
    if (status === undefined) return;
    const intent = intentFor(dispatchIntent.current, !status.paused);
    dispatchIntent.current = intent;
    pause.mutate(
      { paused: intent.paused, idempotencyKey: intent.key },
      { onSuccess: () => { dispatchIntent.current = null; setAsking(false); } },
    );
  }

  function toggleVectors() {
    const control = vectors.data;
    if (control === undefined || vectorPause.isPending) return;
    pause.reset();
    vectorPause.reset();
    const intent = intentFor(vectorIntent.current, !control.paused);
    vectorIntent.current = intent;
    vectorPause.mutate(
      { paused: intent.paused, idempotencyKey: intent.key },
      { onSuccess: () => { vectorIntent.current = null; } },
    );
  }

  const refusal = pause.isError ? pause.error : vectorPause.isError ? vectorPause.error : null;
  return (
    <PauseStatusView
      status={dispatch.data}
      failed={dispatch.isError}
      mayToggle={account.data !== undefined && canExecute(roles, 'pause')}
      asking={asking}
      busy={pause.isPending}
      error={refusal === null ? null : failureMessage(refusal).detail}
      onAsk={() => { pause.reset(); vectorPause.reset(); setAsking(true); }}
      onConfirm={confirm}
      onCancel={() => { pause.reset(); dispatchIntent.current = null; setAsking(false); }}
      vectors={mayRead ? vectorsPauseOf(vectors.data, vectors.isError) : undefined}
      onToggleVectors={toggleVectors}
    />
  );
}
