'use client';

/**
 * The dialogs of the AI steps of «Проекты и этапы» (`version-comparison-projects.js:540-606` `confirmDialog`, `lunaDialog`,
 * `aiDialog`, `reportDialog`, `runSelected`): **every AI start shows the estimate and the consent line**, through the one
 * `EstimatePanel`, and the start carries the digest of the estimate that was shown.
 *
 * {@link AiStartDialog} is the dialog of a step with its scope (a pair check, the description of a series, a resume after an
 * overrun); {@link ReportDraftDialog} makes the report's draft first (no model, nothing spent: the contract's two-step report) and
 * then asks for the consent to its estimate; {@link SelectionDialog} shows the first eight selected steps and the estimate of each
 * AI step that has one, and queues them with the digests the reader saw.
 */

import { useEffect, useRef, useState } from 'react';

import type { ComparisonAiJobId, ComparisonLaunchItem, ComparisonReportId, ComparisonReportKind, ComparisonSeriesId, ProjectUid } from '@/shared/api';
import type { AiJobMethod, ConsentKind, EstimateScope, SelectionItem } from '@/entities/version-series';
import {
  EstimatePanel,
  QUEUE_ENQUEUE_LABEL,
  STEP_LABELS,
  comparisonFailure,
  consentOf,
  estimateLines,
  previewLines,
  selectionTitle,
  useConsentFlow,
  useQueueCommand,
  useReportCommand,
  useSelectionEstimates,
  CONSENT_LINES,
} from '@/entities/version-series';
import { CommandRefusal } from './module-state';
import styles from './ai-steps.module.css';

export interface AiStartDialogProps {
  readonly title: string;
  readonly scope: EstimateScope;
  readonly consentKind: ConsentKind;
  readonly confirmLabel: string;
  readonly restart?: boolean;
  /** A resume of a paused job (after `overrun` or `route_changed`) is a new consent for what is left. */
  readonly resumeJob?: { readonly method: AiJobMethod; readonly jobId: ComparisonAiJobId };
  readonly continueReportId?: ComparisonReportId;
  /** «Повторить листы с ошибкой»: the job whose failed sheets are described again. */
  readonly retryJobId?: ComparisonAiJobId;
  readonly intro?: string;
  readonly onDone: () => void;
  readonly onCancel: () => void;
}

export function AiStartDialog({ title, scope, consentKind, confirmLabel, restart, resumeJob, continueReportId, retryJobId, intro, onDone, onCancel }: AiStartDialogProps) {
  const flow = useConsentFlow(scope, {
    ...(restart === true ? { restart: true } : {}),
    ...(resumeJob === undefined ? {} : { resumeJob }),
    ...(continueReportId === undefined ? {} : { continueReportId }),
    ...(retryJobId === undefined ? {} : { retryJobId }),
    onStarted: onDone,
  });
  return (
    <EstimatePanel
      title={title}
      consentKind={consentKind}
      confirmLabel={confirmLabel}
      estimate={flow.estimate}
      loading={flow.loading}
      failure={flow.failure}
      agreedDigest={flow.agreedDigest}
      busy={flow.busy}
      onAgree={flow.agree}
      onConfirm={flow.confirm}
      onCancel={onCancel}
      intro={intro === undefined ? undefined : <p className="am-note">{intro}</p>}
    />
  );
}

export interface ReportDraftDialogProps {
  readonly title: string;
  readonly seriesId: ComparisonSeriesId;
  readonly kind?: ComparisonReportKind;
  readonly confirmLabel: string;
  readonly onDone: () => void;
  readonly onCancel: () => void;
}

/**
 * «Сформировать PDF-отчёт»: a draft is made first (it calls no model and spends nothing, `createComparisonReport`), so there is an
 * estimate to consent to; the start then consents to that estimate. A draft the reader does not start stays in the report history
 * of the series, where «Удалить» takes it away.
 */
export function ReportDraftDialog({ title, seriesId, kind = 'client', confirmLabel, onDone, onCancel }: ReportDraftDialogProps) {
  const create = useReportCommand();
  const asked = useRef(false);
  const [draftId, setDraftId] = useState<ComparisonReportId | null>(null);
  useEffect(() => {
    if (asked.current) return;
    asked.current = true;
    create.mutate({ act: 'create', seriesId, kind, reuse: true }, { onSuccess: (report) => setDraftId(report.report_id) });
  }, []);
  if (draftId === null) {
    const failure = create.error === null ? null : comparisonFailure(create.error);
    return (
      <section className="am-note" role="group" aria-label={title} data-estimate-panel="draft">
        <h3>{title}</h3>
        {failure === null ? <p role="status">Готовим черновик отчёта и оценку: модель не вызывается, ничего не тратится…</p> : <CommandRefusal failure={failure} />}
        <button type="button" className="am-button am-button--quiet" onClick={onCancel}>Отмена</button>
      </section>
    );
  }
  return (
    <AiStartDialog
      title={title}
      scope={{ kind: 'report', reportId: draftId }}
      consentKind="report"
      confirmLabel={confirmLabel}
      onDone={onDone}
      onCancel={onCancel}
    />
  );
}

