'use client';

/**
 * Run progress.
 *
 * The one screen that polls, and it polls through `pollRunStatus` in `@/shared/api` --
 * the single loop, at the frozen 2 s / x1.5 / 15 s schedule, with no deadline.
 *
 * `RUN-SCREEN-01a` (plan `executors-runs-rework-plan` §9) rebuilt the layout on the same data; the rules below are the ones it kept.
 * The screen is a head over two tabs: the head states the run (its state, the stage it is on, a bar, the estimated finish, the live
 * line and the rail of chips) and what to do next; «Обзор» holds the findings and spend tiles, the outcome, the queue card and a folded
 * «Подробнее»; «Журнал» holds the run's events. A chip opens «Этапы анализа раздела», which holds the stage table, the planned
 * procedures, the executor and the preset.
 *
 * What this widget is careful about:
 *
 *   **The state is the contract's word.** `RunStateBadge` renders `created`, `queued`,
 *   `running`, `validating`, `published`, `partial`, `failed` or `cancelled` and nothing
 *   else. There is no "in progress", no "done" and no "OK". `succeeded` is a stage
 *   status and appears only in the stage table, in the dialog, where it is correct.
 *
 *   **`published` is the success terminal, and `partial` and `failed` borrow nothing
 *   from it.** A `partial` run states its recorded degradation set; a `failed` run states
 *   the catalog code it terminated with, and its interrupted reason when `OD-10`
 *   reconciled it.
 *
 *   **A recorded run still says so.** The provider mode no longer sits on the head's badge (plan §9.1); it is a row of «Подробнее»
 *   with its sentence, and a missing or unrecognised mode has its own label there, neither of which can be mistaken for `live`. A recorded
 *   run also carries the small chip «из записи» in the head, beside its state (`WEB-INT-1`, the owner's rule that a recorded run must
 *   not look live); a live run draws nothing there.
 *
 *   **Motion stops when the run stops.** A terminal or reconciled reading shows no live line, because there is no activity. The
 *   head keeps `data-run-activity` (`polling` or `stopped`) for the browser journey, which reads it, and says a sentence only for the
 *   one case a reader must not miss: the poll has stopped while the run is still open, so the reading is the last one received.
 *
 *   **Two counts, never one.** Published findings are admitted evidence; diagnostic
 *   observations are what the run noticed and did not admit. They are rendered apart and
 *   never summed. The finding count stays inside `Outcome`, where it is scoped to the
 *   states that can have one -- a `cancelled` run published nothing, and "Published
 *   findings: 0" would be a claim about a publication that never happened.
 *
 *   **The worker is named only while one can hold the run.** In `running` and `validating`
 *   the run's Job holds a Lease, and `RunHolder` reads the worker registry when it mounts
 *   and on tab return, never on the poll, to name the worker whose `current_run_ids` lists
 *   the run (`W54-WORKERS-WEB`). In any other state no worker holds it and nothing is read.
 *
 *   **The executor is named only when the reading carries one.** `EXEC-PAR-WEB-01`: a run that
 *   froze a connection shows its name and pinned model in the dialog and the live line, and a run in the queue
 *   says it is waiting for that executor. A run with none -- every run on the environment source
 *   -- shows no row and no placeholder, because a screen that cannot say which executor does not
 *   say one. The read-only role is shown no server (`R-150w`).
 *
 *   **A cost is never shown without the count it sums.** `D-15` is open: the total spans
 *   retry attempts. `runCost` returns `unreadable` rather than print a figure whose span
 *   the reader cannot see; the spend tile and the notes follow it.
 */

import Link from 'next/link';
import { useState } from 'react';
import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';

