'use client';

/**
 * The window «Сформировать PDF-отчёт…» (plan §1.1; `frontend/static/js/version-comparison-md-report.js`): the source — «сводка
 * проекта» or «загрузить MD-файл» —, the kind (the default «Отчёт для заказчика · Изменения проектных решений», or the analytic
 * one), the reuse of finished parts, and the history of the reports of the series with their per-transition progress, their
 * downloads and their controls: «Отменить», «Продолжить», «Пересобрать PDF» (no model call, nothing is spent), «Удалить»,
 * «Исходный MD», «Подготовить отчёт для заказчика» from a finished analytic report.
 *
 * **A report is made in two steps** (seal §3 decision 3): «Подготовить оценку» makes a draft — it calls no model and spends
 * nothing — and the estimate it carries is shown with the consent line (`EstimatePanel`); only «Сформировать» after the consent
 * starts the model work, and it carries the digest of the estimate that was shown. Every text the model wrote carries «не
 * подтверждено инженером»; the PDF carries it on every page.
 */

import { useRef, useState } from 'react';
import type { ReactNode } from 'react';

import type { ComparisonReport, ComparisonReportId, ComparisonReportKind, ComparisonReportSource, ComparisonSeries, ComparisonTransition } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { LoadingState } from '@/shared/ui';
import type { ComparisonFailure } from '@/entities/version-series';
import {
  AiLabel,
  CONFIRM_LABELS,
  RecordedMark,
  isRecordedRoute,
  EstimatePanel,
  REPORT_KIND_LABELS,
  REPORT_KIND_TITLES,
  REPORT_SOURCE_LABELS,
  REPORT_STAGE_LABELS,
  REPORT_STATE_LABELS,
  RESTART_CONFIRM_LABELS,
  canCancelReport,
  canContinueReport,
  canDeleteReport,
  canPrepareClientReport,
  canRebuildReport,
  canStartReport,
  comparisonFailure,
  hasArtifact,
  isLiveReport,
  pauseNeedsConsent,
  pdfName,
  reportProgressLine,
  sourceMdName,
  unitMark,
  usageLine,
  useConsentFlow,
  useDownload,
  useReportCommand,
  useReports,
} from '@/entities/version-series';
import { FailureBlock } from './failure-block';

import styles from './comparison-report.module.css';

export const WINDOW_TITLE = 'Отчёт для заказчика по «Сводке изменений (MD)»';
export const WINDOW_SUBTITLE =
  '«Изменения проектных решений»: по каждой выдаче масштаб и главные изменения для закупки, монтажа и эксплуатации. Отчёт строится по фактам сводки; исходные PDF не открываются.';
export const NO_SUMMARY_HINT = 'Сводки проекта ещё нет — сначала «ИИ-описание изменений».';
export const NO_REPORTS = 'Отчётов ещё нет.';
export const MAX_SOURCE_NOTE = 'Файл — UTF-8, не больше 20 МиБ, с переходами под заголовками вида «## 1. первая версия → вторая версия».';

function transitionName(transition: ComparisonTransition | undefined, names: ReadonlyMap<string, string>): string {
  return transition === undefined ? '№?' : `${names.get(transition.source_version_uid) ?? '№?'} → ${names.get(transition.target_version_uid) ?? '№?'}`;
}

export type ReportAct = 'cancel' | 'continue' | 'rebuild' | 'delete' | 'prepare' | 'start' | 'pdf' | 'source';

export interface ReportWindowViewProps {
  readonly reports: readonly ComparisonReport[];
  readonly transitions: readonly ComparisonTransition[];
  readonly names: ReadonlyMap<string, string>;
  readonly summaryReady: boolean;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly failure: ComparisonFailure | null;
  readonly source: ComparisonReportSource;
  readonly onSource: (source: ComparisonReportSource) => void;
  readonly kind: ComparisonReportKind;
  readonly onKind: (kind: ComparisonReportKind) => void;
  readonly reuse: boolean;
  readonly onReuse: (on: boolean) => void;
  readonly fileName: string | null;
  readonly onFile: (file: File | null) => void;
  readonly onPrepareEstimate: () => void;
  readonly onAct: (report: ComparisonReport, act: ReportAct) => void;
  readonly onClose: () => void;
  /** The estimate dialog of the draft being started or of the report being continued. */
  readonly dialog: ReactNode;
}