export interface SelectionDialogProps {
  readonly projectUid: ProjectUid;
  readonly items: readonly (SelectionItem & { readonly label: string })[];
  readonly restart: boolean;
  /** The queue is stopped or busy: said once, as the original does (`:410-415`). */
  readonly queueNote: string;
  readonly onDone: () => void;
  readonly onCancel: () => void;
}

export function SelectionDialog({ projectUid, items, restart, queueNote, onDone, onCancel }: SelectionDialogProps) {
  const estimates = useSelectionEstimates(projectUid, items, true);
  const enqueue = useQueueCommand();
  const [agreedDigests, setAgreedDigests] = useState<readonly string[] | null>(null);
  const sets = new Set(items.map((item) => item.documentUid)).size;
  const held = (estimates.data ?? []).filter((row) => row.estimate !== null);
  const digests = held.map((row) => row.estimate?.estimate_digest ?? '');
  // One tick covers the estimates on screen: it is void as soon as any estimate on screen has a digest that was not ticked.
  const agreed = held.length === 0 || (agreedDigests !== null && held.every((row) => agreedDigests.includes(row.estimate?.estimate_digest ?? '')));
  const failure = enqueue.error === null ? null : comparisonFailure(enqueue.error);
  const send = (): void => {
    const body: ComparisonLaunchItem[] = items.map((item) => {
      const row = (estimates.data ?? []).find((entry) => entry.item.documentUid === item.documentUid && entry.item.step === item.step);
      return row?.estimate === undefined || row.estimate === null
        ? { document_uid: item.documentUid, step: item.step }
        : { document_uid: item.documentUid, step: item.step, consent: consentOf(row.estimate) };
    });
    enqueue.mutate({ act: 'enqueue', projectUid, items: body, restart }, { onSuccess: onDone });
  };
  return (
    <section className={styles.aiBlock} role="group" aria-label={selectionTitle(items.length, sets)} data-selection-dialog="">
      <h3 className={styles.aiTitle}>{selectionTitle(items.length, sets)}</h3>
      <p className="am-note">Шаги идут по одному: комплект за комплектом, внутри комплекта — слева направо.</p>
      <ol className={styles.stripList}>
        {previewLines(items).map((line) => (
          <li key={line} className={styles.stripEntry}>{line}</li>
        ))}
      </ol>
      {queueNote === '' ? null : <p className={styles.warning} data-queue-note="">{queueNote}</p>}
      {estimates.isPending && items.some((item) => item.step === 'ai_pairs' || item.step === 'ai_changes') ? (
        <p className="am-note" role="status">Оценка объёма…</p>
      ) : null}
      {(estimates.data ?? []).map((row) => (
        <div key={`${row.item.documentUid}:${row.item.step}`} className={styles.reportRow} data-selection-estimate={row.estimate === null ? 'none' : row.estimate.method}>
          <strong>{items.find((item) => item.documentUid === row.item.documentUid && item.step === row.item.step)?.label ?? STEP_LABELS[row.item.step]}</strong>
          {row.estimate === null ? (
            row.why === '' ? null : <span className={styles.hint}>{row.why} Шаг встанет в очередь и будет ждать подтверждения.</span>
          ) : (
            estimateLines(row.estimate).slice(0, 4).map((line) => <span key={line.key} className={styles.hint}>{line.text}</span>)
          )}
        </div>
      ))}
      {held.length === 0 ? null : (
        <label className={styles.cellSelect} data-consent-line="">
          <input
            type="checkbox"
            checked={agreed}
            disabled={enqueue.isPending}
            onChange={(event) => setAgreedDigests(event.target.checked ? digests : null)}
          />
          <span>{CONSENT_LINES.sheet_changes}</span>
        </label>
      )}
      <CommandRefusal failure={failure} />
      <div className={styles.reportActions}>
        <button type="button" className="am-button" disabled={!agreed || enqueue.isPending || estimates.isPending} data-selection-confirm="" onClick={send}>
          {enqueue.isPending ? 'Запуск…' : QUEUE_ENQUEUE_LABEL}
        </button>
        <button type="button" className="am-button am-button--quiet" disabled={enqueue.isPending} onClick={onCancel}>
          Отмена
        </button>
      </div>
    </section>
  );
}
