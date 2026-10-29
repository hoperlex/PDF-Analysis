'use client';

/**
 * The commands of the AI layer of «Сравнение версий» (wave C2). Every one is an expert's act and carries an `Idempotency-Key`
 * (`useKeyedCommand`): the key is minted when the reader expresses the intent and reused on every retry of it.
 *
 * **A start carries the digest of the estimate that was shown.** {@link useAiStart} takes the estimate the dialog displayed and
 * sends `consentOf(thatEstimate)`; the digest is part of the command's signature, so a new estimate is a new intent and a new key,
 * and a retry of the same one reuses its key. Nothing in this file computes a digest, reads a different estimate or sends a
 * consent that was not given: a start without a confirmed line is `422 comparison_consent_required` at the server, and the dialog
 * does not offer it.
 */

import type {
  ComparisonAiConsent,
  ComparisonAiEstimate,
  ComparisonAiJob,
  ComparisonAiJobId,
  ComparisonLaunchItem,
  ComparisonLaunchQueue,
  ComparisonReport,
  ComparisonReportId,
  ComparisonReportKind,
  ComparisonSeriesId,
  ProjectUid,
} from '@/shared/api';
import {
  cancelComparisonAiPairCheck,
  cancelComparisonAiSheetChanges,
  cancelComparisonReport,
  cancelComparisonSpecification,
  clearComparisonLaunchQueue,
  continueComparisonReport,
  createComparisonReport,
  deleteComparisonReport,
  dequeueComparisonAiSheetChanges,
  enqueueComparisonLaunch,
  finishComparisonAiSheetChanges,
  pauseComparisonAiPairCheck,
  pauseComparisonAiSheetChanges,
  pauseComparisonLaunchQueue,
  prepareComparisonClientReport,
  rebuildComparisonReportPdf,
  removeComparisonLaunchEntry,
  resumeComparisonAiPairCheck,
  resumeComparisonAiSheetChanges,
  resumeComparisonLaunchQueue,
  retryComparisonAiSheetChanges,
  startComparisonAiPairCheck,
  startComparisonAiSheetChanges,
  startComparisonReport,
  startComparisonSheetDescription,
  startComparisonSpecification,
  uploadComparisonReportSource,
} from '@/shared/api';

import { consentOf } from '../model/estimate';

import type { EstimateScope } from './use-ai';
import { estimateScopeKey } from './use-ai';
import { useKeyedCommand } from './use-keyed-command';

// ------------------------------------------------------------------------------ the start

export interface StartAiCommand {
  readonly scope: EstimateScope;
  /** The estimate **as the dialog showed it**: its digest is the consent's. */
  readonly shown: ComparisonAiEstimate;
  /** «Заново» / «Описать заново» / «Сформировать заново». */
  readonly restart?: boolean;
  /** «Повторить листы с ошибкой»: the job whose failed sheets are described again. */
  readonly retryJobId?: ComparisonAiJobId;
}

/** The consent that goes with a command: the shown estimate's digest, confirmed. Exported so a test can pin it. */
export function consentFor(command: Pick<StartAiCommand, 'shown'>): ComparisonAiConsent {
  return consentOf(command.shown);
}

/** The request an AI start sends. Exported so a test can pin that it carries the digest of the estimate that was shown. */
export async function sendAiStart(command: StartAiCommand, idempotencyKey: string): Promise<ComparisonAiJob | ComparisonReport> {
  const consent = consentFor(command);
  const scope = command.scope;
  switch (scope.kind) {
    case 'pair_check':
      return (
        await startComparisonAiPairCheck({
          path: { project_uid: scope.projectUid, document_uid: scope.documentUid },
          body: { consent },
          idempotencyKey,
        })
      ).data;
    case 'sheet_changes':
      if (command.retryJobId !== undefined) {
        return (
          await retryComparisonAiSheetChanges({ path: { comparison_ai_job_id: command.retryJobId }, body: { consent }, idempotencyKey })
        ).data;
      }
      return (
        await startComparisonAiSheetChanges({
          path: { comparison_series_id: scope.seriesId },
          body: { consent, ...(command.restart === true ? { restart: true } : {}) },
          idempotencyKey,
        })
      ).data;
    case 'sheet':
      return (
        await startComparisonSheetDescription({ path: { comparison_sheet_pair_id: scope.pairId }, body: { consent }, idempotencyKey })
      ).data;
    case 'spec':
      return (
        await startComparisonSpecification({ path: { comparison_transition_id: scope.transitionId }, body: { consent }, idempotencyKey })
      ).data;
    case 'report':
      return (await startComparisonReport({ path: { comparison_report_id: scope.reportId }, body: { consent }, idempotencyKey })).data;
  }
}

