'use client';

/**
 * The three AI blocks of «Сравнение листов» between «Сводка переходов» and the matrix
 * (`frontend/static/js/version-comparison.js:159-333`): «ИИ-описание изменений», «Полные спецификации (СО)» and
 * «Сводка MD и отчёт для заказчика».
 *
 * Each block is a view driven by props (so every state is rendered by the static harness) and a container that reads its own
 * data from `entities/version-series`. A block whose operation answers `503 dependency_unavailable` says «Модуль ещё
 * недоступен» in its place and nothing else; a block that has nothing to show yet says so in a sentence. No block starts a model
 * call by itself: «Запустить», «Повторить листы с ошибкой» and «Сравнить спецификации» open the estimate dialog.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import type {
  ComparisonAiSheetChanges,
  ComparisonReport,
  ComparisonReviewSheet,
  ComparisonSeries,
  ComparisonSpecChange,
  ComparisonSpecification,
  ComparisonTransition,
  ComparisonTransitionId,
  ProjectUid,
} from '@/shared/api';
import { LoadingState } from '@/shared/ui';
import type { ComparisonFailure } from '@/entities/version-series';
import {
  AI_PAUSE_ADVICE,
  AI_PAUSE_REASON_LABELS,
  AI_SHEET_STATE_LABELS,
  AI_TEXT_NOTE,
  AiText,
  RecordedMark,
  RETRY_FAILED_LABEL,
  REPORT_KIND_LABELS,
  REPORT_STAGE_LABELS,
  REPORT_STATE_LABELS,
  REVIEW_SHEET_KIND_LABELS,
  REVIEW_SHEET_KIND_TITLES,
  SPEC_CHANGE_KIND_LABELS,
  SPEC_METHOD_LABELS,
  SPEC_METHOD_TITLES,
  SPEC_PHASE_LABELS,
  SPEC_STATE_LABELS,
  aiJobStateLabel,
  canContinueReport,
  comparisonFailure,
  coverageLine,
  coveragePercent,
  hasArtifact,
  isRecordedRoute,
  pdfName,
  positionsLine,
  progressPercent,
  reportProgressLine,
  sheetTotals,
  specFieldLabel,
  specMethodsLine,
  specReasonWords,
  specSheetsLine,
  unitMark,
  useAiJobAct,
  useAiSheetChanges,
  useDownload,
  useReportCommand,
  useReports,
  useReviewSheets,
  useSpecificationChanges,
  useSpecifications,
} from '@/entities/version-series';

import { AiStartDialog } from './ai-dialogs';
import { CommandRefusal, FailureState } from './module-state';
import aiStyles from './ai-steps.module.css';
import styles from './version-series.module.css';

function n(value: number): string {
  return value.toLocaleString('ru-RU');
}

/** «1 мин 5 с» (`fmtDuration`, `version-comparison.js:973`). */
export function duration(seconds: number | undefined): string {
  if (seconds === undefined) return '—';
  return seconds >= 60 ? `${Math.floor(seconds / 60)} мин ${Math.round(seconds % 60)} с` : `${Math.round(seconds)} с`;
}

function transitionName(transition: Pick<ComparisonTransition, 'source_version_uid' | 'target_version_uid'>, names: ReadonlyMap<string, string>): string {
  return `${names.get(transition.source_version_uid) ?? '№?'} → ${names.get(transition.target_version_uid) ?? '№?'}`;
}

const NAMELESS = '№?';

// ------------------------------------------------------------------------------ «ИИ-описание изменений»