import type { RunStatus } from '@/shared/api';
import { isTerminalRunState } from '@/shared/api';
import { SHOW_REVIEW_INDICATION } from '@/shared/config';
import { formatInstant, routes } from '@/shared/lib';
import { useMe } from '@/entities/account';
import { RunWorkerLine, runHoldsLease, runWorker, useWorkerLookup } from '@/entities/execution';
import { GroupWaitDetail } from '@/entities/executor-group';
import { groupByCategory, runFindingsQueryOptions, SEVERITY_LABELS } from '@/entities/finding';
import { tallySeverity } from '@/widgets/finding-list';
import { NormReferencesSection } from '@/widgets/norm-references';
import { RunStagesDialog } from '@/widgets/run-stages-dialog';
import { ExtendedReview, useExtendedReviewReading } from '@/widgets/extended-review';
import {
  ErrorState,
  LoadingState,
  NotApplicableState,
  STATE_LABELS,
  COST_BASIS_LABELS,
  microsAsUsd,
  runStageLabel,
  PROVIDER_MODE_LABELS,
  PROVIDER_MODE_UNKNOWN_LABEL,
} from '@/shared/ui';
import {
  arV3GroupReviewAddress,
  costBasisCaption,
  diagnosticObservationCount,
  elapsedMs,
  formatCostMicros,
  formatElapsed,
  groupDigits,
  hasKnownRunVocabulary,
  interruptedReason,
  isRunAnimating,
  looksLikeArV3GroupId,
  extendedLiveProgress,
  procedureReadings,
  providerModeCaption,
  runAnalysis,
  runAnalysisKind,
  runChips,
  runCost,
  runExecutorLine,
  runHasPublishedResult,
  runOutcome,
  runProviderMode,
  runQueueReasonLabel,
  runWaitingSentence,
  shortModelName,
  terminalReasonNote,
  useArV3StartAllowed,
  useRunStatus,
} from '@/entities/audit-run';
import type { RunChipDefinition } from '@/entities/audit-run';

import styles from './run-progress.module.css';
import { PdfPrecheckProgress } from './pdf-precheck-progress';
import { RunHeader } from './run-header';
import { RunNextTask } from './run-next-task';
import { RunTabs } from './run-tabs';
import { startedFrom } from '../model/started-from';
import { maySeeServer } from '../model/server-access';
import type { RunTab } from '../model/run-tabs';

export interface RunProgressProps {
  readonly projectUid: string;
  readonly runId: string;
  /** The page's own controls for this run («Отменить прогон»), beside the review call in the head. */
  readonly actions?: ReactNode;
  /**
   * The run's events, for the «Журнал» tab (`UI-B-39`). The page decides whether the account may read the journal (`R-150w`) and
   * passes it only then: with none the tab is not drawn, as it was not before for a read-only account.
   */
  readonly journal?: ReactNode;
}

/** The worker holding a running or validating run, read from the registry's first page. */
function RunHolder({ runId }: { readonly runId: string }) {
  const workers = useWorkerLookup(true);
  return <RunWorkerLine worker={runWorker(workers.data, workers.error !== null, runId)} />;
}

const UNKNOWN_RUN_TITLE = 'Прогон содержит неизвестное значение.';

/**
 * The second sentence of a published AR v3 beta Run (`R-146as`, `R-146ba`).
 *
 * A Run whose reading carries at least one published finding says so and who decides on it; a Run
 * that publishes none (a count of zero, or a count the server did not report) keeps the sentence that
 * says no canonical finding is published here. The words that call a citation provisional or say
 * it needs the expert are `SHOW_REVIEW_INDICATION`'s: with it off they are left out and nothing else
 * changes. «решение по каждой записывает эксперт» is not one of them: it says whose decision a verdict is.
 */
function V3PublishedSentence({ findingCount }: { readonly findingCount: number | null }) {
  if (findingCount !== null && findingCount > 0) {
    return SHOW_REVIEW_INDICATION ? (
      <p>Находки с предварительными нормативными ссылками опубликованы; решение по каждой записывает эксперт. Числовой или правовой вывод не утверждён.</p>
    ) : (
      <p>Находки с нормативными ссылками опубликованы; решение по каждой записывает эксперт. Числовой или правовой вывод не утверждён.</p>
    );
  }
  return SHOW_REVIEW_INDICATION ? (
    <p>Канонические находки здесь не публикуются. Каждая тема и цитата требует проверки эксперта; числовой или правовой вывод не утверждён.</p>
  ) : (
    <p>Канонические находки здесь не публикуются. Числовой или правовой вывод не утверждён.</p>
  );
}

