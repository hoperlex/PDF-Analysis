'use client';

/**
 * Start the six AR v3 checks over one published version.
 *
 * It is the group's counterpart of `StartRunControl` and borrows its discipline: one
 * idempotency key per intent (`useIntentKey`), a retry under the same key and nothing else,
 * no provider-mode selector, no pack selection and no text input. On failure the refusal is
 * said in its own sentence (`../model/start-failure.ts`) and the single-run start is never
 * offered as a substitute.
 *
 * The control does not navigate. It hands the 202 group to `onStarted`, and the widget that
 * mounts it decides where to go (`run-list` opens the group review). A 202 whose group
 * address is malformed is a fault, not a success: `onStarted` is not called with it.
 *
 * It is split into this hook-holding component and a presentational `StartArV3GroupView`, so
 * the states a settled mutation produces — pending, and every refusal — are renderable by
 * the instruments that cannot settle a mutation (`D-82`).
 */

import Link from 'next/link';

import type { ArV3BetaGroup, ProjectUid, VersionUid } from '@/shared/api';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import { routes, useIntentKey } from '@/shared/lib';
import { looksLikeArV3GroupId } from '@/entities/audit-run';

import type { ArV3GroupStartFailure } from '../model/start-failure';
import {
  CLASSIFICATION_LINK_KINDS,
  MALFORMED_GROUP_ANSWER,
  classifyArV3GroupStartFailure,
} from '../model/start-failure';
import { useStartArV3Group } from '../model/use-start-ar-v3-group';

import styles from './start-ar-v3-group-control.module.css';

export interface StartArV3GroupViewProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  readonly pending: boolean;
  readonly failure: ArV3GroupStartFailure | null;
  readonly onSend: () => void;
}

export function StartArV3GroupView({
  projectUid,
  versionUid,
  pending,
  failure,
  onSend,
}: StartArV3GroupViewProps) {
  return (
    <div className={styles.control} data-ar-v3-group-start>
      <button type="button" className="am-button" onClick={onSend} disabled={pending}>
        Запустить шесть проверок АР v3
      </button>
      <p className="am-note">
        <em>
          Шесть отдельных прогонов; результат — предварительные цитаты для проверки экспертом,
          без числовых выводов.
        </em>
      </p>

      {pending ? <LoadingState what="запрос на шесть проверок" /> : null}

      {failure !== null && failure.presentation === 'unsupported' ? (
        <UnsupportedState
          title={failure.title}
          detail={
            <>
              <p data-ar-v3-group-failure={failure.kind}>{failure.detail}</p>
              {CLASSIFICATION_LINK_KINDS.has(failure.kind) ? (
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
              <p>Шесть проверок не запущены.</p>
            </>
          }
        />
      ) : null}

      {failure !== null && failure.presentation === 'error' ? (
        <ErrorState
          title={failure.title}
          detail={<span data-ar-v3-group-failure={failure.kind}>{failure.detail}</span>}
          correlationId={failure.correlationId}
          {...(failure.retryable ? { onRetry: onSend, retryLabel: 'Повторить с тем же ключом' } : {})}
        />
      ) : null}
    </div>
  );
}

export interface StartArV3GroupControlProps {
  /** The project the version belongs to, for the link a classification refusal carries. */
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** Called with the 202 group, so the mounting widget can open its review. */
  readonly onStarted?: ((group: ArV3BetaGroup) => void) | undefined;
}

export function StartArV3GroupControl({ projectUid, versionUid, onStarted }: StartArV3GroupControlProps) {
  const idempotencyKey = useIntentKey(`start-ar-v3-group:${versionUid}`);
  const mutation = useStartArV3Group();

  const send = () => {
    mutation.mutate(
      { versionUid, idempotencyKey },
      {
        onSuccess: (group) => {
          if (looksLikeArV3GroupId(group?.group_id)) onStarted?.(group);
        },
      },
    );
  };

  const malformed = mutation.isSuccess && !looksLikeArV3GroupId(mutation.data?.group_id);
  const failure: ArV3GroupStartFailure | null = malformed
    ? MALFORMED_GROUP_ANSWER
    : mutation.error === null || mutation.error === undefined
      ? null
      : classifyArV3GroupStartFailure(mutation.error);

  return (
    <StartArV3GroupView
      projectUid={projectUid}
      versionUid={versionUid}
      pending={mutation.isPending}
      failure={failure}
      onSend={send}
    />
  );
}
