'use client';

/**
 * The reads of the AI layer of «Сравнение версий» (wave C2): the pair check and its hints, the AI description of a series and of
 * one sheet, the specifications, the reports, the launch queue of a project and the installation's AI queue, and the estimate
 * an AI start would consent to.
 *
 * Every read starts nothing and calls no model (the contract says so of each). A read re-reads itself while the thing it shows
 * moves — a job that is queued or running, a report that is live — on a named interval and never otherwise
 * (`tests/unit/run/polling.test.ts` holds this file to that, as it holds the other comparison reads). A module that is not wired
 * answers `503 dependency_unavailable`; the query keeps the error, the widget shows it as the module's state.
 */

import { useQuery } from '@tanstack/react-query';

import type {
  ComparisonAiEstimate,
  ComparisonAiPairCheck,
  ComparisonAiPairHint,
  ComparisonAiQueue,
  ComparisonAiSheetChanges,
  ComparisonLaunchQueue,
  ComparisonReport,
  ComparisonReportId,
  ComparisonReviewSheet,
  ComparisonSeriesId,
  ComparisonSheetDescription,
  ComparisonSheetDescriptionHistory,
  ComparisonSheetPairId,
  ComparisonSpecChangeKind,
  ComparisonSpecChangePage,
  ComparisonSpecification,
  ComparisonTransitionId,
  DocumentUid,
  ProjectUid,
} from '@/shared/api';
import {
  estimateComparisonAiPairCheck,
  estimateComparisonAiSheetChanges,
  estimateComparisonSheetDescription,
  estimateComparisonSpecification,
  getComparisonAiPairCheck,
  getComparisonAiQueue,
  getComparisonAiSheetChanges,
  getComparisonLaunchQueue,
  getComparisonReport,
  getComparisonSheetDescription,
  listComparisonAiPairHints,
  listComparisonReports,
  listComparisonReviewSheets,
  listComparisonSheetDescriptionHistory,
  listComparisonSpecificationChanges,
  listComparisonSpecifications,
} from '@/shared/api';

import { COMPARISON_KEYS } from './keys';

/** A job or a report that moves is read again every 3 s (`version-comparison.js:865`, `md-report.js:121`). */
export const AI_POLL_MS = 3_000;
/** The queues are read every 5 s while something waits (`version-comparison.js:956`). */
export const AI_QUEUE_POLL_MS = 5_000;

const HINT_PAGE_LIMIT = 200;
const HINT_PAGE_CAP = 5;

function jobMoves(state: string | undefined): boolean {
  return state === 'queued' || state === 'running';
}

export function useAiPairCheck(projectUid: ProjectUid, documentUid: DocumentUid, enabled: boolean) {
  return useQuery<ComparisonAiPairCheck>({
    queryKey: COMPARISON_KEYS.aiPair(projectUid, documentUid),
    queryFn: async () => (await getComparisonAiPairCheck({ path: { project_uid: projectUid, document_uid: documentUid } })).data,
    refetchInterval: (query) => (jobMoves(query.state.data?.job?.state) ? AI_POLL_MS : false),
    enabled,
    retry: false,
  });
}

/** The hints of the AI check of doubtful pairs, newest first, pages followed up to a cap. */
export function useAiPairHints(projectUid: ProjectUid, documentUid: DocumentUid, enabled: boolean) {
  return useQuery<ComparisonAiPairHint[]>({
    queryKey: COMPARISON_KEYS.aiHints(projectUid, documentUid),
    queryFn: async () => {
      const hints: ComparisonAiPairHint[] = [];
      let cursor: string | undefined;
      for (let page = 0; page < HINT_PAGE_CAP; page += 1) {
        const answer = (
          await listComparisonAiPairHints({
            path: { project_uid: projectUid, document_uid: documentUid },
            query: { limit: HINT_PAGE_LIMIT, ...(cursor === undefined ? {} : { cursor }) },
          })
        ).data;
        hints.push(...answer.items);
        if (answer.page.next_cursor === null) break;
        cursor = answer.page.next_cursor;
      }
      return hints;
    },
    enabled,
    retry: false,
  });
}

