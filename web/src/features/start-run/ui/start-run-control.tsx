'use client';

/**
 * Start one run over one published version.
 *
 * There is no provider-mode selector and, on failure, no offer to start the run "in
 * recorded mode instead". `dependency_unavailable` is rendered as itself, with a retry
 * under the same key and nothing else — the alternative on offer would be a different
 * run whose provenance the user did not ask for.
 *
 * There is no cancel and no re-run carryover: `P3-WEB-01` rules both out for PC-01.
 */

import type { RunStatus, VersionUid } from '@/shared/api';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import { useIntentKey } from '@/shared/lib';
import type { RunFailure } from '@/entities/audit-run';
import { classifyRunFailure } from '@/entities/audit-run';

import { useStartRun } from '../model/use-start-run';

export interface StartRunControlProps {
  readonly versionUid: VersionUid;
  /** Called with the 202 reading, so the screen can move to run progress. */
  readonly onStarted?: ((run: RunStatus) => void) | undefined;
}

export function StartRunControl({ versionUid, onStarted }: StartRunControlProps) {
  const idempotencyKey = useIntentKey(`start-run:${versionUid}`);
  const mutation = useStartRun();

  const send = () => {
    mutation.mutate({ versionUid, idempotencyKey }, { onSuccess: (run) => onStarted?.(run) });
  };

  const failure: RunFailure | null =
    mutation.error === null || mutation.error === undefined
      ? null
      : classifyRunFailure(mutation.error);

  return (
    <div>
      <button type="button" className="am-button" onClick={send} disabled={mutation.isPending}>
        Start run
      </button>
      <p>
        <em>
          The run uses the provider mode this deployment is configured for. It is shown on
          the run, and it is never chosen here.
        </em>
      </p>

      {mutation.isPending ? <LoadingState what="the run request" /> : null}

      {failure !== null && failure.presentation === 'unsupported' ? (
        <UnsupportedState
          title={failure.title}
          detail={
            <>
              <p data-run-failure={failure.kind}>{failure.detail}</p>
              {failure.correlationId === null ? null : (
                <p>
                  Correlation id <code>{failure.correlationId}</code>
                </p>
              )}
              <p>No run was started.</p>
            </>
          }
        />
      ) : null}

      {failure !== null && failure.presentation === 'error' ? (
        <ErrorState
          title={failure.title}
          detail={<span data-run-failure={failure.kind}>{failure.detail}</span>}
          correlationId={failure.correlationId}
          {...(failure.retryable ? { onRetry: send, retryLabel: 'Retry under the same key' } : {})}
        />
      ) : null}
    </div>
  );
}
