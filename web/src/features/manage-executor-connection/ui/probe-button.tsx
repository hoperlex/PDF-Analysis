'use client';

/**
 * «Проверить» (`requestExecutorProbe`, `EXEC-HTTP-01`).
 *
 * The probe runs on a worker, over the same network path as a real call, so the answer is not
 * this request's: the button only records that a probe is wanted. The connection's card shows
 * the probe as requested, then running, then its outcome in Russian; the detail read polls
 * while a probe is open. A second press while one is open is refused here, and the server
 * refuses it too.
 */

import { useState } from 'react';

import type { ExecutorConnectionId } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { connectionFailure } from '@/entities/executor-connection';

import { useCommandKey } from '../model/use-command-key';
import { useRequestExecutorProbe } from '../model/use-manage-executor-connection';
import { CommandFailure } from './command-failure';

export interface ProbeButtonProps {
  readonly connectionId: ExecutorConnectionId;
  /** The revision the probe will test, so a repeat after an unknown outcome is the same intent. */
  readonly revisionId: string;
  /** A probe is already requested or running. */
  readonly open: boolean;
}

export function ProbeButton({ connectionId, revisionId, open }: ProbeButtonProps) {
  const probe = useRequestExecutorProbe();
  const keys = useCommandKey();
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function press() {
    setFailure(null);
    try {
      await probe.mutateAsync({ connectionId, idempotencyKey: keys.keyFor(`${connectionId}:${revisionId}`) });
      keys.release();
    } catch (error) {
      const failed = connectionFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <>
      <button
        className="am-button"
        type="button"
        data-executor-probe={connectionId}
        disabled={probe.isPending || open}
        onClick={() => void press()}
      >
        {open ? 'Проверка идёт…' : 'Проверить'}
      </button>
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </>
  );
}