export function useAiSheetChanges(seriesId: ComparisonSeriesId | null) {
  return useQuery<ComparisonAiSheetChanges>({
    queryKey: COMPARISON_KEYS.aiSheets(seriesId ?? 'none'),
    queryFn: async () => (await getComparisonAiSheetChanges({ path: { comparison_series_id: seriesId as ComparisonSeriesId } })).data,
    refetchInterval: (query) => (jobMoves(query.state.data?.job?.state) ? AI_POLL_MS : false),
    enabled: seriesId !== null,
    retry: false,
  });
}

export function useSpecifications(seriesId: ComparisonSeriesId | null) {
  return useQuery<ComparisonSpecification[]>({
    queryKey: COMPARISON_KEYS.specs(seriesId ?? 'none'),
    queryFn: async () =>
      (await listComparisonSpecifications({ path: { comparison_series_id: seriesId as ComparisonSeriesId }, query: { limit: 200 } })).data.items,
    refetchInterval: (query) => ((query.state.data ?? []).some((spec) => spec.state === 'running') ? AI_POLL_MS : false),
    enabled: seriesId !== null,
    retry: false,
  });
}

export function useSpecificationChanges(transitionId: ComparisonTransitionId | null, kind?: ComparisonSpecChangeKind) {
  return useQuery<ComparisonSpecChangePage>({
    queryKey: [...COMPARISON_KEYS.specChanges(transitionId ?? 'none'), kind ?? 'all'],
    queryFn: async () =>
      (
        await listComparisonSpecificationChanges({
          path: { comparison_transition_id: transitionId as ComparisonTransitionId },
          query: { limit: 200, ...(kind === undefined ? {} : { kind }) },
        })
      ).data,
    enabled: transitionId !== null,
    retry: false,
  });
}

/** The reports of a series, newest first. */
export function useReports(seriesId: ComparisonSeriesId | null, enabled = true) {
  return useQuery<ComparisonReport[]>({
    queryKey: COMPARISON_KEYS.reports(seriesId ?? 'none'),
    queryFn: async () =>
      (await listComparisonReports({ path: { comparison_series_id: seriesId as ComparisonSeriesId }, query: { limit: 50 } })).data.items,
    refetchInterval: (query) => ((query.state.data ?? []).some((report) => report.state === 'queued' || report.state === 'running') ? AI_POLL_MS : false),
    enabled: seriesId !== null && enabled,
    retry: false,
  });
}

export function useLaunchQueue(projectUid: ProjectUid | null) {
  return useQuery<ComparisonLaunchQueue>({
    queryKey: COMPARISON_KEYS.launchQueue(projectUid ?? 'none'),
    queryFn: async () => (await getComparisonLaunchQueue({ path: { project_uid: projectUid as ProjectUid } })).data,
    refetchInterval: (query) => (query.state.data?.state === 'running' ? AI_QUEUE_POLL_MS : false),
    enabled: projectUid !== null,
    retry: false,
  });
}

export function useAiQueue() {
  return useQuery<ComparisonAiQueue>({
    queryKey: COMPARISON_KEYS.aiQueue(),
    queryFn: async () => (await getComparisonAiQueue({})).data,
    refetchInterval: (query) => ((query.state.data?.items.length ?? 0) > 0 ? AI_QUEUE_POLL_MS : false),
    retry: false,
  });
}

/** The stored description of one sheet pair; it is read again while the sheet is queued or being described. */
export function useSheetDescription(pairId: ComparisonSheetPairId | null) {
  return useQuery<ComparisonSheetDescription>({
    queryKey: COMPARISON_KEYS.description(pairId ?? 'none'),
    queryFn: async () => (await getComparisonSheetDescription({ path: { comparison_sheet_pair_id: pairId as ComparisonSheetPairId } })).data,
    refetchInterval: (query) => (query.state.data?.state === 'queued' || query.state.data?.state === 'running' ? AI_POLL_MS : false),
    enabled: pairId !== null,
    retry: false,
  });
}