/** Every AI start: «Проверить», «Запустить», «Описать заново», «Передать и описать», the specification, the report. */
export function useAiStart() {
  return useKeyedCommand<StartAiCommand, ComparisonAiJob | ComparisonReport>({
    // The digest is in the signature: a new estimate is a new intent with a new key; the same estimate retried keeps its key.
    signatureOf: (command) =>
      ['ai-start', estimateScopeKey(command.scope), command.shown.estimate_digest, command.restart === true, command.retryJobId ?? ''].join('|'),
    send: sendAiStart,
  });
}

// ------------------------------------------------------------------------------ the controls of a job

export type AiJobMethod = 'pair_check' | 'sheet_changes' | 'spec';
export type AiJobAct = 'pause' | 'resume' | 'cancel' | 'finish' | 'dequeue';

export interface AiJobActCommand {
  readonly method: AiJobMethod;
  readonly act: AiJobAct;
  readonly jobId: ComparisonAiJobId;
  /** A resume after `overrun` or `route_changed` carries the consent of a new estimate. */
  readonly shown?: ComparisonAiEstimate;
}

/** Which controls exist for which method (`CMP-SEAL-C2` §3): the pair check pauses, resumes and cancels; a specification only cancels. */
export const JOB_ACTS: Readonly<Record<AiJobMethod, readonly AiJobAct[]>> = {
  pair_check: ['pause', 'resume', 'cancel'],
  sheet_changes: ['pause', 'resume', 'cancel', 'finish', 'dequeue'],
  spec: ['cancel'],
};

async function actOnJob(command: AiJobActCommand, idempotencyKey: string): Promise<ComparisonAiJob> {
  if (!JOB_ACTS[command.method].includes(command.act)) {
    throw new Error(`The ${command.method} job has no control ${command.act}.`);
  }
  const path = { comparison_ai_job_id: command.jobId };
  const base = { path, idempotencyKey } as const;
  const body = { body: command.shown === undefined ? {} : { consent: consentOf(command.shown) } } as const;
  if (command.method === 'pair_check') {
    if (command.act === 'pause') return (await pauseComparisonAiPairCheck(base)).data;
    if (command.act === 'resume') return (await resumeComparisonAiPairCheck({ ...base, ...body })).data;
    return (await cancelComparisonAiPairCheck(base)).data;
  }
  if (command.method === 'spec') return (await cancelComparisonSpecification(base)).data;
  switch (command.act) {
    case 'pause': return (await pauseComparisonAiSheetChanges(base)).data;
    case 'resume': return (await resumeComparisonAiSheetChanges({ ...base, ...body })).data;
    case 'finish': return (await finishComparisonAiSheetChanges(base)).data;
    case 'dequeue': return (await dequeueComparisonAiSheetChanges(base)).data;
    default: return (await cancelComparisonAiSheetChanges(base)).data;
  }
}

/** «Пауза», «Продолжить», «Отменить», «Досчитать», «Из очереди» / «Убрать из очереди». */
export function useAiJobAct() {
  return useKeyedCommand<AiJobActCommand, ComparisonAiJob>({
    signatureOf: (command) => ['ai-job', command.method, command.act, command.jobId, command.shown?.estimate_digest ?? ''].join('|'),
    send: actOnJob,
  });
}

// ------------------------------------------------------------------------------ the reports

export type ReportCommand =
  | { readonly act: 'create'; readonly seriesId: ComparisonSeriesId; readonly kind: ComparisonReportKind; readonly reuse: boolean }
  | {
      readonly act: 'upload';
      readonly seriesId: ComparisonSeriesId;
      readonly kind: ComparisonReportKind;
      readonly reuse: boolean;
      readonly sourceName: string;
      readonly file: Blob;
    }
  | { readonly act: 'cancel' | 'rebuild' | 'delete'; readonly reportId: ComparisonReportId }
  | { readonly act: 'continue'; readonly reportId: ComparisonReportId; readonly shown?: ComparisonAiEstimate }
  | { readonly act: 'prepare'; readonly reportId: ComparisonReportId; readonly reuse: boolean };