function UnitMark({ value }: { readonly value: ComparisonReport['parts'][number]['selection'] }) {
  const unit = unitMark(value);
  return (
    <span className={value === 'failed' ? `${styles.unit} ${styles.unitFailed}` : styles.unit} title={unit.word} {...(value === undefined ? {} : { 'data-unit-mark': value })}>
      {unit.mark}
    </span>
  );
}

function PartsTable({ report, transitions, names }: { readonly report: ComparisonReport; readonly transitions: readonly ComparisonTransition[]; readonly names: ReadonlyMap<string, string> }) {
  if (report.parts.length === 0) return null;
  return (
    <div className={styles.scroller}>
      {report.kind === 'analytic' ? <p className={styles.muted}>Показатели относятся к переходу в целом. Большая сводка нового аналитического отчёта обрабатывается частями с анализом и проверкой каждой части. Отметка завершения относится ко всем предусмотренным частям; отдельные счётчики частей этим интерфейсом API не передаются. Подробный охват сохранён в готовом PDF, исходный MD остаётся полным.</p> : null}
      <table className={styles.table} data-report-parts={report.kind}>
        <thead>
          {report.kind === 'client' ? (
            <tr><th scope="col">Переход</th><th scope="col">Отбор</th><th scope="col">Пунктов</th><th scope="col">Вопросов</th></tr>
          ) : (
            <tr><th scope="col">Переход</th><th scope="col">Анализ</th><th scope="col">Проверка</th><th scope="col">Факты</th><th scope="col">Предупреждения</th></tr>
          )}
        </thead>
        <tbody>
          {report.parts.map((part) => (
            <tr key={part.transition_id}>
              <td>{transitionName(transitions.find((item) => item.transition_id === part.transition_id), names)}</td>
              {report.kind === 'client' ? (
                <>
                  <td><UnitMark value={part.selection} /></td>
                  <td className={styles.numeric}>{part.points ?? ''}</td>
                  <td className={styles.numeric}>{part.questions ?? ''}</td>
                </>
              ) : (
                <>
                  <td><UnitMark value={part.analysis} /></td>
                  <td><UnitMark value={part.verification} /></td>
                  <td className={styles.numeric}>{part.facts === undefined ? '' : `${part.facts.found} / ${part.facts.confirmed} / ${part.facts.contradicted} / ${part.facts.unconfirmed}`}</td>
                  <td className={styles.numeric}>{part.warnings === undefined || part.warnings === 0 ? '' : `${part.warnings} ⓘ`}</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ReportWindowView({
  reports, transitions, names, summaryReady, mayAct, busy, failure, source, onSource, kind, onKind, reuse, onReuse, fileName, onFile,
  onPrepareEstimate, onAct, onClose, dialog,
}: ReportWindowViewProps) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const canPrepare = source === 'series_summary' ? summaryReady : fileName !== null;
  const live = reports.find((report) => report.state !== 'draft');
  return (
    <section className={styles.window} role="group" aria-label={WINDOW_TITLE} data-report-window="">
      <div className={styles.head}>
        <div>
          <h3 className={styles.title}>{WINDOW_TITLE}</h3>
          <p className={styles.subtitle}>{WINDOW_SUBTITLE}</p>
        </div>
        <button type="button" className="am-button am-button--quiet am-button--small" title="Закрыть окно" onClick={onClose}>✕ Закрыть</button>
      </div>
      <FailureBlock failure={failure} />
      {mayAct ? (
        <div className={styles.start} data-report-start="">
          <div className={styles.row}>
            <label className={styles.choice}>
              <input type="radio" name="report-source" checked={source === 'series_summary'} disabled={!summaryReady} onChange={() => onSource('series_summary')} />
              <span data-report-source="series_summary">{REPORT_SOURCE_LABELS.series_summary}</span>
            </label>
            <label className={styles.choice}>
              <input type="radio" name="report-source" checked={source === 'uploaded_md'} onChange={() => onSource('uploaded_md')} />
              <span data-report-source="uploaded_md">{REPORT_SOURCE_LABELS.uploaded_md}</span>
            </label>
            {source === 'uploaded_md' ? (
              <input ref={fileRef} type="file" accept=".md,text/markdown,text/plain" aria-label="MD-файл со сводкой" onChange={(event) => onFile(event.target.files?.[0] ?? null)} />
            ) : null}
          </div>
          {source === 'series_summary' && !summaryReady ? <p className={styles.muted}>{NO_SUMMARY_HINT}</p> : null}
          {source === 'uploaded_md' ? <p className={styles.muted}>{MAX_SOURCE_NOTE}</p> : null}
          <div className={styles.row}>
            {(['client', 'analytic'] as const).map((value) => (
              <label key={value} className={styles.choice} title={REPORT_KIND_TITLES[value]}>
                <input type="radio" name="report-kind" checked={kind === value} onChange={() => onKind(value)} />
                <span data-report-kind={value}>{REPORT_KIND_LABELS[value]}</span>
              </label>
            ))}
          </div>
          <p className={styles.muted}>{kind === 'client'
            ? 'Для отчёта заказчику отбор изменений выполняется одним обращением на переход по фактам сводки. Предел этого режима — 400 000 символов на переход; для большей сводки выберите аналитический отчёт и подготовьте его отдельную оценку.'
            : 'Новый аналитический отчёт разбирает большую MD-сводку по частям: отдельный анализ и проверка фактов. Число обращений берётся из подготовленной оценки; одна часть не означает весь переход. Прежние сохранённые планы не расширяются.'}</p>
          <label className={styles.choice} title="Готовые части прошлых отчётов по тому же содержанию берутся без нового обращения к ИИ.">
            <input type="checkbox" checked={reuse} onChange={(event) => onReuse(event.target.checked)} />
            <span>использовать готовые части прошлых отчётов</span>
          </label>
          <div className={styles.row}>
            <button type="button" className="am-button" disabled={!canPrepare || busy} title="Подготовить черновик и оценку. Модель не вызывается и ничего не тратится: передача начнётся только после вашего подтверждения." data-report-prepare="" onClick={onPrepareEstimate}>
              Подготовить оценку
            </button>
            <span className={styles.muted}>Ответ ИИ — <AiLabel />.</span>
          </div>
        </div>
      ) : null}
      {dialog}
      <h4 className={styles.heading}>Отчёты комплекта</h4>
      {reports.length === 0 ? (
        <p className={styles.muted}>{NO_REPORTS}</p>
      ) : (
        <div className={styles.scroller}>
          <table className={styles.table} data-report-history="">
            <thead>
              <tr><th scope="col">Создан</th><th scope="col">Источник</th><th scope="col">Состояние</th><th scope="col">Ход</th><th scope="col">Действия</th></tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.report_id} className={live?.report_id === report.report_id ? styles.selected : undefined} data-report-state={report.state}>
                  <td>{formatInstant(report.created_at)}</td>
                  <td>
                    <div data-report-kind={report.kind}>{REPORT_KIND_LABELS[report.kind]}</div>
                    <div className={styles.muted}>
                      <span data-report-source={report.source}>{REPORT_SOURCE_LABELS[report.source]}</span>
                      {report.source_name === undefined ? '' : ` · ${report.source_name}`}
                      {report.prepared_from_id === undefined ? '' : ' · подготовлен из аналитического отчёта'}
                    </div>
                  </td>
                  <td>
                    <span className="am-badge am-badge--active" data-report-state={report.state}>{REPORT_STATE_LABELS[report.state]}</span>
                    {isRecordedRoute(report.job) ? <RecordedMark /> : null}
                    {report.stage === undefined || !isLiveReport(report) ? null : (
                      <div className={styles.muted} data-report-stage={report.stage}>{REPORT_STAGE_LABELS[report.stage]}</div>
                    )}
                    {report.failure_reason === undefined ? null : <div className={styles.warning}>{reasonOf(report.failure_reason)}</div>}
                    {report.job?.pause_reason !== undefined && pauseNeedsConsent(report.job.pause_reason) ? (
                      <div className={styles.warning} data-ai-pause-reason={report.job.pause_reason}>Продолжить можно только с новой оценкой и новым подтверждением.</div>
                    ) : null}
                  </td>
                  <td>
                    <div>{reportProgressLine(report)}</div>
                    <div className={styles.muted}>{usageLine(report)}</div>
                    {report.reuse && report.state === 'draft' ? <div className={styles.muted}>готовые части прошлых отчётов будут использованы</div> : null}
                  </td>
                  <td>
                    <span className={styles.actions}>
                      {hasArtifact(report, 'report_pdf') ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" data-report-act="pdf" disabled={busy} onClick={() => onAct(report, 'pdf')}>Скачать PDF</button>
                      ) : null}
                      {hasArtifact(report, 'source_md') ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" data-report-act="source" title="Скачать исходный MD, по которому составлен этот отчёт." disabled={busy} onClick={() => onAct(report, 'source')}>Исходный MD</button>
                      ) : null}
                      {mayAct && canStartReport(report) ? (
                        <button type="button" className="am-button am-button--small" data-report-act="start" disabled={busy} onClick={() => onAct(report, 'start')}>Начать…</button>
                      ) : null}
                      {mayAct && canCancelReport(report) ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" data-report-act="cancel" title="Остановить формирование. Готовые части сохранятся — отчёт можно продолжить." disabled={busy} onClick={() => onAct(report, 'cancel')}>Отменить</button>
                      ) : null}
                      {mayAct && canContinueReport(report) ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" data-report-act="continue" title="Продолжить: готовые переходы берутся из сохранённых, заново отправляются только неподготовленные." disabled={busy} onClick={() => onAct(report, 'continue')}>Продолжить</button>
                      ) : null}
                      {mayAct && canRebuildReport(report) ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" data-report-act="rebuild" title="Сверстать PDF заново из сохранённого текста. Модель не вызывается, ничего не тратится." disabled={busy} onClick={() => onAct(report, 'rebuild')}>Пересобрать PDF</button>
                      ) : null}
                      {mayAct && canPrepareClientReport(report) ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" data-report-act="prepare" title="Отбор главных изменений по каждому переходу из проверенных фактов аналитического отчёта. Оценка и подтверждение — перед передачей." disabled={busy} onClick={() => onAct(report, 'prepare')}>Подготовить отчёт для заказчика</button>
                      ) : null}
                      {mayAct && canDeleteReport(report) ? (
                        <button type="button" className="am-button am-button--small am-button--quiet" data-report-act="delete" title="Убрать отчёт из истории. Опубликованные файлы не удаляются." disabled={busy} onClick={() => onAct(report, 'delete')}>Удалить</button>
                      ) : null}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {live === undefined ? null : (
        <>
          <h4 className={styles.heading}>Ход по переходам</h4>
          <PartsTable report={live} transitions={transitions} names={names} />
        </>
      )}
    </section>
  );
}

function reasonOf(reason: string): string {
  return `Отчёт остановился: ${REASON_WORDS[reason] ?? 'причина не описана'}.`;
}

const REASON_WORDS: Readonly<Record<string, string>> = {
  model_failed: 'модель не дала пригодного ответа',
  pdf_failed: 'не удалось сверстать PDF',
  source_invalid: 'файл сводки не подошёл',
  summary_changed: 'сводка проекта изменилась после подготовки оценки',
};

export interface ReportWindowProps {
  readonly series: ComparisonSeries;
  readonly names: ReadonlyMap<string, string>;
  readonly mayAct: boolean;
  readonly summaryReady?: boolean;
  readonly onClose: () => void;
}

type Open = { readonly kind: 'start' | 'continue'; readonly report: ComparisonReport } | null;

function ReportDialog({ open, onClose }: { readonly open: NonNullable<Open>; readonly onClose: () => void }) {
  const flow = useConsentFlow(
    { kind: 'report', reportId: open.report.report_id },
    open.kind === 'continue' ? { continueReportId: open.report.report_id, onStarted: onClose } : { onStarted: onClose },
  );
  const title = open.kind === 'continue' ? 'Продолжить PDF-отчёт' : 'PDF-отчёт';
  return (
    <EstimatePanel
      title={title}
      consentKind="report"
      confirmLabel={open.kind === 'continue' ? 'Продолжить' : open.report.state === 'draft' ? CONFIRM_LABELS.report : RESTART_CONFIRM_LABELS.report}
      estimate={flow.estimate}
      allowLocalAssembly={open.report.kind === 'analytic' && flow.estimate?.calls === 0 && (flow.estimate.transitions ?? 0) > 0}
      loading={flow.loading}
      failure={flow.failure}
      agreedDigest={flow.agreedDigest}
      busy={flow.busy}
      onAgree={flow.agree}
      onConfirm={flow.confirm}
      onCancel={onClose}
    />
  );
}

export function ReportWindow({ series, names, mayAct, summaryReady = true, onClose }: ReportWindowProps) {
  const reports = useReports(series.series_id);
  const command = useReportCommand();
  const download = useDownload();
  const [source, setSource] = useState<ComparisonReportSource>(summaryReady ? 'series_summary' : 'uploaded_md');
  const [kind, setKind] = useState<ComparisonReportKind>('client');
  const [reuse, setReuse] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [open, setOpen] = useState<Open>(null);
  if (reports.isPending) return <LoadingState what="отчёты" />;
  if (reports.isError) {
    return <FailureBlock failure={comparisonFailure(reports.error)} title="Отчёты не открылись" />;
  }
  const error = command.error ?? download.error ?? null;
  const act = (report: ComparisonReport, what: ReportAct): void => {
    command.reset();
    download.reset();
    const id = report.report_id as ComparisonReportId;
    switch (what) {
      case 'start': return setOpen({ kind: 'start', report });
      case 'continue':
        if (pauseNeedsConsent(report.job?.pause_reason)) return setOpen({ kind: 'continue', report });
        return void command.mutate({ act: 'continue', reportId: id });
      case 'cancel': return void command.mutate({ act: 'cancel', reportId: id });
      case 'rebuild': return void command.mutate({ act: 'rebuild', reportId: id });
      case 'delete': return void command.mutate({ act: 'delete', reportId: id });
      case 'prepare': return void command.mutate({ act: 'prepare', reportId: id, reuse }, { onSuccess: (draft) => setOpen({ kind: 'start', report: draft }) });
      case 'pdf': return void download.mutate({ kind: 'report-pdf', reportId: id, fileName: pdfName(report) });
      case 'source': return void download.mutate({ kind: 'report-md', reportId: id, fileName: sourceMdName(report) });
    }
  };
  return (
    <ReportWindowView
      reports={reports.data}
      transitions={series.transitions ?? []}
      names={names}
      summaryReady={summaryReady}
      mayAct={mayAct}
      busy={command.isPending || download.isPending}
      failure={error === null ? null : comparisonFailure(error)}
      source={source}
      onSource={setSource}
      kind={kind}
      onKind={setKind}
      reuse={reuse}
      onReuse={setReuse}
      fileName={file?.name ?? null}
      onFile={setFile}
      onPrepareEstimate={() => {
        command.reset();
        const done = { onSuccess: (draft: ComparisonReport) => setOpen({ kind: 'start', report: draft }) };
        if (source === 'series_summary') command.mutate({ act: 'create', seriesId: series.series_id, kind, reuse }, done);
        else if (file !== null) command.mutate({ act: 'upload', seriesId: series.series_id, kind, reuse, sourceName: file.name, file }, done);
      }}
      onAct={act}
      onClose={onClose}
      dialog={open === null ? null : <ReportDialog open={open} onClose={() => setOpen(null)} />}
    />
  );
}