/**
 * `AR-V3-OPT-IN`: «Анализ» in the run's facts -- which analysis produced it. A run of AR v3 (beta) always says so, with its
 * scope, and links to the review of its group; a standard run says «Стандартный» only where the deployment allows a
 * start of v3 (`start_allowed`), so a deployment with one analysis shows no line about the other. Only a standard run asks
 * the server whether v3 is allowed; a v3 run needs no answer.
 */
function AnalysisFact({ status }: { readonly status: RunStatus }) {
  return runAnalysisKind(status) === 'standard' ? <StandardAnalysisFact status={status} /> : <AnalysisLine status={status} />;
}

/** The only run page that asks the server: a standard run, to learn whether there is another analysis to tell it from. */
function StandardAnalysisFact({ status }: { readonly status: RunStatus }) {
  return useArV3StartAllowed() ? <AnalysisLine status={status} /> : null;
}

function AnalysisLine({ status }: { readonly status: RunStatus }) {
  const analysis = runAnalysis(status);
  return (
    <>
      <dt>Анализ</dt>
      <dd data-run-analysis={analysis.kind} data-run-scope={analysis.scope ?? undefined}>
        {analysis.label}
        {looksLikeArV3GroupId(analysis.groupId) ? (
          <>
            {' · '}
            <Link href={arV3GroupReviewAddress(analysis.groupId)} data-run-group-review>
              шесть проверок группы
            </Link>
          </>
        ) : null}
      </dd>
    </>
  );
}