export interface AiChangesBlockViewProps {
  readonly changes: ComparisonAiSheetChanges;
  readonly series: ComparisonSeries;
  readonly names: ReadonlyMap<string, string>;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly failure: ComparisonFailure | null;
  /** The transitions whose fold is open, and the sheets the open folds hold. */
  readonly folds: ReadonlySet<string>;
  readonly review: ReadonlyMap<string, readonly ComparisonReviewSheet[]>;
  readonly onFold: (transitionId: string) => void;
  readonly onAct: (act: 'cancel' | 'finish' | 'dequeue' | 'retry') => void;
  readonly onOpenTransition: (transition: ComparisonTransition) => void;
  readonly onOpenReviewSheet: (transition: ComparisonTransition, sheet: ComparisonReviewSheet) => void;
  readonly dialog: ReactNode;
}

export function AiChangesBlockView({
  changes, series, names, mayAct, busy, failure, folds, review, onFold, onAct, onOpenTransition, onOpenReviewSheet, dialog,
}: AiChangesBlockViewProps) {
  const job = changes.job;
  const totals = sheetTotals(changes.transitions);
  const partial = job?.state === 'completed' && (totals.errors > 0 || totals.review > 0);
  const stateText =
    job === undefined
      ? 'описание ещё не запускалось'
      : job.state === 'queued'
        ? `в очереди${job.queue_position === undefined ? '' : ` №${job.queue_position}`}`
        : partial
          ? `готово${totals.errors > 0 ? `, ошибок ${n(totals.errors)}` : ''}${totals.review > 0 ? `, проверить листов: ${n(totals.review)}` : ''}`
          : aiJobStateLabel(job);
  const canCancel = job !== undefined && (job.state === 'running' || job.state === 'paused');
  const canFinish = job !== undefined && (job.state === 'cancelled' || job.state === 'failed' || job.state === 'paused') && job.counts.done < job.counts.total;
  const canDequeue = job !== undefined && job.state === 'queued';
  const canRetry = job !== undefined && totals.errors > 0 && (job.state === 'completed' || job.state === 'failed' || job.state === 'cancelled');
  return (
    <section className={aiStyles.aiBlock} aria-label="ИИ-описание изменений" data-ai-changes={job?.state ?? 'none'}>
      <div className={aiStyles.aiHead}>
        <h3 className={aiStyles.aiTitle}>ИИ-описание изменений</h3>
        {job === undefined ? (
          <span className="am-note">{stateText}</span>
        ) : (
          <>
            <span className="am-badge am-badge--active" data-ai-job-state={job.state}>{stateText}</span>
            {isRecordedRoute(job) ? <RecordedMark /> : null}
            <span className="am-note">
              листов готово: {n(totals.done)} из {n(totals.sheets)} · время {duration(totals.seconds)} · обращений {n(totals.calls)} · токены: вход {n(totals.inputTokens)}, выход {n(totals.outputTokens)}
            </span>
          </>
        )}
        {mayAct && canCancel ? (
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} title="Остановить описание. Готовые описания листов сохранятся." onClick={() => onAct('cancel')}>Отменить</button>
        ) : null}
        {mayAct && canFinish ? (
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} title="Описать оставшиеся листы; готовые не описываются заново." onClick={() => onAct('finish')}>Досчитать</button>
        ) : null}
        {mayAct && canDequeue ? (
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} title="Убрать комплект из очереди ИИ-описаний; ничего не будет описано." onClick={() => onAct('dequeue')}>Убрать из очереди</button>
        ) : null}
        {mayAct && canRetry ? (
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} title="Описать заново только листы с ошибкой (например, после отказа провайдера); готовые листы не повторяются." data-ai-retry="" onClick={() => onAct('retry')}>{RETRY_FAILED_LABEL}</button>
        ) : null}
      </div>
      {job?.state === 'paused' && job.pause_reason !== undefined ? (
        <p className={aiStyles.warning} role="status" data-ai-pause-reason={job.pause_reason}>
          Пауза: {AI_PAUSE_REASON_LABELS[job.pause_reason]}. {AI_PAUSE_ADVICE[job.pause_reason]}
        </p>
      ) : null}
      <CommandRefusal failure={failure} />
      {dialog}
      {job !== undefined && job.spend.unknown_calls > 0 ? (
        <p className={aiStyles.warning} data-unknown-calls="">
          Обращений с неизвестным исходом: {job.spend.unknown_calls}. Они не отправляются повторно сами; листы с таким исходом нужно повторить вручную.
        </p>
      ) : null}
      <div className={styles.scroller}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Переход</th><th scope="col">Ход описания</th><th scope="col">Листов</th><th scope="col">Изм.</th><th scope="col">Вопр.</th>
              <th scope="col">Ошибок</th>
              <th scope="col" title="Листы, где ИИ изменений не нашёл, но сравнение оставило пометки (например, пара листов сопоставлена неуверенно). Их нужно посмотреть самому.">Проверить</th>
              <th scope="col">Обращ.</th><th scope="col">Вход</th><th scope="col">Выход</th><th scope="col">Время</th><th scope="col"><span className={styles.visuallyHidden}>Открыть</span></th>
            </tr>
          </thead>
          <tbody>
            {changes.transitions.map((row) => {
              const transition = (series.transitions ?? []).find((item) => item.transition_id === row.transition_id);
              const open = folds.has(row.transition_id);
              const sheets = review.get(row.transition_id) ?? [];
              return (
                <RowWithFold key={row.transition_id} columns={12} open={open} fold={
                  sheets.length === 0 ? (
                    <span className={styles.muted}>Листов «Проверить», добавленных и удалённых нет.</span>
                  ) : (
                    sheets.map((sheet) => (
                      <div key={sheet.sheet_pair_id} className={aiStyles.single} data-review-kind={sheet.kind} data-ai-sheet-state={sheet.state}>
                        <span className="am-badge am-badge--degraded" title={REVIEW_SHEET_KIND_TITLES[sheet.kind]}>{REVIEW_SHEET_KIND_LABELS[sheet.kind]}</span>
                        <strong>{sheet.page_b?.title ?? sheet.page_a?.title ?? 'Лист'}</strong>
                        <span className={styles.muted}>
                          {sheet.page_a === undefined ? '' : `было стр. ${sheet.page_a.page.page_number}`}
                          {sheet.page_a !== undefined && sheet.page_b !== undefined ? ' → ' : ''}
                          {sheet.page_b === undefined ? '' : `стало стр. ${sheet.page_b.page.page_number}`} · {AI_SHEET_STATE_LABELS[sheet.state]}
                        </span>
                        {transition === undefined ? null : (
                          <button type="button" className="am-button am-button--small am-button--quiet" title="Открыть этот лист: наложение, было, стало; справа — описание ИИ и что проверить." onClick={() => onOpenReviewSheet(transition, sheet)}>Открыть</button>
                        )}
                      </div>
                    ))
                  )
                }>
                  <td className={styles.transitionName}>
                    <button type="button" className={aiStyles.fold} aria-expanded={open} title={open ? 'Свернуть листы перехода' : 'Показать листы перехода: проверить, добавлен или удалён'} onClick={() => onFold(row.transition_id)}>
                      {open ? '▾' : '▸'}
                    </button>{' '}
                    {transition === undefined ? NAMELESS : transitionName(transition, names)}
                  </td>
                  <td className={styles.progressCell}>
                    <progress className={styles.progress} value={row.done} max={Math.max(1, row.sheets)} aria-label="Ход описания перехода" />
                    <span className={styles.muted}> {n(row.done)} из {n(row.sheets)}{progressPercent(row.done, row.sheets) === 100 ? ' · готово' : ''}</span>
                  </td>
                  <td className={aiStyles.numeric}>{n(row.sheets)}</td>
                  <td className={aiStyles.numeric}>{n(row.changed)}</td>
                  <td className={aiStyles.numeric}>{n(row.questions)}</td>
                  <td className={row.errors > 0 ? `${aiStyles.numeric} ${aiStyles.errorCell}` : aiStyles.numeric}>{row.errors > 0 ? n(row.errors) : ''}</td>
                  <td className={aiStyles.numeric}>{row.to_review > 0 ? n(row.to_review) : ''}</td>
                  <td className={aiStyles.numeric}>{n(row.calls)}</td>
                  <td className={aiStyles.numeric}>{n(row.input_tokens)}</td>
                  <td className={aiStyles.numeric}>{n(row.output_tokens)}</td>
                  <td className={aiStyles.numeric}>{duration(row.seconds)}</td>
                  <td>
                    {transition === undefined ? null : (
                      <button type="button" className="am-button am-button--small am-button--quiet" title="Показать в матрице этот переход: версии станут парой «было» и «стало»." onClick={() => onOpenTransition(transition)}>Открыть</button>
                    )}
                  </td>
                </RowWithFold>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="am-note">Описание каждого листа — в просмотрщике пары, окно «Изменения в листе». {AI_TEXT_NOTE}</p>
    </section>
  );
}

function RowWithFold({ children, open, fold, columns }: { readonly children: ReactNode; readonly open: boolean; readonly fold: ReactNode; readonly columns: number }) {
  return (
    <>
      <tr>{children}</tr>
      {open ? (
        <tr className={aiStyles.foldRow}>
          <td colSpan={columns}>{fold}</td>
        </tr>
      ) : null}
    </>
  );
}

export interface AiChangesBlockProps {
  readonly series: ComparisonSeries;
  readonly projectUid: ProjectUid;
  readonly names: ReadonlyMap<string, string>;
  readonly mayAct: boolean;
  readonly onOpenTransition: (transition: ComparisonTransition) => void;
  readonly onOpenReviewSheet: (transition: ComparisonTransition, sheet: ComparisonReviewSheet) => void;
}

export function AiChangesBlock({ series, names, mayAct, onOpenTransition, onOpenReviewSheet }: AiChangesBlockProps) {
  const changes = useAiSheetChanges(series.series_id);
  const act = useAiJobAct();
  const [folds, setFolds] = useState<ReadonlySet<string>>(new Set());
  const [retry, setRetry] = useState(false);
  // The «Проверить» lists of the open folds are read together: one hook per fold would break the rules of hooks.
  const first = [...folds][0] ?? null;
  const reviewed = useReviewSheets((first ?? null) as ComparisonTransitionId | null, first !== null);
  if (changes.isPending) return <LoadingState what="ИИ-описание изменений" />;
  if (changes.isError) return <FailureState error={changes.error} title="ИИ-описание изменений не открылось" />;
  const data = changes.data;
  const review = new Map<string, readonly ComparisonReviewSheet[]>(first === null ? [] : [[first, reviewed.data ?? []]]);
  const job = data.job;
  return (
    <AiChangesBlockView
      changes={data}
      series={series}
      names={names}
      mayAct={mayAct}
      busy={act.isPending}
      failure={act.error === null ? null : comparisonFailure(act.error)}
      folds={folds}
      review={review}
      onFold={(id) => setFolds((held) => (held.has(id) ? new Set() : new Set([id])))}
      onAct={(what) => {
        act.reset();
        if (job === undefined) return;
        if (what === 'retry') return setRetry(true);
        act.mutate({ method: 'sheet_changes', act: what, jobId: job.job_id });
      }}
      onOpenTransition={onOpenTransition}
      onOpenReviewSheet={onOpenReviewSheet}
      dialog={
        retry && job !== undefined ? (
          <AiStartDialog
            title="ИИ-описание изменений · листы с ошибкой"
            scope={{ kind: 'sheet_changes', seriesId: series.series_id, onlyFailed: true }}
            consentKind="sheet_changes"
            confirmLabel={RETRY_FAILED_LABEL}
            retryJobId={job.job_id}
            intro="Будут описаны заново только листы, которые ИИ не смог описать. Готовые листы не повторяются."
            onDone={() => setRetry(false)}
            onCancel={() => setRetry(false)}
          />
        ) : null
      }
    />
  );
}

// ------------------------------------------------------------------------------ «Полные спецификации (СО)»

export interface SpecificationsBlockViewProps {
  readonly specs: readonly ComparisonSpecification[];
  readonly transitions: readonly ComparisonTransition[];
  readonly names: ReadonlyMap<string, string>;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly failure: ComparisonFailure | null;
  readonly openChanges: string | null;
  readonly changes: ReactNode;
  readonly onOpenChanges: (transitionId: string) => void;
  readonly onStart: (spec: ComparisonSpecification) => void;
  readonly onCancel: (spec: ComparisonSpecification) => void;
  readonly onOpenTransition: (transition: ComparisonTransition) => void;
  readonly dialog: ReactNode;
}

/** The header state of the block: running, then paused, then failed, then the rest (`SPEC_STATE`, `:872-873`). */
function blockState(specs: readonly ComparisonSpecification[]): ComparisonSpecification['state'] {
  const order: readonly ComparisonSpecification['state'][] = ['running', 'paused', 'failed', 'incomplete', 'cancelled', 'completed', 'not_started', 'not_applicable'];
  return order.find((state) => specs.some((spec) => spec.state === state)) ?? 'not_applicable';
}

export function SpecificationsBlockView({
  specs, transitions, names, mayAct, busy, failure, openChanges, changes, onOpenChanges, onStart, onCancel, onOpenTransition, dialog,
}: SpecificationsBlockViewProps) {
  const state = blockState(specs);
  const running = specs.find((spec) => spec.state === 'running');
  return (
    <section className={aiStyles.aiBlock} aria-label="Полные спецификации (СО)" data-specifications={state}>
      <div className={aiStyles.aiHead}>
        <h3 className={aiStyles.aiTitle}>Полные спецификации (СО)</h3>
        <span className="am-badge am-badge--active" data-spec-state={state} {...(running?.phase === undefined ? {} : { 'data-spec-phase': running.phase })}>
          {SPEC_STATE_LABELS[state]}
          {running?.phase === undefined ? '' : ` · ${SPEC_PHASE_LABELS[running.phase]}`}
        </span>
        <span className="am-note">{specMethodsLine(specs)}</span>
      </div>
      <CommandRefusal failure={failure} />
      {dialog}
      <div className={styles.scroller}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Переход</th><th scope="col">Способ</th>
              <th scope="col" title="Листов спецификации в прежней и в новой версии">Листов СО</th>
              <th scope="col" title="Блоки текста спецификации, которые разметил ИИ и подтвердила программа">Покрыто</th>
              <th scope="col" title="Позиции: изменено / добавлено / удалено; «?» — не удалось сопоставить">Позиции</th>
              <th scope="col">Причина / замечание</th><th scope="col"><span className={styles.visuallyHidden}>Действия</span></th>
            </tr>
          </thead>
          <tbody>
            {specs.map((spec) => {
              const transition = transitions.find((item) => item.transition_id === spec.transition_id);
              const canStart = mayAct && spec.state !== 'not_applicable' && spec.state !== 'running' && spec.state !== 'paused' && spec.sheets_a > 0 && spec.sheets_b > 0;
              return (
                <RowWithFold key={spec.transition_id} columns={7} open={openChanges === spec.transition_id} fold={changes}>
                  <td className={styles.transitionName}>{transition === undefined ? NAMELESS : transitionName(transition, names)}</td>
                  <td title={SPEC_METHOD_TITLES[spec.method]} data-spec-method={spec.method}>{SPEC_METHOD_LABELS[spec.method]}</td>
                  <td className={aiStyles.numeric}>{specSheetsLine(spec)}</td>
                  <td className={styles.progressCell}>
                    {spec.method === 'whole' ? (
                      <>
                        <progress className={styles.progress} value={coveragePercent(spec)} max={100} aria-label="Покрытие спецификации" />
                        <span className={styles.muted}> {coverageLine(spec)}</span>
                      </>
                    ) : (
                      <span className={styles.muted} title="Листы СО этого перехода описывает «ИИ-описание изменений» как обычные листы.">в «ИИ-описании»</span>
                    )}
                  </td>
                  <td className={aiStyles.numeric}>{positionsLine(spec.totals)}</td>
                  <td className={spec.state === 'failed' || spec.state === 'incomplete' ? aiStyles.errorCell : undefined}>
                    <span data-spec-state={spec.state}>{SPEC_STATE_LABELS[spec.state]}</span>
                    {spec.reason === undefined ? null : <> · {specReasonWords(spec.reason)}</>}
                  </td>
                  <td>
                    <span className={styles.actions}>
                      {canStart ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} title="ИИ прочитает спецификацию каждой версии целиком, затем программа сравнит две независимо от порядка строк." onClick={() => onStart(spec)}>
                          Сравнить спецификации
                        </button>
                      ) : null}
                      {mayAct && spec.state === 'running' && spec.job_id !== undefined ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} onClick={() => onCancel(spec)}>Отменить</button>
                      ) : null}
                      {spec.totals !== undefined ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" aria-expanded={openChanges === spec.transition_id} onClick={() => onOpenChanges(spec.transition_id)}>Позиции</button>
                      ) : null}
                      {transition === undefined ? null : (
                        <button type="button" className="am-button am-button--small am-button--quiet" title="Показать в матрице этот переход: версии станут парой «было» и «стало»." onClick={() => onOpenTransition(transition)}>Открыть</button>
                      )}
                    </span>
                  </td>
                </RowWithFold>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="am-note">{AI_TEXT_NOTE}</p>
    </section>
  );
}

export function SpecificationChanges({ transitionId }: { readonly transitionId: ComparisonTransitionId }) {
  const changes = useSpecificationChanges(transitionId);
  if (changes.isPending) return <LoadingState what="позиции спецификации" />;
  if (changes.isError) return <FailureState error={changes.error} title="Позиции спецификации не открылись" />;
  return <SpecificationChangesView items={changes.data.items} />;
}

export function SpecificationChangesView({ items }: { readonly items: readonly ComparisonSpecChange[] }) {
  if (items.length === 0) return <span className={styles.muted}>Изменений позиций нет.</span>;
  return (
    <ul className={aiStyles.stripList}>
      {items.map((change) => (
        <li key={change.change_id} className={aiStyles.stripEntry} data-spec-change-kind={change.kind}>
          <strong>{SPEC_CHANGE_KIND_LABELS[change.kind]}</strong>{' '}
          {(change.new ?? change.old)?.name ?? ''}
          {change.fields.length === 0 ? null : (
            <span className={aiStyles.hint}>
              {change.fields.map((field) => `${specFieldLabel(field.field)}: ${field.was ?? '—'} → ${field.now ?? '—'}`).join('; ')}
            </span>
          )}
          {change.text === undefined ? null : <AiText as="span">{change.text}</AiText>}
        </li>
      ))}
    </ul>
  );
}

export interface SpecificationsBlockProps {
  readonly series: ComparisonSeries;
  readonly names: ReadonlyMap<string, string>;
  readonly mayAct: boolean;
  readonly onOpenTransition: (transition: ComparisonTransition) => void;
}

export function SpecificationsBlock({ series, names, mayAct, onOpenTransition }: SpecificationsBlockProps) {
  const specs = useSpecifications(series.series_id);
  const act = useAiJobAct();
  const [openChanges, setOpenChanges] = useState<string | null>(null);
  const [starting, setStarting] = useState<ComparisonSpecification | null>(null);
  if (specs.isPending) return <LoadingState what="полные спецификации" />;
  if (specs.isError) return <FailureState error={specs.error} title="Полные спецификации не открылись" />;
  const items = specs.data.filter((spec) => spec.state !== 'not_applicable');
  if (items.length === 0) return null;
  return (
    <SpecificationsBlockView
      specs={items}
      transitions={series.transitions ?? []}
      names={names}
      mayAct={mayAct}
      busy={act.isPending}
      failure={act.error === null ? null : comparisonFailure(act.error)}
      openChanges={openChanges}
      changes={openChanges === null ? null : <SpecificationChanges transitionId={openChanges as ComparisonTransitionId} />}
      onOpenChanges={(id) => setOpenChanges((held) => (held === id ? null : id))}
      onStart={setStarting}
      onCancel={(spec) => {
        if (spec.job_id !== undefined) act.mutate({ method: 'spec', act: 'cancel', jobId: spec.job_id });
      }}
      onOpenTransition={onOpenTransition}
      dialog={
        starting === null ? null : (
          <AiStartDialog
            title="Полные спецификации · сравнение перехода"
            scope={{ kind: 'spec', transitionId: starting.transition_id }}
            consentKind="spec"
            confirmLabel="Запустить сравнение"
            intro="ИИ разметит спецификацию каждой версии, программа сверит цитаты и значения с текстом листа и только потом сравнит две. Если сторону не удалось прочитать целиком, добавления и удаления не публикуются."
            onDone={() => setStarting(null)}
            onCancel={() => setStarting(null)}
          />
        )
      }
    />
  );
}

// ------------------------------------------------------------------------------ «Сводка MD и отчёт для заказчика»

export interface SummaryReportBlockViewProps {
  readonly report: ComparisonReport | undefined;
  readonly summaryReady: boolean;
  readonly transitions: readonly ComparisonTransition[];
  readonly names: ReadonlyMap<string, string>;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly failure: ComparisonFailure | null;
  readonly onPdf: (report: ComparisonReport) => void;
  readonly onMd: () => void;
  readonly onContinue: (report: ComparisonReport) => void;
}

export function SummaryReportBlockView({ report, summaryReady, transitions, names, mayAct, busy, failure, onPdf, onMd, onContinue }: SummaryReportBlockViewProps) {
  return (
    <section className={aiStyles.aiBlock} aria-label="Сводка MD и отчёт для заказчика" data-summary-report={report?.state ?? 'none'}>
      <div className={aiStyles.aiHead}>
        <h3 className={aiStyles.aiTitle}>Сводка MD и отчёт для заказчика</h3>
        {report === undefined ? (
          <span className="am-note">отчёт по этой сводке ещё не формировался</span>
        ) : (
          <>
            <span className="am-badge am-badge--active" data-report-state={report.state}>{REPORT_STATE_LABELS[report.state]}</span>
            {isRecordedRoute(report.job) ? <RecordedMark /> : null}
            <span className="am-note">
              {report.stage === undefined ? '' : <>шаг: <span data-report-stage={report.stage}>{REPORT_STAGE_LABELS[report.stage]}</span> · </>}
              {reportProgressLine(report)}
              {report.job === undefined ? '' : ` · обращений ${n(report.job.spend.calls)} · токены: вход ${n(report.job.spend.input_tokens)}, выход ${n(report.job.spend.output_tokens)}`}
            </span>
            {hasArtifact(report, 'report_pdf') ? (
              <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} data-report-download="pdf" onClick={() => onPdf(report)}>Скачать PDF</button>
            ) : null}
            {mayAct && canContinueReport(report) ? (
              <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} title="Продолжить отчёт с того же места: готовые переходы не отправляются заново." onClick={() => onContinue(report)}>Продолжить</button>
            ) : null}
          </>
        )}
        {summaryReady ? (
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} data-report-download="md" onClick={onMd}>Скачать MD</button>
        ) : null}
      </div>
      <CommandRefusal failure={failure} />
      {report === undefined ? null : (
        <>
          {report.failure_reason === undefined || report.state === 'running' ? null : (
            <p className={aiStyles.warning} role="status">Отчёт остановился: {specReasonWords(report.failure_reason)}.</p>
          )}
          <div className={styles.scroller}>
            <table className={styles.table}>
              <thead>
                {report.kind === 'client' ? (
                  <tr>
                    <th scope="col">Переход</th>
                    <th scope="col" title="Отбор для заказчика: ✓ готово, ⟳ идёт, ✗ не подготовлен после повторов, · ждёт, — изменений нет">Отбор</th>
                    <th scope="col" title="Пунктов в отчёте">Пунктов</th><th scope="col">Вопросов</th>
                  </tr>
                ) : (
                  <tr>
                    <th scope="col">Переход</th><th scope="col">Анализ</th><th scope="col">Проверка</th>
                    <th scope="col" title="Найдено аналитиком / подтверждено проверкой / противоречит сводке / не подтверждено">Факты</th>
                    <th scope="col">Предупреждения</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {report.parts.map((part) => {
                  const transition = transitions.find((item) => item.transition_id === part.transition_id);
                  const mark = (value: typeof part.selection) => {
                    const unit = unitMark(value);
                    return (
                      <span className={value === 'failed' ? `${aiStyles.unit} ${aiStyles.unitFailed}` : aiStyles.unit} title={unit.word} {...(value === undefined ? {} : { 'data-unit-mark': value })}>
                        {unit.mark}
                      </span>
                    );
                  };
                  return (
                    <tr key={part.transition_id}>
                      <td className={styles.transitionName}>{transition === undefined ? NAMELESS : transitionName(transition, names)}</td>
                      {report.kind === 'client' ? (
                        <>
                          <td>{mark(part.selection)}</td>
                          <td className={aiStyles.numeric}>{part.points ?? ''}</td>
                          <td className={aiStyles.numeric}>{part.questions ?? ''}</td>
                        </>
                      ) : (
                        <>
                          <td>{mark(part.analysis)}</td>
                          <td>{mark(part.verification)}</td>
                          <td className={aiStyles.numeric}>
                            {part.facts === undefined ? '' : `${part.facts.found} / ${part.facts.confirmed} / ${part.facts.contradicted} / ${part.facts.unconfirmed}`}
                          </td>
                          <td className={aiStyles.numeric}>{part.warnings === undefined || part.warnings === 0 ? '' : `${part.warnings} ⓘ`}</td>
                        </>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="am-note">
            <span data-report-kind={report.kind}>{REPORT_KIND_LABELS[report.kind]}</span>. Каждая страница PDF несёт строку «не подтверждено инженером».
          </p>
        </>
      )}
    </section>
  );
}

export interface SummaryReportBlockProps {
  readonly series: ComparisonSeries;
  readonly names: ReadonlyMap<string, string>;
  readonly mayAct: boolean;
  readonly summaryReady: boolean;
}

export function SummaryReportBlock({ series, names, mayAct, summaryReady }: SummaryReportBlockProps) {
  const reports = useReports(series.series_id);
  const command = useReportCommand();
  const download = useDownload();
  if (reports.isPending) return <LoadingState what="сводку и отчёт" />;
  if (reports.isError) return <FailureState error={reports.error} title="Сводка и отчёт не открылись" />;
  const report = reports.data.find((item) => item.state !== 'draft');
  if (report === undefined && !summaryReady) return null;
  const error = command.error ?? download.error ?? null;
  return (
    <SummaryReportBlockView
      report={report}
      summaryReady={summaryReady}
      transitions={series.transitions ?? []}
      names={names}
      mayAct={mayAct}
      busy={command.isPending || download.isPending}
      failure={error === null ? null : comparisonFailure(error)}
      onPdf={(item) => download.mutate({ kind: 'report-pdf', reportId: item.report_id, fileName: pdfName(item) })}
      onMd={() => download.mutate({ kind: 'summary-md', seriesId: series.series_id, fileName: 'svodka-izmeneniy.md' })}
      onContinue={(item) => command.mutate({ act: 'continue', reportId: item.report_id })}
    />
  );
}

