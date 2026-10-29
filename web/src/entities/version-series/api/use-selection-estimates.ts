'use client';

/**
 * The estimates behind «Запустить выбранные по очереди» (`version-comparison-projects.js:398-419`; seal §3 decision 5).
 *
 * The launch queue takes one consent **per set and AI step, when the step's estimate exists**; a step whose estimate does not
 * exist yet (the series is not computed, the summary is not there, the module is not wired) is queued without one and waits as
 * «ждёт подтверждения». This reads, for each selected AI step, the estimate the reader is about to consent to, and says why
 * there is none for the rest. It reads only; the dialog shows every estimate it holds and the enqueue carries their digests.
 */

import { useQuery } from '@tanstack/react-query';

import type { ComparisonAiEstimate, ComparisonStepId, DocumentUid, ProjectUid } from '@/shared/api';
import { estimateComparisonAiPairCheck, estimateComparisonAiSheetChanges, listComparisonSeries } from '@/shared/api';

import { comparisonFailure } from '../model/failure';
import { latestSeries } from '../model/series-words';

import { COMPARISON_KEYS } from './keys';

export interface SelectionItem {
  readonly documentUid: DocumentUid;
  readonly step: ComparisonStepId;
}

export interface SelectionEstimate {
  readonly item: SelectionItem;
  /** The estimate the reader sees, or `null` when none exists for this step yet. */
  readonly estimate: ComparisonAiEstimate | null;
  /** Why there is none: the sentence of the refusal, or `''` for a step that has no model call. */
  readonly why: string;
}

async function one(projectUid: ProjectUid, item: SelectionItem): Promise<SelectionEstimate> {
  try {
    if (item.step === 'ai_pairs') {
      const estimate = (await estimateComparisonAiPairCheck({ path: { project_uid: projectUid, document_uid: item.documentUid } })).data;
      return { item, estimate, why: '' };
    }
    if (item.step === 'ai_changes') {
      const page = (await listComparisonSeries({ path: { project_uid: projectUid, document_uid: item.documentUid }, query: { limit: 1 } })).data;
      const series = latestSeries(page.items);
      if (series === null) return { item, estimate: null, why: 'Сравнение соседних версий ещё не посчитано: оценки пока нет.' };
      const estimate = (await estimateComparisonAiSheetChanges({ path: { comparison_series_id: series.series_id } })).data;
      return { item, estimate, why: '' };
    }
    if (item.step === 'report') return { item, estimate: null, why: 'Оценка отчёта появится, когда будет готова сводка.' };
    return { item, estimate: null, why: '' };
  } catch (error) {
    return { item, estimate: null, why: comparisonFailure(error).detail };
  }
}

export function useSelectionEstimates(projectUid: ProjectUid, items: readonly SelectionItem[], enabled: boolean) {
  const key = items.map((item) => `${item.documentUid}:${item.step}`).join(',');
  return useQuery<SelectionEstimate[]>({
    queryKey: [...COMPARISON_KEYS.estimate(`selection|${projectUid}`), key],
    queryFn: async () => {
      const out: SelectionEstimate[] = [];
      for (const item of items) out.push(await one(projectUid, item));
      return out;
    },
    enabled: enabled && items.length > 0,
    staleTime: 0,
    gcTime: 0,
    retry: false,
  });
}