function Outcome({ status }: { readonly status: RunStatus }) {
  const outcome = runOutcome(status);
  const v3Beta = runAnalysisKind(status) === 'ar_v3_beta';

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
      if (v3Beta) return (
        <div className={styles.outcome} data-run-outcome="published" data-review-only="ar-v3-beta">
          <p>{SHOW_REVIEW_INDICATION ? 'Прогон завершён. Предварительный нормативный разбор АР v3 сохранён.' : 'Прогон завершён. Нормативный разбор АР v3 сохранён.'}</p>
          <V3PublishedSentence findingCount={outcome.findingCount} />
        </div>
      );
      return (
        <div className={styles.outcome} data-run-outcome="published">
          <p>
            Прогон достиг успешного терминального состояния{' '}
            <span data-run-state="published">{STATE_LABELS.published}</span>. Опубликованных находок:{' '}
            {outcome.findingCount === null ? <em>не сообщено</em> : outcome.findingCount}
          </p>
        </div>
      );
    case 'partial':
      if (v3Beta) return (
        <div className={styles.outcome} data-run-outcome="partial" data-review-only="ar-v3-beta">
          <p>{SHOW_REVIEW_INDICATION ? 'Предварительный нормативный разбор АР v3 завершился частично. Полный проверенный результат не подтверждён.' : 'Нормативный разбор АР v3 завершился частично. Полный проверенный результат не подтверждён.'}</p>
          <p>{SHOW_REVIEW_INDICATION ? 'Канонические находки не публикуются; требуется проверка эксперта.' : 'Канонические находки не публикуются.'}</p>
        </div>
      );
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
                {/*
                 * The stage's name, not its id. `D-62`: the machine value stays in
                 * `data-degraded-stage`, where the journey and `PA-01` criterion 4 read
                 * it, and the reviewer reads a word. This list is the second consumer
                 * `STAGE_LABELS` had on the day it was written, which is why that map was
                 * exported from `shared/ui` rather than kept private — `VERDICT_LABELS`
                 * and `STATE_LABELS` each had to be exported after a second consumer had
                 * already rendered the raw value.
                 */}
                {outcome.degradation.map((stageId) => (
                  <li key={stageId} data-degraded-stage={stageId}>
                    {runStageLabel(stageId)}
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
      {cost.kind === 'absent' && !isTerminalRunState(status.state) ? (
        <p data-run-cost="pending">Стоимость появится по ходу прогона.</p>
      ) : cost.kind === 'absent' ? (
        <p data-run-cost="absent">
          Прогон не обращался к провайдеру, поэтому сообщать о стоимости нечего. Это не
          нулевая стоимость: здесь ничего не потрачено, потому что ничего не вызывалось,
          а это разные утверждения.
        </p>
      ) : cost.kind === 'unmetered' ? (
        // `EXEC-SEAL-01`: only the caption. No figure, no basis row and no «сообщённый ноль».
        <p data-run-cost="unmetered" data-cost-basis="unmetered">
          {costBasisCaption('unmetered')}
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
              {cost.basis === null
                ? 'не указано'
                : cost.basis === 'unrecognized'
                  ? 'неизвестное значение'
                  : COST_BASIS_LABELS[cost.basis]}
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

/**
 * The tile «Находки» (`R-151j`): the run's findings by the severity the expert decided, read from the same complete list «Разбор»
 * reads (`runFindingsQueryOptions`, one cache entry), and the way into «Разбор». Counts are over the whole run. A finding without a
 * decided severity is «Не определена»; the model's proposals are not counted here (they are on «Разбор», under their own label).
 * Until the list has been read, or when it cannot be, the tile shows only the way in: it claims no count it has not got.
 */
function FindingsTile({ projectUid, status }: { readonly projectUid: string; readonly status: RunStatus }) {
  const findings = useQuery(runFindingsQueryOptions(status.run_id));
  const items = findings.data?.data.items;
  const tally = items === undefined ? null : tallySeverity(groupByCategory(items));
  const strip = tally === null
    ? []
    : [
        ...(['critical', 'economic', 'operational', 'recommendation', 'check_adjacent'] as const).map((value) => ({
          key: value, label: SEVERITY_LABELS[value], count: tally.decided[value],
        })),
        { key: 'undetermined', label: 'Не определена', count: tally.decided.undetermined },
      ].filter((entry) => entry.count > 0);
  return (
    <section className={styles.tile} aria-label="Находки" data-run-findings-tile="">
      <h2>Находки</h2>
      {strip.length === 0 ? null : (
        <ul className={styles.severities} aria-label="Важность, решённая экспертом" data-severity-strip="">
          {strip.map((entry) => (
            <li key={entry.key} className={styles.severity} data-severity={entry.key}>
              {entry.label} {entry.count}
            </li>
          ))}
        </ul>
      )}
      <p className={styles.tileLink}>
        <Link href={routes.review(projectUid, status.run_id)}>в Разбор →</Link>
      </p>
    </section>
  );
}

/**
 * The tile «Расход»: the totals, and only the totals the reading has. A figure is printed with the number of calls it sums
 * (`D-15`); a run on a subscription connection has no figure and says so; a run that called no provider has nothing to report, which is
 * not a zero. The reading has no token counts, so none are shown. The sentences that qualify these figures are in «Пояснения к цифрам».
 */
function SpendTile({ status }: { readonly status: RunStatus }) {
  const cost = runCost(status);
  return (
    <section className={styles.tile} aria-label="Расход" data-run-spend={cost.kind}>
      <h2>Расход</h2>
      {cost.kind === 'reported' ? (
        <p className={styles.spend}>
          <span className={styles.spendFigure} data-spend-micros={cost.micros}>{`$${microsAsUsd(cost.micros)}`}</span>
          <span className={styles.spendNote}>
            вызовов {groupDigits(cost.callCount)}
            {cost.basis === null ? '' : cost.basis === 'unrecognized' ? ' · основание: неизвестное значение' : ` · ${COST_BASIS_LABELS[cost.basis]}`}
          </span>
        </p>
      ) : cost.kind === 'unmetered' ? (
        <p className={styles.spendNote}>
          По подписке. {costBasisCaption('unmetered')}
          {cost.callCount === null ? '' : ` Вызовов: ${groupDigits(cost.callCount)}.`}
        </p>
      ) : cost.kind === 'unreadable' ? (
        <p className={styles.spendNote}>Стоимость прочитать нельзя; причина — в «Подробнее», «Пояснения к цифрам».</p>
      ) : isTerminalRunState(status.state) ? (
        <p className={styles.spendNote}>Прогон не обращался к провайдеру.</p>
      ) : (
        // An open run has not finished calling: «не обращался» is a claim about a finished run (`RUN-SCREEN-FIX-01`).
        <p className={styles.spendNote} data-run-spend-pending="">Появится по ходу прогона.</p>
      )}
    </section>
  );
}

export function RunProgress({ projectUid, runId, actions, journal }: RunProgressProps) {
  const { status, failure, polling, retry } = useRunStatus(runId);
  const me = useMe();
  const reading = useExtendedReviewReading(runId);
  const [tab, setTab] = useState<RunTab>('overview');
  const [dialogChip, setDialogChip] = useState<RunChipDefinition['id'] | null>(null);

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

  if (!hasKnownRunVocabulary(status)) {
    return (
      <div data-run-progress-fault="closed-vocabulary">
        <ErrorState
          title={UNKNOWN_RUN_TITLE}
          detail="Состояние прогона или этапа нельзя показать достоверно — показание скрыто."
        />
      </div>
    );
  }

  const mode = runProviderMode(status);
  const modeText = mode === 'unknown'
    ? PROVIDER_MODE_UNKNOWN_LABEL
    : mode === 'unrecognized'
      ? 'неизвестное значение'
      : PROVIDER_MODE_LABELS[mode];
  const animating = isRunAnimating(status);
  const interrupted = interruptedReason(status);
  const executor = runExecutorLine(status);
  const from = startedFrom(status);
  const v3Beta = runAnalysisKind(status) === 'ar_v3_beta';
  const reviewable = !v3Beta && runHasPublishedResult(status.state, status.analysis_profile_id);
  const showServer = maySeeServer(me.data?.roles);
  const modelShort = shortModelName(executor?.model);
  const pin = executor?.model ?? null;
  const model = modelShort === null || pin === null ? null : { short: modelShort, pin };
  const chips = runChips({
    status,
    procedures: procedureReadings(reading?.result),
    reused: from === null ? undefined : from.reusedStageIds,
  });
  const liveProgress = extendedLiveProgress(reading?.result);
  const cost = runCost(status);
  const tabs: readonly RunTab[] = journal === undefined ? ['overview'] : ['overview', 'journal'];
  const active: RunTab = tabs.includes(tab) ? tab : 'overview';

  const overview = (
    <>
      <div className={styles.tiles}>
        {reviewable ? (
          <FindingsTile projectUid={projectUid} status={status} />
        ) : (
          <section className={styles.tile} aria-label="Находки" data-run-findings-tile="">
            <h2>Находки</h2>
            {v3Beta ? (
              <NotApplicableState
                title={SHOW_REVIEW_INDICATION ? 'Предварительный разбор АР v3' : 'Разбор АР v3'}
                detail={
                  <p>
                    Для просмотра шести прогонов откройте «Настройки анализа» и укажите идентификатор группы из ответа запуска. Здесь нет канонических находок для разбора или принятия решения.
                  </p>
                }
              />
            ) : !isTerminalRunState(status.state) ? (
              // An open run has no result yet; «Разбирать нечего» is the sentence of a run that ended without one (`RUN-SCREEN-FIX-01`).
              <p className={styles.spendNote} data-run-findings-pending="">Появятся по ходу прогона.</p>
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
          </section>
        )}
        <SpendTile status={status} />
      </div>

      <Outcome status={status} />

      {interrupted !== null && status.state !== 'failed' ? (
        <p data-interrupted-reason={interrupted}>
          У прогона указана причина прерывания: {interrupted}.
        </p>
      ) : null}

      {/* `UI-B-70`: a run that waits in the queue says what goes first and why it waits, as the original's «Следующая задача». */}
      {status.state === 'queued' ? <RunNextTask status={status} /> : null}

      {/* Folded: the run's identity, the checks that precede it, the norms it cites, the full analysis and the notes on the figures. */}
      <details className={styles.more} data-run-more="" open={cost.kind === 'unreadable'}>
        <summary className={styles.moreSummary}>Подробнее</summary>
        <div className={styles.moreBody}>
          <section className={styles.panel} aria-label="Сведения о прогоне">
            <h2>Сведения о прогоне</h2>
            <p className={styles.caption}>{providerModeCaption(mode)}</p>
            <dl className={styles.facts}>
              <dt>Прогон</dt>
              <dd><code>{status.run_id}</code></dd>
              <dt>Версия</dt>
              <dd>
                <Link href={routes.version(status.project_uid, status.version_uid)}>
                  <code>{status.version_uid}</code>
                </Link>
              </dd>
              <AnalysisFact status={status} />
              <dt>Режим провайдера</dt>
              <dd><strong data-provider-mode={mode}>{modeText}</strong></dd>
              {/* `R-151v`: who started the run; a run created before contract 1.21.0 does not know. */}
              <dt>Запустил</dt>
              <dd data-run-started-by={status.started_by_user_uid ?? 'unknown'}>{status.started_by_label ?? 'неизвестно'}</dd>
              <dt>Создан</dt>
              <dd>{formatInstant(status.created_at)}</dd>
              <dt>Завершён</dt>
              <dd>{formatInstant(status.terminal_at)}</dd>
              <dt>Длительность</dt>
              <dd data-run-elapsed={elapsedMs(status.created_at, status.terminal_at) ?? 'unknown'}>
                {formatElapsed(elapsedMs(status.created_at, status.terminal_at))}
              </dd>
            </dl>
            {runHoldsLease(status.state) ? <RunHolder runId={status.run_id} /> : null}
            <p className={styles.caption}>
              Прогон никогда не меняет прочитанную версию; остальные её прогоны перечислены на её странице.
            </p>
          </section>

          <PdfPrecheckProgress status={status} />

          {/* `NORM-REFS-RUN-01`: the norms the stored run's text cites. Only once the run has stopped;
              while it is in flight its text layer may not exist yet, and «нет текстового слоя»
              would be a claim about a run that has not got that far. */}
          {isTerminalRunState(status.state) ? <NormReferencesSection runId={status.run_id} /> : null}

          <ExtendedReview key={runId} runId={runId} active={animating} projectUid={projectUid} planElsewhere />

          {/*
            The sentences that qualify the figures stay on the screen and are read when asked for, as the CSV columns are
            on the export bar (`R-18`). They open by themselves when the cost cannot be read, because that sentence is
            the only place the screen says why no figure is shown.
          */}
          <section className={styles.notes} aria-label="Пояснения к цифрам">
            <details open={cost.kind === 'unreadable'} data-run-notes="">
              <summary className={styles.notesSummary}>Пояснения к цифрам</summary>
              <Recorded status={status} />
            </details>
          </section>
        </div>
      </details>
    </>
  );

  return (
    <div className={styles.progress} data-run-id={status.run_id}>
      <RunHeader
        status={status}
        chips={chips}
        executor={executor}
        model={model}
        showServer={showServer}
        liveProgress={liveProgress}
        recorded={mode === 'recorded'}
        polling={polling}
        from={from}
        waiting={status.state === 'queued' ? (executor === null ? runQueueReasonLabel(status) : runWaitingSentence(executor)) : null}
        waitDetail={
          status.state === 'queued' && executor !== null && executor.phase === 'planned' ? (
            <GroupWaitDetail
              groupId={status.planned?.executor_group_id}
              revisionId={status.planned?.executor_group_revision_id}
              waitReason={executor.queueReason ?? null}
            />
          ) : null
        }
        actions={
          <>
            {reviewable ? (
              <Link className="am-button" href={routes.review(projectUid, status.run_id)}>
                Разобрать находки
              </Link>
            ) : null}
            {actions}
          </>
        }
        onOpenChip={setDialogChip}
      />

      {failure !== null ? (
        <ErrorState
          title={failure.title}
          detail={
            <span data-run-failure={failure.kind}>
              {failure.detail} Показание ниже — последнее полученное.
            </span>
          }
          correlationId={failure.correlationId}
          {...(failure.retryable ? { onRetry: retry, retryLabel: 'Повторить' } : {})}
        />
      ) : null}

      {tabs.length < 2 ? (
        overview
      ) : (
        <RunTabs tabs={tabs} active={active} onSelect={setTab}>
          {active === 'journal' ? journal : overview}
        </RunTabs>
      )}

      {dialogChip === null ? null : (
        <RunStagesDialog
          status={status}
          chips={chips}
          selected={dialogChip}
          onSelect={setDialogChip}
          onClose={() => setDialogChip(null)}
          reusedStageIds={from === null ? undefined : from.reusedStageIds}
          showServer={showServer}
        />
      )}
    </div>
  );
}
