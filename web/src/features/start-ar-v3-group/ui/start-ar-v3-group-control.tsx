'use client';

/**
 * Start the six AR v3 checks over one published version.
 *
 * It is the group's counterpart of `StartRunControl` and borrows its discipline: one
 * idempotency key per intent, a retry under the same key and nothing else, no provider-mode
 * selector, no pack selection and no text input. Unlike `StartRunControl` it holds neither the
 * key nor the mutation: it is drawn only on an installed pack or while a start is pending, and
 * can be taken off the page by a failed status re-read or by the list around it loading, so the
 * caller holds the key, the mutation's observer and whether a request is pending
 * (`useArV3GroupStartIntent`) and hands them in. On failure the refusal is
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
import { SHOW_REVIEW_INDICATION } from '@/shared/config';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeArV3GroupId } from '@/entities/audit-run';

import type { ArV3GroupStartFailure } from '../model/start-failure';
import {
  CLASSIFICATION_LINK_KINDS,
  MALFORMED_GROUP_ANSWER,
  classifyArV3GroupStartFailure,
} from '../model/start-failure';
import type { ArV3GroupStartIntent } from '../model/use-ar-v3-group-start-intent';

import styles from './start-ar-v3-group-control.module.css';

export interface StartArV3GroupViewProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  readonly pending: boolean;
  readonly failure: ArV3GroupStartFailure | null;
  readonly onSend: () => void;
  readonly relaxedLimits?: boolean | undefined;
  readonly onRelaxedLimitsChange?: ((value: boolean) => void) | undefined;
}

export function StartArV3GroupView({
  projectUid,
  versionUid,
  pending,
  failure,
  onSend,
  relaxedLimits = false,
  onRelaxedLimitsChange,
}: StartArV3GroupViewProps) {
  return (
    <div className={styles.control} data-ar-v3-group-start>
      <label className={styles.limitToggle}>
        <input
          type="checkbox"
          checked={relaxedLimits}
          disabled={pending || onRelaxedLimitsChange === undefined}
          onChange={(event) => onRelaxedLimitsChange?.(event.currentTarget.checked)}
        />
        Повышенные лимиты ИИ-анализа
      </label>
      <p className="am-note">
        {relaxedLimits
          ? 'Бюджет стоимости отключён; ответ до 64 000 токенов. Провайдер может установить меньший предел.'
          : 'Стандартный бюджет стоимости; ответ до 16 000 токенов.'}
      </p>
      <button type="button" className="am-button" onClick={onSend} disabled={pending}>
        Запустить шесть проверок АР v3
      </button>
      <p className="am-note">
        <em>
          {SHOW_REVIEW_INDICATION
            ? 'Шесть отдельных прогонов; результат — предварительные цитаты для проверки экспертом, без числовых выводов.'
            : 'Шесть отдельных прогонов; результат — нормативные цитаты, без числовых выводов.'}
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
  /** Held by the caller, so the key, the observer and the answer outlive this control; see `useArV3GroupStartIntent`. */
  readonly intent: ArV3GroupStartIntent;
  /** Called with the 202 group, so the mounting widget can open its review. */
  readonly onStarted?: ((group: ArV3BetaGroup) => void) | undefined;
}

export function StartArV3GroupControl({
  projectUid,
  versionUid,
  intent,
  onStarted,
}: StartArV3GroupControlProps) {
  const { mutation } = intent;

  const send = () => {
    mutation.mutate(
      { versionUid, idempotencyKey: intent.idempotencyKey, relaxedLimits: intent.relaxedLimits },
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
      // A start this control did not send (an earlier mount of the list) still blocks a second.
      pending={mutation.isPending || intent.inFlight}
      failure={failure}
      onSend={send}
      relaxedLimits={intent.relaxedLimits}
      onRelaxedLimitsChange={intent.setRelaxedLimits}
    />
  );
}
