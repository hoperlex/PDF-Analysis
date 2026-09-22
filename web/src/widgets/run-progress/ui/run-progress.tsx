'use client';

/**
 * Run progress.
 *
 * The one screen that polls, and it polls through `pollRunStatus` in `@/shared/api` —
 * the single loop, at the frozen 2 s / ×1.5 / 15 s schedule, with no deadline.
 *
 * What this widget is careful about:
 *
 *   **The state is the contract's word.** `RunStateBadge` renders `created`, `queued`,
 *   `running`, `validating`, `published`, `partial`, `failed` or `cancelled` and nothing
 *   else. There is no "in progress", no "done" and no "OK". `succeeded` is a stage
 *   status and appears only in the stage table below, where it is correct.
 *
 *   **`published` is the success terminal, and `partial` and `failed` borrow nothing
 *   from it.** A `partial` run states its recorded degradation set; a `failed` run states
 *   the catalog code it terminated with, and its interrupted reason when `OD-10`
 *   reconciled it.
 *
 *   **A recorded run never reads as a live one.** The provider mode sits on the badge and
 *   again as a sentence, and a reading that carries no recognised mode says `unknown` —
 *   never `live`.
 *
 *   **Motion stops when the run stops.** A terminal or reconciled reading shows no
 *   activity indicator, because there is no activity.
 *
 *   **The screen leads with what the run did, not with what the poller is doing.**
 *   `DEBT_REGISTER.md` `D-20` is open: `execute_run` is inline, so a run is already
 *   `published` when `startRun` answers and there is no observable `running` state to
 *   watch. Every real reading is therefore terminal, `isRunAnimating` is false, and the
 *   activity line reads "Not polling. This reading is final." That sentence is true, and
 *   it is the one thing on this screen a user cannot otherwise check, so it stays — but
 *   it sits below the result rather than above it. Leading a terminal run with a
 *   paragraph about polling puts machinery where the answer belongs.
 *
 *   **Two counts, never one.** Published findings are admitted evidence; diagnostic
 *   observations are what the run noticed and did not admit. They are rendered apart and
 *   never summed. The finding count stays inside `Outcome`, where it is scoped to the
 *   states that can have one — a `cancelled` run published nothing, and "Published
 *   findings: 0" would be a claim about a publication that never happened.
 *
 *   **A cost is never shown without the count it sums.** `D-15` is open: the total spans
 *   retry attempts. `runCost` returns `unreadable` rather than print a figure whose span
 *   the reader cannot see.
 */

import Link from 'next/link';

import type { RunStatus } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { ErrorState, LoadingState, NotApplicableState, RunStateBadge, STATE_LABELS } from '@/shared/ui';
import styles from './run-progress.module.css';

import {
  StageTable,
  badgeProviderMode,
  costBasisCaption,
  diagnosticObservationCount,
  elapsedMs,
  formatCostMicros,
  formatElapsed,
  interruptedReason,
  isRunAnimating,
  providerModeCaption,
  runCost,
  runHasPublishedResult,
  runOutcome,
  runProviderMode,
  stageRows,
  terminalReasonNote,
  useRunStatus,
} from '@/entities/audit-run';

export interface RunProgressProps {
  readonly projectUid: string;
  readonly runId: string;
}