export function useDescriptionHistory(pairId: ComparisonSheetPairId | null, enabled: boolean) {
  return useQuery<ComparisonSheetDescriptionHistory>({
    queryKey: COMPARISON_KEYS.descriptionHistory(pairId ?? 'none'),
    queryFn: async () =>
      (await listComparisonSheetDescriptionHistory({ path: { comparison_sheet_pair_id: pairId as ComparisonSheetPairId }, query: { limit: 50 } })).data,
    enabled: pairId !== null && enabled,
    retry: false,
  });
}

/** The «Проверить» list and the added and removed single sheets of a transition. */
export function useReviewSheets(transitionId: ComparisonTransitionId | null, enabled: boolean) {
  return useQuery<ComparisonReviewSheet[]>({
    queryKey: COMPARISON_KEYS.reviewSheets(transitionId ?? 'none'),
    queryFn: async () =>
      (await listComparisonReviewSheets({ path: { comparison_transition_id: transitionId as ComparisonTransitionId }, query: { limit: 200 } })).data.items,
    enabled: transitionId !== null && enabled,
    retry: false,
  });
}

// ------------------------------------------------------------------------------ the estimate

/** What an estimate is asked for: the scope of the AI start it belongs to. */
export type EstimateScope =
  | { readonly kind: 'pair_check'; readonly projectUid: ProjectUid; readonly documentUid: DocumentUid }
  | { readonly kind: 'sheet_changes'; readonly seriesId: ComparisonSeriesId; readonly onlyFailed?: boolean }
  | { readonly kind: 'sheet'; readonly pairId: ComparisonSheetPairId }
  | { readonly kind: 'spec'; readonly transitionId: ComparisonTransitionId }
  /** A report's estimate is the one its draft carries: the draft is read, nothing is computed twice. */
  | { readonly kind: 'report'; readonly reportId: ComparisonReportId };

export function estimateScopeKey(scope: EstimateScope): string {
  switch (scope.kind) {
    case 'pair_check': return `pair_check|${scope.projectUid}|${scope.documentUid}`;
    case 'sheet_changes': return `sheet_changes|${scope.seriesId}|${scope.onlyFailed === true ? 'failed' : 'all'}`;
    case 'sheet': return `sheet|${scope.pairId}`;
    case 'spec': return `spec|${scope.transitionId}`;
    case 'report': return `report|${scope.reportId}`;
  }
}

async function readEstimate(scope: EstimateScope): Promise<ComparisonAiEstimate> {
  switch (scope.kind) {
    case 'pair_check':
      return (await estimateComparisonAiPairCheck({ path: { project_uid: scope.projectUid, document_uid: scope.documentUid } })).data;
    case 'sheet_changes':
      return (
        await estimateComparisonAiSheetChanges({
          path: { comparison_series_id: scope.seriesId },
          ...(scope.onlyFailed === true ? { query: { only_failed: true } } : {}),
        })
      ).data;
    case 'sheet':
      return (await estimateComparisonSheetDescription({ path: { comparison_sheet_pair_id: scope.pairId } })).data;
    case 'spec':
      return (await estimateComparisonSpecification({ path: { comparison_transition_id: scope.transitionId } })).data;
    case 'report': {
      const report = (await getComparisonReport({ path: { comparison_report_id: scope.reportId } })).data;
      if (report.estimate === undefined) throw new Error('У отчёта, который не черновик, нет оценки для подтверждения.');
      return report.estimate;
    }
  }
}

/**
 * The estimate of an AI start, read when the dialog opens. It is never kept: a stale one is exactly what the digest guards
 * against, so the read is fresh every time (`staleTime` 0, no retry) and is read again after a refused start.
 */
export function useAiEstimate(scope: EstimateScope | null) {
  return useQuery<ComparisonAiEstimate>({
    queryKey: COMPARISON_KEYS.estimate(scope === null ? 'none' : estimateScopeKey(scope)),
    queryFn: () => readEstimate(scope as EstimateScope),
    enabled: scope !== null,
    staleTime: 0,
    gcTime: 0,
    retry: false,
  });
}
