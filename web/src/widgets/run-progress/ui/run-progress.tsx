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
 *   again as a sentence. Missing and unrecognised modes have different labels, neither
 *   of which can be mistaken for `live`.
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
 *   **The worker is named only while one can hold the run.** In `running` and `validating`
 *   the run's Job holds a Lease, and `RunHolder` reads the worker registry when it mounts
 *   and on tab return, never on the poll, to name the worker whose `current_run_ids` lists
 *   the run (`W54-WORKERS-WEB`). In any other state no worker holds it and nothing is read.
 *
 *   **The executor is named only when the reading carries one.** `EXEC-PAR-WEB-01`: a run that
 *   froze a connection shows its name and pinned model in the run's facts, and a run in the queue
 *   says it is waiting for that executor. A run with none — every run on the environment source
 *   — shows no row and no placeholder, because a screen that cannot say which executor does not
 *   say one.
 *
 *   **A cost is never shown without the count it sums.** `D-15` is open: the total spans
 *   retry attempts. `runCost` returns `unreadable` rather than print a figure whose span
 *   the reader cannot see.
 */

import Link from 'next/link';
import type { ReactNode } from 'react';

import type { RunStatus } from '@/shared/api';
import { isTerminalRunState } from '@/shared/api';
import { SHOW_REVIEW_INDICATION } from '@/shared/config';
import { formatInstant, routes } from '@/shared/lib';
import { RunWorkerLine, runHoldsLease, runWorker, useWorkerLookup } from '@/entities/execution';
import { GroupWaitDetail } from '@/entities/executor-group';
import { NormReferencesSection } from '@/widgets/norm-references';
import {
  ErrorState,
  LoadingState,
  NotApplicableState,
  RunStateBadge,
  StageStatusBadge,
  runStageLabel,
  STATE_LABELS,
  COST_BASIS_LABELS,
  PROVIDER_MODE_LABELS,
  PROVIDER_MODE_UNKNOWN_LABEL,
} from '@/shared/ui';
import styles from './run-progress.module.css';
import { PdfPrecheckProgress } from './pdf-precheck-progress';
import { RunLiveLine } from './run-live-line';
import { RunNextTask } from './run-next-task';
import { ExtendedReview } from '@/widgets/extended-review';
import { startedFrom, type StartedFrom } from '../model/started-from';

import {
  StageTable,
  type StageRow,
  arV3GroupReviewAddress,
  badgeProviderMode,
  costBasisCaption,
  diagnosticObservationCount,
  elapsedMs,
  formatCostMicros,
  formatElapsed,
  hasKnownRunVocabulary,
  interruptedReason,
  isRunAnimating,
  looksLikeArV3GroupId,
  providerModeCaption,
  runAnalysis,
  runAnalysisKind,
  runCost,
  runExecutorLine,
  runExecutorValue,
  runHasPublishedResult,
  runOutcome,
  runPresetLine,
  runPresetValue,
  runProviderMode,
  runWaitingSentence,
  stageRows,
  terminalReasonNote,
  useArV3StartAllowed,
  useRunStatus,
} from '@/entities/audit-run';

export interface RunProgressProps {
  readonly projectUid: string;
  readonly runId: string;
  /** The page's own controls for this run («Отменить прогон»), beside the review call in the head. */
  readonly actions?: ReactNode;
}

/** The worker holding a running or validating run, read from the registry's first page. */
function RunHolder({ runId }: { readonly runId: string }) {
  const workers = useWorkerLookup(true);
  return <RunWorkerLine worker={runWorker(workers.data, workers.error !== null, runId)} />;
}

const UNKNOWN_RUN_TITLE = 'Прогон содержит неизвестное значение.';

/** The original-style rail displays only stages reported or scheduled for this Run. */
function PipelineRail({ rows, reused }: { readonly rows: readonly StageRow[]; readonly reused?: ReadonlySet<string> }) {
  return (
    <div className={styles.pipeline} role="list" aria-label="Этапы этого прогона" data-run-pipeline="">
      {rows.map((row, index) => (
        <div className={styles.pipelineItem} key={row.stageId} role="listitem">
          <div
            className={styles.pipelineStage}
            data-pipeline-stage={row.stageId}
            data-pipeline-status={row.status ?? 'not-reported'}
            {...(reused?.has(row.stageId) ? { 'data-pipeline-reused': '' } : {})}
          >
            <span className={styles.pipelineOrdinal}>{row.ordinal === null ? '—' : String(row.ordinal).padStart(2, '0')}</span>
            <span className={styles.pipelineName}>{runStageLabel(row.stageId)}</span>
            <span className={styles.pipelineStatus}>
              {row.status === null ? 'Не начинался' : <StageStatusBadge status={row.status} errorCode={row.errorCode} />}
            </span>
            {/* `R-151i`: a stage taken from the earlier run took no time here; the rail says where it came from instead. */}
            {reused?.has(row.stageId) ? <span className={styles.pipelineTook}>из прогона</span> : elapsedMs(row.startedAt, row.finishedAt) === null ? null : (
              <span className={styles.pipelineTook} data-pipeline-took={formatElapsed(elapsedMs(row.startedAt, row.finishedAt))}>
                {formatElapsed(elapsedMs(row.startedAt, row.finishedAt))}
              </span>
            )}
          </div>
          {index === rows.length - 1 ? null : <span className={styles.pipelineArrow} aria-hidden="true">→</span>}
        </div>
      ))}
    </div>
  );
}

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
/**
 * `R-151i` («Запущен с этапа N из прогона …»): the earlier run this one took its first stages from, linked. Nothing for a run
 * that was not started from a stage.
 */
