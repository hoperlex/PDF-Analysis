'use client';

/**
 * The switch «Использовать» of a server row (`HOSTS-WEB-01`, `R-149b`). **Only an administrator is drawn it**: the caller
 * passes the control to an administrator and nothing to anyone else, and the server checks the role again. Off, the server
 * takes no new run; the runs it already holds finish. Every change is a journalled event on the server, with its author.
 *
 * The switch shows the server's own answer: it is not flipped until the command has been accepted, so a refused command leaves
 * it where it was, with the refusal under it. One idempotency key per intent, kept for an explicit repeat after an unknown
 * outcome and released when the command settles.
 */

import { useState } from 'react';

import type { ExecutorHostId } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { USE_HINT, USE_LABEL, hostFailure } from '@/entities/executor-host';
import { useCommandKey } from '@/features/manage-executor-connection';

import { useSetExecutorHostEnabled } from '../model/use-manage-executor-host';
import { HostFailure } from './host-failure';

export interface HostEnabledSwitchViewProps {
  readonly name: string;
  readonly enabled: boolean;
  readonly pending: boolean;
  readonly failure: ExecutionFailure | null;
  readonly onChange: (next: boolean) => void;
}

export function HostEnabledSwitchView({ name, enabled, pending, failure, onChange }: HostEnabledSwitchViewProps) {
  return (
    <span data-host-switch={enabled ? 'on' : 'off'}>
      <label title={USE_HINT}>
        <input
          type="checkbox"
          role="switch"
          checked={enabled}
          disabled={pending}
          aria-label={`${USE_LABEL}: ${name}`}
          onChange={(event) => onChange(event.currentTarget.checked)}
        />{' '}
        {USE_LABEL}
      </label>
      {failure === null ? null : <HostFailure failure={failure} />}
    </span>
  );
}

export interface HostEnabledSwitchProps {
  readonly hostId: ExecutorHostId;
  readonly name: string;
  readonly enabled: boolean;
}

export function HostEnabledSwitch({ hostId, name, enabled }: HostEnabledSwitchProps) {
  const set = useSetExecutorHostEnabled();
  const keys = useCommandKey();
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function change(next: boolean) {
    setFailure(null);
    try {
      await set.mutateAsync({ hostId, enabled: next, idempotencyKey: keys.keyFor(`${hostId}:${String(next)}`) });
      keys.release();
    } catch (error) {
      const failed = hostFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <HostEnabledSwitchView name={name} enabled={enabled} pending={set.isPending} failure={failure} onChange={(next) => void change(next)} />
  );
}
