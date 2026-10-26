'use client';

/**
 * Start one run over one published version, on the executor the person chooses.
 *
 * `EXEC-PAR-WEB-01`: the control offers «Исполнитель» — «По умолчанию (маршрут)» or one of the
 * connections that can serve a run now (`./executor-select.tsx`). The choice goes out as
 * `executor_connection_id` and only when a connection is chosen; the default is the absence of
 * the field (`../model/start-run-intent.ts`). It is part of the intent: the same version on
 * another executor is another request, so the idempotency key is minted for the version *and* the
 * choice. A connection that stops being usable between choosing and starting refuses the start;
 * the choice stays on the page, the refusal is said as itself and carries a retry under the same
 * key (`./start-run-failure.tsx`). The control never picks another executor, or the route, after
 * a refusal — changing the choice is the person's act, and a changed choice clears the old
 * refusal, which was about the old one.
 *
 * The list of connections is read with the existing hooks of `entities/executor-connection`
 * (open to every role). It adds no polling of its own; when it cannot be read the select says so
 * and the start on the default still works.
 *
 * There is no provider-mode selector and, on failure, no offer to start the run "in recorded mode
 * instead" — the mode this deployment is configured for is shown on the run and never chosen
 * here. There is no cancel and no re-run carryover: `P3-WEB-01` rules both out for PC-01.
 */

import { useId, useState } from 'react';

import type { ExecutorConnectionId, ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { LoadingState } from '@/shared/ui';
import { useIntentKey } from '@/shared/lib';
import type { RunFailure } from '@/entities/audit-run';
import { classifyRunFailure } from '@/entities/audit-run';
import { executionFailure } from '@/entities/execution';
import {
  executorChoices,
  useExecutorConnectionDetails,
  useExecutorConnections,
} from '@/entities/executor-connection';

import { startRunIntent } from '../model/start-run-intent';
import { useStartRun } from '../model/use-start-run';

import type { ExecutorListReading } from './executor-select';
import { ExecutorSelectView } from './executor-select';
import { StartRunFailureView } from './start-run-failure';

export interface StartRunControlProps {
  /** The project the version belongs to, for the link a classification refusal carries. */
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** Called with the 202 reading, so the screen can move to run progress. */
  readonly onStarted?: ((run: RunStatus) => void) | undefined;
}

/**
 * The connections as the select reads them: the list, then the settings of each connection that
 * is not archived (the readiness rule needs the current revision and its probe).
 */
function useExecutorListReading(): ExecutorListReading {
  const list = useExecutorConnections();
  const items = list.data?.items ?? [];
  const settings = useExecutorConnectionDetails(
    items.filter((item) => item.archived_at === undefined).map((item) => item.connection_id),
  );

  if (list.data === undefined && list.isError) {
    const failure = executionFailure(list.error, false);
    return {
      phase: 'failed',
      detail: failure.detail,
      correlationId: failure.correlationId,
      onRetry: () => void list.refetch(),
    };
  }
  if (list.data === undefined || settings.pending) return { phase: 'loading' };
  return { phase: 'ready', choices: executorChoices(items, settings.details) };
}

export function StartRunControl({ projectUid, versionUid, onStarted }: StartRunControlProps) {
  const [chosen, setChosen] = useState<ExecutorConnectionId | null>(null);
  const intent = startRunIntent(versionUid, chosen);
  const idempotencyKey = useIntentKey(intent.signature);
  const mutation = useStartRun();
  const selectId = useId();
  const reading = useExecutorListReading();

  const send = () => {
    mutation.mutate(intent.command(idempotencyKey), { onSuccess: (run) => onStarted?.(run) });
  };

  const failure: RunFailure | null =
    mutation.error === null || mutation.error === undefined
      ? null
      : classifyRunFailure(mutation.error);

  return (
    <div className="am-form" data-start-run-control>
      <ExecutorSelectView
        id={selectId}
        reading={reading}
        value={chosen}
        disabled={mutation.isPending}
        onChange={(next) => {
          setChosen(next);
          mutation.reset();
        }}
      />
      <button type="button" className="am-button" onClick={send} disabled={mutation.isPending}>
        Запустить прогон
      </button>
      <p className="am-note">
        <em>
          Прогон использует тот режим провайдера, на который настроено это развёртывание.
          Он показан на прогоне и никогда не выбирается здесь.
        </em>
      </p>

      {mutation.isPending ? <LoadingState what="запрос на прогон" /> : null}

      {failure === null ? null : (
        <StartRunFailureView
          failure={failure}
          projectUid={projectUid}
          versionUid={versionUid}
          onRetry={send}
        />
      )}
    </div>
  );
}