function StartedFromFact({ status, from }: { readonly status: RunStatus; readonly from: StartedFrom }) {
  return (
    <>
      <dt>Запущен с этапа</dt>
      <dd data-run-started-from={from.sourceRunId} data-run-start-stage={from.stageId}>
        {from.ordinal}. {runStageLabel(from.stageId)} из прогона{' '}
        <Link href={routes.run(status.project_uid, from.sourceRunId)}><code>{from.sourceRunId}</code></Link>
      </dd>
    </>
  );
}

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
            <span data-run-state="published">{STATE_LABELS.published}</span>.
          </p>
          <p>
            Опубликованных находок:{' '}
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
      {cost.kind === 'absent' ? (
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
 * The line of figures under the head, as the original's spend bar («⚡ ↓вход ↑выход · Платно $ · N calls ·
 * длительность»). Each tile is shown only when its figure is one the screen may state: the finding count only
 * for a run that published, the cost only with the number of calls it sums. The sentences that qualify each
 * figure are below, in «Пояснения к цифрам»; nothing here is a zero the reading did not report.
 */
function Figures({ status }: { readonly status: RunStatus }) {
  const outcome = runOutcome(status);
  const diagnostics = diagnosticObservationCount(status);
  const cost = runCost(status);
  return (
    <dl className={styles.figures} aria-label="Итоги прогона">
      {outcome.kind === 'published' ? (
        <div className={styles.figure}>
          <dt>Находок</dt>
          <dd>{outcome.findingCount === null ? '—' : outcome.findingCount}</dd>
        </div>
      ) : null}
      <div className={styles.figure}>
        <dt>Диагностических наблюдений</dt>
        <dd>{diagnostics === null ? '—' : diagnostics}</dd>
      </div>
      <div className={styles.figure}>
        <dt>Длительность</dt>
        <dd>{formatElapsed(elapsedMs(status.created_at, status.terminal_at))}</dd>
      </div>
      {cost.kind === 'reported' ? (
        <>
          <div className={styles.figure}>
            <dt>Стоимость</dt>
            <dd>{formatCostMicros(cost.micros)}</dd>
          </div>
          <div className={styles.figure}>
            <dt>Вызовов провайдера</dt>
            <dd>{cost.callCount}</dd>
          </div>
        </>
      ) : null}
    </dl>
  );
}

export function RunProgress({ projectUid, runId, actions }: RunProgressProps) {
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
  const preset = runPresetLine(status);
  const waiting = executor === null ? null : runWaitingSentence(executor);

  const from = startedFrom(status);
  const v3Beta = runAnalysisKind(status) === 'ar_v3_beta';
  const reviewable = !v3Beta && runHasPublishedResult(status.state, status.analysis_profile_id);

  return (
    <div className={styles.progress} data-run-id={status.run_id}>
      {/*
        The head, as the original's pipeline card: the state and whether the reading is final on top, the stages
        in a rail, and on the right what to do next -- review the findings, or stop the run.
      */}
      <section className={styles.head} aria-label="Этапы и действия">
        <div className={styles.headTop}>
          <p className={styles.mode}>
            <RunStateBadge state={status.state} providerMode={badgeProviderMode(mode)} />
            <span data-provider-mode={mode}>
              режим провайдера: <strong data-provider-mode={mode}>{modeText}</strong>
            </span>
          </p>
          <p className={styles.activity} data-run-activity={animating && polling ? 'polling' : 'stopped'}>
            {animating && polling
              ? 'Идёт опрос следующего показания: интервал растёт с 2 с до 15 с и прекращается в терминальном состоянии.'
              : animating
                ? 'Опрос остановлен, но прогон ещё открыт: показание — последнее полученное, а не окончательное.'
                : 'Опрос остановлен, показание окончательное.'}
          </p>
        </div>
        {/* `UI-A-65`: the open run's live line -- the stage it is on and how long it has been going. */}
        {animating ? <RunLiveLine status={status} rows={stageRows(status)} /> : null}
        <div className={styles.headBody}>
          <PipelineRail rows={stageRows(status)} {...(from === null ? {} : { reused: from.reusedStageIds })} />
          {reviewable || actions !== undefined ? (
            <div className={styles.headActions}>
              {reviewable ? (
                <p className={styles.reviewCall}>
                  <Link className="am-button" href={routes.review(projectUid, status.run_id)}>
                    Разобрать находки
                  </Link>
                  <span>
                    режим провайдера этого прогона: <strong data-provider-mode={mode}>{modeText}</strong>
                  </span>
                </p>
              ) : null}
              {actions}
            </div>
          ) : null}
        </div>
      </section>

      {/* `R-151i`: a run started from a stage says so under its head, with the way back to the run it took the first stages from. */}
      {from === null ? null : (
        <p className={styles.caption} data-run-started-from-note={from.stageId}>
          Запущен с этапа {from.ordinal} «{runStageLabel(from.stageId)}» из прогона{' '}
          <Link href={routes.run(status.project_uid, from.sourceRunId)}><code>{from.sourceRunId}</code></Link>:
          результаты предыдущих этапов взяты из него, этот этап и следующие выполнены заново.
        </p>
      )}

      <Figures status={status} />

      <Outcome status={status} />

      {/* `UI-B-70`: a run that waits in the queue says what goes first and why it waits, as the original's «Следующая задача». */}
      {status.state === 'queued' ? <RunNextTask status={status} /> : null}

      <div className={styles.columns}>
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
            {from === null ? null : <StartedFromFact status={status} from={from} />}
            {executor === null ? null : <><dt>Исполнитель</dt><dd data-run-executor>{runExecutorValue(executor)}</dd></>}
            {preset === null ? null : <><dt>Пресет</dt><dd data-run-preset>{runPresetValue(preset)}</dd></>}
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

          {waiting === null ? null : <p data-run-executor-waiting>{waiting}</p>}
          {/* `EXEC2-FOLLOWUP-01`: a group Run that waits for a runner says what is actually wrong, and that the wait ends. */}
          {executor === null || executor.phase !== 'planned' ? null : (
            <GroupWaitDetail
              groupId={status.planned?.executor_group_id}
              revisionId={status.planned?.executor_group_revision_id}
              waitReason={executor.queueReason ?? null}
            />
          )}
          {runHoldsLease(status.state) ? <RunHolder runId={status.run_id} /> : null}
          <p className={styles.caption}>
            Прогон никогда не меняет прочитанную версию; остальные её прогоны перечислены на её странице.
          </p>
        </section>

        <section className={styles.panel} aria-label="Подробности этапов">
          <h2>Подробности этапов</h2>
          <StageTable rows={stageRows(status)} />
        </section>
      </div>

      <ExtendedReview key={runId} runId={runId} active={animating} projectUid={projectUid} />

      {interrupted !== null && status.state !== 'failed' ? (
        <p data-interrupted-reason={interrupted}>
          У прогона указана причина прерывания: {interrupted}.
        </p>
      ) : null}

      <PdfPrecheckProgress status={status} />

      {reviewable ? null : (
        <>
          <h2>Разбор</h2>
          {v3Beta ? (
            <NotApplicableState
              title={SHOW_REVIEW_INDICATION ? 'Предварительный разбор АР v3' : 'Разбор АР v3'}
              detail={
                <p>
                  Для просмотра шести прогонов откройте «Настройки анализа» и укажите идентификатор группы из ответа запуска. Здесь нет канонических находок для разбора или принятия решения.
                </p>
              }
            />
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
        </>
      )}

      {/* `NORM-REFS-RUN-01`: the norms the stored run's text cites. Only once the run has stopped;
          while it is in flight its text layer may not exist yet, and «нет текстового слоя»
          would be a claim about a run that has not got that far. */}
      {isTerminalRunState(status.state) ? <NormReferencesSection runId={status.run_id} /> : null}

      {/*
        The sentences that qualify the figures stay on the screen and are read when asked for, as the CSV columns are
        on the export bar (`R-18`). They open by themselves when the cost cannot be read, because that sentence is
        the only place the screen says why no figure is shown.
      */}
      <section className={styles.notes} aria-label="Пояснения к цифрам">
        <details open={runCost(status).kind === 'unreadable'} data-run-notes="">
          <summary className={styles.notesSummary}>Пояснения к цифрам</summary>
          <Recorded status={status} />
        </details>
      </section>

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
