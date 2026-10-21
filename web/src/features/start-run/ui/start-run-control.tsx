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
 *
 * `W59-SECTION-UI-01`: a version with no confirmed stage and section, or whose confirmed
 * section has no analysis profile, is refused before a run exists. The refusal says which,
 * and links to the version's stage-and-section panel (`routes.versionClassification`) —
 * the one place the first can be fixed and the second can be read. It offers no other
 * section and no default profile.
 */

import Link from 'next/link';

import type { ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import { routes, useIntentKey } from '@/shared/lib';
import type { RunFailure } from '@/entities/audit-run';
import { classifyRunFailure } from '@/entities/audit-run';

import { useStartRun } from '../model/use-start-run';

export interface StartRunControlProps {
  /** The project the version belongs to, for the link a classification refusal carries. */
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** Called with the 202 reading, so the screen can move to run progress. */
  readonly onStarted?: ((run: RunStatus) => void) | undefined;
}

export function StartRunControl({ projectUid, versionUid, onStarted }: StartRunControlProps) {
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
        Запустить прогон
      </button>
      <p className="am-note">
        <em>
          Прогон использует тот режим провайдера, на который настроено это развёртывание.
          Он показан на прогоне и никогда не выбирается здесь.
        </em>
      </p>

      {mutation.isPending ? <LoadingState what="запрос на прогон" /> : null}

      {failure !== null && failure.presentation === 'unsupported' ? (
        <UnsupportedState
          title={failure.title}
          detail={
            <>
              <p data-run-failure={failure.kind}>{failure.detail}</p>
              {failure.kind === 'version_unclassified' ||
              failure.kind === 'section_profile_unavailable' ? (
                <p>
                  <Link
                    href={routes.versionClassification(projectUid, versionUid)}
                    data-classification-link=""
                  >
                    {failure.kind === 'version_unclassified'
                      ? 'Подтвердить стадию и раздел'
                      : 'Открыть стадию и раздел версии'}
                  </Link>
                </p>
              ) : null}
              {failure.correlationId === null ? null : (
                <p>
                  Идентификатор корреляции <code>{failure.correlationId}</code>
                </p>
              )}
              <p>Прогон не запущен.</p>
            </>
          }
        />
      ) : null}

      {failure !== null && failure.presentation === 'error' ? (
        <ErrorState
          title={failure.title}
          detail={<span data-run-failure={failure.kind}>{failure.detail}</span>}
          correlationId={failure.correlationId}
          {...(failure.retryable ? { onRetry: send, retryLabel: 'Повторить с тем же ключом' } : {})}
        />
      ) : null}
    </div>
  );
}