function reportSignature(command: ReportCommand): string {
  switch (command.act) {
    case 'create': return ['report', 'create', command.seriesId, command.kind, command.reuse].join('|');
    case 'upload': return ['report', 'upload', command.seriesId, command.kind, command.reuse, command.sourceName, command.file.size].join('|');
    case 'continue': return ['report', 'continue', command.reportId, command.shown?.estimate_digest ?? ''].join('|');
    case 'prepare': return ['report', 'prepare', command.reportId, command.reuse].join('|');
    default: return ['report', command.act, command.reportId].join('|');
  }
}

async function sendReport(command: ReportCommand, idempotencyKey: string): Promise<ComparisonReport> {
  switch (command.act) {
    case 'create':
      return (
        await createComparisonReport({
          path: { comparison_series_id: command.seriesId },
          body: { kind: command.kind, reuse: command.reuse },
          idempotencyKey,
        })
      ).data;
    case 'upload':
      return (
        await uploadComparisonReportSource({
          path: { comparison_series_id: command.seriesId },
          query: { kind: command.kind, reuse: command.reuse, source_name: command.sourceName },
          body: command.file,
          idempotencyKey,
        })
      ).data;
    case 'cancel': return (await cancelComparisonReport({ path: { comparison_report_id: command.reportId }, idempotencyKey })).data;
    case 'rebuild': return (await rebuildComparisonReportPdf({ path: { comparison_report_id: command.reportId }, idempotencyKey })).data;
    case 'delete': return (await deleteComparisonReport({ path: { comparison_report_id: command.reportId }, idempotencyKey })).data;
    case 'continue':
      return (
        await continueComparisonReport({
          path: { comparison_report_id: command.reportId },
          body: command.shown === undefined ? {} : { consent: consentOf(command.shown) },
          idempotencyKey,
        })
      ).data;
    case 'prepare':
      return (
        await prepareComparisonClientReport({ path: { comparison_report_id: command.reportId }, body: { reuse: command.reuse }, idempotencyKey })
      ).data;
  }
}

/** «Сформировать PDF-отчёт…» (a draft, no spend), «Отменить», «Продолжить», «Пересобрать PDF», «Удалить», «Подготовить отчёт для заказчика». */
export function useReportCommand() {
  return useKeyedCommand<ReportCommand, ComparisonReport>({ signatureOf: reportSignature, send: sendReport });
}

// ------------------------------------------------------------------------------ the launch queue

export type QueueCommand =
  | { readonly act: 'enqueue'; readonly projectUid: ProjectUid; readonly items: readonly ComparisonLaunchItem[]; readonly restart?: boolean }
  | { readonly act: 'pause' | 'resume' | 'clear'; readonly projectUid: ProjectUid }
  | { readonly act: 'remove'; readonly entryId: string };

function queueSignature(command: QueueCommand): string {
  switch (command.act) {
    case 'enqueue':
      return ['queue', 'enqueue', command.projectUid, command.restart === true, ...command.items.map((item) => `${item.document_uid}:${item.step}:${item.consent?.estimate_digest ?? ''}`)].join('|');
    case 'remove': return ['queue', 'remove', command.entryId].join('|');
    default: return ['queue', command.act, command.projectUid].join('|');
  }
}

async function sendQueue(command: QueueCommand, idempotencyKey: string): Promise<ComparisonLaunchQueue> {
  switch (command.act) {
    case 'enqueue':
      return (
        await enqueueComparisonLaunch({
          path: { project_uid: command.projectUid },
          body: { items: [...command.items], ...(command.restart === true ? { restart: true } : {}) },
          idempotencyKey,
        })
      ).data;
    case 'pause': return (await pauseComparisonLaunchQueue({ path: { project_uid: command.projectUid }, idempotencyKey })).data;
    case 'resume': return (await resumeComparisonLaunchQueue({ path: { project_uid: command.projectUid }, idempotencyKey })).data;
    case 'clear': return (await clearComparisonLaunchQueue({ path: { project_uid: command.projectUid }, idempotencyKey })).data;
    case 'remove':
      return (await removeComparisonLaunchEntry({ path: { comparison_launch_entry_id: command.entryId as never }, idempotencyKey })).data;
  }
}

/** «Запустить выбранные по очереди», «Пауза очереди», «Продолжить очередь», «Очистить», «✕». */
export function useQueueCommand() {
  return useKeyedCommand<QueueCommand, ComparisonLaunchQueue>({ signatureOf: queueSignature, send: sendQueue });
}