function Outcome({ status }: { readonly status: RunStatus }) {
  const outcome = runOutcome(status);

  switch (outcome.kind) {
    case 'in_flight':
      return (
        <p className={styles.outcome} data-run-outcome="in_flight">
          Прогон в состоянии{' '}
          <span data-run-state={outcome.state}>{STATE_LABELS[outcome.state]}</span>. Результат
          ещё не опубликован и не подразумевается.
        </p>
      );
    case 'published':
      return (
        <div className={styles.outcome} data-run-outcome="published">
          <p>
            Прогон достиг успешного терминального состояния{' '}
            <span data-run-state="published">{STATE_LABELS.published}</span>.
          </p>
          <p>
            Опубликованных находок:{' '}
            {outcome.findingCount === null ? <em>не сообщено</em> : outcome.findingCount}
          </p>
        </div>
      );
    case 'partial':
      return (
        <div className={styles.outcome} data-run-outcome="partial">
          <p>
            Прогон завершился как <span data-run-state="partial">{STATE_LABELS.partial}</span>. Он опубликовал результат с
            зафиксированной деградацией: часть этапов не выполнена, и это не{' '}
            <span data-run-state="published">{STATE_LABELS.published}</span>.
          </p>
          {outcome.degradation.length === 0 ? (
            <p>
              <em>Показание не содержит списка деградаций.</em>
            </p>
          ) : (
            <>
              <p>Отсутствующие или деградировавшие этапы:</p>
              <ul>
                {outcome.degradation.map((stageId) => (
                  <li key={stageId} data-degraded-stage={stageId}>
                    <code>{stageId}</code>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      );
    case 'failed': {
      // The identifier and the sentence, in that order and both of them. An operator
      // quoting the code into an issue needs the code; a person reading the screen needs
      // the sentence. `W28-LIVE` measured this block printing only the first.
      const note = terminalReasonNote(outcome.terminalReason);
      return (
        <div className={styles.outcome} data-run-outcome="failed">
          <p>
            Прогон завершился как <span data-run-state="failed">{STATE_LABELS.failed}</span>. Ничего не опубликовано.
          </p>
          <p>
            Терминальная причина:{' '}
            {outcome.terminalReason === null ? (
              <em>не сообщено</em>
            ) : (
              <code data-terminal-reason={outcome.terminalReason}>{outcome.terminalReason}</code>
            )}
          </p>
          <p data-terminal-reason-note={note.kind}>{note.sentence}</p>
          {outcome.interrupted === null ? null : (
            <p data-interrupted-reason={outcome.interrupted}>
              Прогон был прерван и сверен: {outcome.interrupted}. Сейчас он не выполняется.
            </p>
          )}
        </div>
      );
    }
    case 'cancelled':
      return (
        <p className={styles.outcome} data-run-outcome="cancelled">
          Прогон завершился как <span data-run-state="cancelled">{STATE_LABELS.cancelled}</span>. Ничего не опубликовано.
        </p>
      );
  }
}

/**
 * What the run recorded and what it spent.
 *
 * Two counts that are never added together and a cost that is never invented.
 */
function Recorded({ status }: { readonly status: RunStatus }) {
  const diagnostics = diagnosticObservationCount(status);
  const cost = runCost(status);

  return (
    <>
      <h2>Диагностические наблюдения</h2>
      <p>
        Зарегистрировано:{' '}
        {diagnostics === null ? (
          <em data-diagnostic-observation-count="not-reported">не сообщено</em>
        ) : (
          <strong data-diagnostic-observation-count={diagnostics}>{diagnostics}</strong>
        )}
      </p>
      <p>
        Диагностическое наблюдение — это то, что прогон заметил, но не принял как
        свидетельство. Это не находка, оно не считается находкой, и два итога никогда
        не складываются.
      </p>

      <h2>Стоимость</h2>
      {cost.kind === 'absent' ? (
        <p data-run-cost="absent">
          Прогон не обращался к провайдеру, поэтому сообщать о стоимости нечего. Это не
          нулевая стоимость: здесь ничего не потрачено, потому что ничего не вызывалось,
          а это разные утверждения.
        </p>
      ) : cost.kind === 'unreadable' ? (
        <p data-run-cost="unreadable">
          Стоимость этого показания прочитать нельзя: {cost.why}. Цифра не показана, потому
          что итог, охват которого читателю не виден, не годится для решений.
        </p>
      ) : (
        <div data-run-cost="reported">
          <dl>
            <dt>Потрачено</dt>
            <dd data-cost-micros={cost.micros}>
              <strong>{formatCostMicros(cost.micros)}</strong> единиц валюты провайдера{' '}
              <span>
                (<code>{cost.micros}</code> миллионных — целое число, сохранённое прогоном)
              </span>
            </dd>
            <dt>Вызовов провайдера в сумме</dt>
            <dd data-model-call-count={cost.callCount}>{cost.callCount}</dd>
            <dt>Основание</dt>
            <dd data-cost-basis={cost.basis ?? 'unstated'}>
              <code>{cost.basis ?? 'unstated'}</code>
            </dd>
          </dl>
          <p>{costBasisCaption(cost.basis)}</p>
          <p>
            Итог суммирует все обращения к провайдеру, включая повторы. Рядом напечатано
            число вызовов, чтобы прогон, ответивший с первого раза, отличался от того,
            который пришлось повторять.
          </p>
          {cost.micros === 0 ? (
            <p data-run-cost-zero="reported">
              Прогон обратился к провайдеру{' '}
              {cost.callCount === 1 ? 'один раз' : `${cost.callCount} раз`}, и плата не
              начислена. Это сообщённый ноль, а не отсутствующая стоимость.
            </p>
          ) : null}
        </div>
      )}
    </>
  );
}

export function RunProgress({ projectUid, runId }: RunProgressProps) {
  const { status, failure, polling, retry } = useRunStatus(runId);

  if (status === null && failure !== null) {
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-run-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable ? { onRetry: retry, retryLabel: 'Повторить' } : {})}
      />
    );
  }

  if (status === null) return <LoadingState what="прогон" />;

  const mode = runProviderMode(status);
  const animating = isRunAnimating(status);
  const interrupted = interruptedReason(status);

  return (
    <div data-run-id={status.run_id}>
      <p className={styles.mode}>
        <RunStateBadge state={status.state} providerMode={badgeProviderMode(mode)} />
        <span data-provider-mode={mode}>
          режим провайдера: <strong>{mode}</strong>
        </span>
      </p>
      <p>{providerModeCaption(mode)}</p>

      <dl>
        <dt>Прогон</dt>
        <dd>
          <code>{status.run_id}</code>
        </dd>
        <dt>Версия</dt>
        <dd>
          <code>{status.version_uid}</code>
        </dd>
        <dt>Создан</dt>
        <dd>{formatInstant(status.created_at)}</dd>
        <dt>Завершён</dt>
        <dd>{formatInstant(status.terminal_at)}</dd>
        <dt>Длительность</dt>
        <dd data-run-elapsed={elapsedMs(status.created_at, status.terminal_at) ?? 'unknown'}>
          {formatElapsed(elapsedMs(status.created_at, status.terminal_at))}
        </dd>
      </dl>

      <p>
        <Link href={routes.version(status.project_uid, status.version_uid)}>
          Версия, которую читал прогон
        </Link>{' '}
        — <code>{status.version_uid}</code>. Прогон никогда не меняет прочитанную версию,
        и остальные её прогоны перечислены там же.
      </p>

      <Outcome status={status} />

      {interrupted !== null && status.state !== 'failed' ? (
        <p data-interrupted-reason={interrupted}>
          У прогона указана причина прерывания: {interrupted}.
        </p>
      ) : null}

      <Recorded status={status} />

      <h2>Этапы</h2>
      <StageTable rows={stageRows(status)} />

      <h2>Разбор</h2>
      {runHasPublishedResult(status.state) ? (
        <p>
          <Link href={routes.review(projectUid, status.run_id)}>Разобрать находки</Link>{' '}
          — режим провайдера этого прогона: <strong>{mode}</strong>.
        </p>
      ) : (
        <NotApplicableState
          title="Разбирать нечего."
          detail={
            <p>
              Находки появляются только когда терминальное состояние публикует результат —{' '}
              <span data-run-state="published">{STATE_LABELS.published}</span> или{' '}
              <span data-run-state="partial">{STATE_LABELS.partial}</span>. Этот прогон —{' '}
              <span data-run-state={status.state}>{STATE_LABELS[status.state]}</span>.
            </p>
          }
        />
      )}

      <h2>Показание окончательное?</h2>
      <p className={styles.activity} data-run-activity={animating && polling ? 'polling' : 'stopped'}>
        {animating && polling
          ? 'Идёт опрос следующего показания. Интервал растёт с 2 с до 15 с, срока нет; опрос прекращается, когда прогон достигает терминального состояния.'
          : animating
            ? 'Опрос остановлен, но прогон ещё открыт. Показание выше — последнее полученное, а не окончательное.'
            : 'Опрос остановлен, показание окончательное.'}
      </p>

      {failure !== null ? (
        <ErrorState
          title={failure.title}
          detail={
            <span data-run-failure={failure.kind}>
              {failure.detail} Показание выше — последнее полученное.
            </span>
          }
          correlationId={failure.correlationId}
          {...(failure.retryable ? { onRetry: retry, retryLabel: 'Повторить' } : {})}
        />
      ) : null}
    </div>
  );
}
