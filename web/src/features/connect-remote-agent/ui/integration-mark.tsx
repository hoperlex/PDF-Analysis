'use client';

/**
 * «Разрешено для интеграции» (`EXEC2-WEB-WIZARD-01`, `R-149b`, ADR-0026 decision 8): the
 * administrator's mark on an agent connection.
 *
 * It is one of four distinct statuses and **implies none of the other three**: it is not read off the
 * client's login, it does not install a client, it does not pass a probe, and none of them sets it. The
 * stand records who set it and when, journals both setting and clearing, and does not enforce it —
 * so the mark is shown, with the `R-149b` note beside it, and «готово» does not wait for it.
 *
 * Setting it asks first, in the connection's own words, because it is a decision of the administrator
 * and not a click through: the sentence is `INTEGRATION_NOTE`. Clearing needs no question.
 * `IntegrationMarkView` is a view driven by props.
 */

import { useState } from 'react';

import type { ExecutorConnection } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { formatInstant } from '@/shared/lib';
import {
  CommandFailure,
  useCommandKey,
  useSetExecutorIntegrationAuthorisation,
} from '@/features/manage-executor-connection';

import { agentFailure } from '../model/failure';
import {
  INTEGRATION_ASK_TEXT,
  INTEGRATION_CANCEL_LABEL,
  INTEGRATION_CLEAR_LABEL,
  INTEGRATION_CONFIRM_LABEL,
  INTEGRATION_NOTE,
  INTEGRATION_SET_LABEL,
  STEP_LABELS,
} from '../model/words';

export interface IntegrationMarkViewProps {
  readonly mark: ExecutorConnection['integration_authorisation'];
  readonly canManage: boolean;
  readonly asking: boolean;
  readonly pending: boolean;
  readonly failure: ExecutionFailure | null;
  readonly onAsk: () => void;
  readonly onCancel: () => void;
  readonly onSet: (authorised: boolean) => void;
}

export function IntegrationMarkView({
  mark, canManage, asking, pending, failure, onAsk, onCancel, onSet,
}: IntegrationMarkViewProps) {
  return (
    <section role="group" aria-label={STEP_LABELS.authorised} data-agent-mark={mark === undefined ? 'not_set' : 'set'}>
      <p className="am-note" data-agent-mark-note>{INTEGRATION_NOTE}</p>
      {mark !== undefined ? (
        <p>
          Отметка стоит с <time dateTime={mark.authorised_at}>{formatInstant(mark.authorised_at)}</time>, поставил{' '}
          <code>{mark.authorised_by}</code>.
        </p>
      ) : null}
      {canManage && !asking ? (
        <button
          className="am-button am-button--quiet"
          type="button"
          disabled={pending}
          data-agent-mark-action={mark === undefined ? 'set' : 'clear'}
          onClick={mark === undefined ? onAsk : () => onSet(false)}
        >
          {mark === undefined ? INTEGRATION_SET_LABEL : INTEGRATION_CLEAR_LABEL}
        </button>
      ) : null}
      {canManage && asking ? (
        <div role="group" aria-label={INTEGRATION_CONFIRM_LABEL} data-agent-mark-ask>
          <p className="am-note">{INTEGRATION_ASK_TEXT}</p>
          <button className="am-button" type="button" disabled={pending} data-agent-mark-confirm onClick={() => onSet(true)}>
            {INTEGRATION_CONFIRM_LABEL}
          </button>{' '}
          <button className="am-button am-button--quiet" type="button" disabled={pending} onClick={onCancel}>
            {INTEGRATION_CANCEL_LABEL}
          </button>
        </div>
      ) : null}
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </section>
  );
}

export interface IntegrationMarkProps {
  readonly connection: ExecutorConnection;
  readonly canManage: boolean;
}

export function IntegrationMark({ connection, canManage }: IntegrationMarkProps) {
  const set = useSetExecutorIntegrationAuthorisation();
  const keys = useCommandKey();
  const [asking, setAsking] = useState(false);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function apply(authorised: boolean) {
    setFailure(null);
    try {
      await set.mutateAsync({
        connectionId: connection.connection_id,
        authorised,
        idempotencyKey: keys.keyFor(`${connection.connection_id}:${authorised}`),
      });
      keys.release();
      setAsking(false);
    } catch (error) {
      const failed = agentFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <IntegrationMarkView
      mark={connection.integration_authorisation}
      canManage={canManage}
      asking={asking}
      pending={set.isPending}
      failure={failure}
      onAsk={() => { setAsking(true); setFailure(null); }}
      onCancel={() => { setAsking(false); setFailure(null); }}
      onSet={(authorised) => void apply(authorised)}
    />
  );
}
