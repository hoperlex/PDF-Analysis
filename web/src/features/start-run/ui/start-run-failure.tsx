'use client';

/**
 * What a refused or failed start says, and the one thing it offers (`EXEC-PAR-WEB-01` moved this
 * out of the control so the states a settled mutation produces can be rendered by instruments
 * that cannot settle one, as `start-ar-v3-group` does).
 *
 * There is no provider-mode choice here and no offer to start the run "in recorded mode instead".
 * `dependency_unavailable` is rendered as itself, with a retry under the same key and nothing else
 * — the alternative on offer would be a different run whose provenance the user did not ask for.
 * The same holds for the executor the person chose: a refusal of it (`kind` `executor_unavailable`
 * or `executor_invalid`) is its own sentence, carries a retry only when the envelope says it is
 * retryable, and offers neither another executor nor the route in its place.
 *
 * `W59-SECTION-UI-01`: a version with no confirmed stage and section, or whose confirmed section
 * has no analysis profile, is refused before a run exists. The refusal says which, and links to the
 * version's stage-and-section panel (`routes.versionClassification`) — the one place the first can
 * be fixed and the second can be read. It offers no other section and no default profile.
 */

import Link from 'next/link';

import type { ProjectUid, VersionUid } from '@/shared/api';
import { ErrorState, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import type { RunFailure } from '@/entities/audit-run';

export interface StartRunFailureViewProps {
  readonly failure: RunFailure;
  /** The project the version belongs to, for the link a classification refusal carries. */
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** Sends the same start again, under the key it was sent with. */
  readonly onRetry: () => void;
}

export function StartRunFailureView({ failure, projectUid, versionUid, onRetry }: StartRunFailureViewProps) {
  if (failure.presentation === 'unsupported') {
    return (
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
    );
  }

  return (
    <ErrorState
      title={failure.title}
      detail={<span data-run-failure={failure.kind}>{failure.detail}</span>}
      correlationId={failure.correlationId}
      {...(failure.retryable ? { onRetry, retryLabel: 'Повторить с тем же ключом' } : {})}
    />
  );
}
