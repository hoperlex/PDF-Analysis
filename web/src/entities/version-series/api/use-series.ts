'use client';

/**
 * The series of adjacent transitions: the newest series of a document set, its transitions, the sheet pairs
 * of one transition, one pair, and the commands (`listComparisonSeries`, `getComparisonSeries`,
 * `listComparisonSheetPairs`, `getComparisonSheetPair`, `startComparisonSeries`, the pause, resume, cancel and
 * finish of a series).
 *
 * The series is polled every 2 s while it is queued or running (`version-comparison.js:828`).
 * A command on a series needs the series' identity, and the overview's step carries none, so the commands
 * below find it the way a reader would: the newest series of the document set, read when the button is
 * pressed. «Заново» is `startComparisonSeries` with `restart` (CMP-SEAL-C1 decision 8).
 */

import { useQuery } from '@tanstack/react-query';

import type {
  ComparisonSeries,
  ComparisonSeriesId,
  ComparisonSheetPair,
  ComparisonSheetPairId,
  ComparisonTransitionId,
  DocumentUid,
  ProjectUid,
} from '@/shared/api';
import {
  cancelComparisonSeries,
  finishComparisonSeries,
  getComparisonSeries,
  getComparisonSheetPair,
  listComparisonSeries,
  listComparisonSheetPairs,
  pauseComparisonSeries,
  resumeComparisonSeries,
  startComparisonSeries,
} from '@/shared/api';

import { latestSeries } from '../model/series-words';

import { COMPARISON_KEYS } from './keys';
import { useKeyedCommand } from './use-keyed-command';

export const SERIES_POLL_MS = 2_000;
/** Sheet pairs are read in pages of this size, and at most this many pages per transition. */
export const PAIR_PAGE_LIMIT = 200;
export const PAIR_PAGE_CAP = 10;

function live(series: ComparisonSeries | undefined): boolean {
  return series !== undefined && (series.state === 'queued' || series.state === 'running');
}

/** The newest series of the document set (`listComparisonSeries` answers newest first). */
export function useLatestSeries(projectUid: ProjectUid, documentUid: DocumentUid | null) {
  return useQuery<ComparisonSeries | null>({
    queryKey: COMPARISON_KEYS.seriesList(projectUid, documentUid ?? 'none'),
    queryFn: async () => {
      const page = (
        await listComparisonSeries({
          path: { project_uid: projectUid, document_uid: documentUid as DocumentUid },
          query: { limit: 1 },
        })
      ).data;
      const newest = latestSeries(page.items);
      if (newest === null) return null;
      // The list omits the transitions; the screen needs them, so the newest is read whole.
      return (await getComparisonSeries({ path: { comparison_series_id: newest.series_id } })).data;
    },
    enabled: documentUid !== null,
    refetchInterval: (query) => (live(query.state.data ?? undefined) ? SERIES_POLL_MS : false),
    retry: false,
  });
}

/** Every sheet pair of a transition, in the order of the matrix rows (pages followed up to a cap). */
export function useSheetPairs(transitionId: ComparisonTransitionId | null) {
  return useQuery<ComparisonSheetPair[]>({
    queryKey: COMPARISON_KEYS.pairs(transitionId ?? 'none'),
    queryFn: async () => {
      const pairs: ComparisonSheetPair[] = [];
      let cursor: string | undefined;
      for (let page = 0; page < PAIR_PAGE_CAP; page += 1) {
        const answer = (
          await listComparisonSheetPairs({
            path: { comparison_transition_id: transitionId as ComparisonTransitionId },
            query: { limit: PAIR_PAGE_LIMIT, ...(cursor === undefined ? {} : { cursor }) },
          })
        ).data;
        pairs.push(...answer.items);
        if (answer.page.next_cursor === null) break;
        cursor = answer.page.next_cursor;
      }
      return pairs;
    },
    enabled: transitionId !== null,
    retry: false,
  });
}

/** One pair with its raw evidence, for the viewer. */
export function useSheetPair(pairId: ComparisonSheetPairId | null) {
  return useQuery<ComparisonSheetPair>({
    queryKey: COMPARISON_KEYS.pair(pairId ?? 'none'),
    queryFn: async () => (await getComparisonSheetPair({ path: { comparison_sheet_pair_id: pairId as ComparisonSheetPairId } })).data,
    enabled: pairId !== null,
    retry: false,
  });
}

export interface StartSeriesCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  /** «Заново». */
  readonly restart: boolean;
  /** The revision of the version order the reader saw (`0` for none); `null` where the screen did not read the order. */
  readonly baseOrderRevisionNo: number | null;
}

/** «Запустить» and «Заново». */
export function useStartSeries() {
  return useKeyedCommand<StartSeriesCommand, ComparisonSeries>({
    signatureOf: (command) =>
      ['start', command.projectUid, command.documentUid, command.restart, command.baseOrderRevisionNo ?? ''].join('|'),
    send: async (command, idempotencyKey) =>
      (
        await startComparisonSeries({
          path: { project_uid: command.projectUid, document_uid: command.documentUid },
          body: {
            ...(command.restart ? { restart: true } : {}),
            ...(command.baseOrderRevisionNo === null ? {} : { base_order_revision_no: command.baseOrderRevisionNo }),
          },
          idempotencyKey,
        })
      ).data,
  });
}

export type SeriesAct = 'pause' | 'resume' | 'cancel' | 'finish';

export interface SeriesActCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly act: SeriesAct;
  /** The series the reader looked at; absent when the button sits in a table that does not hold it. */
  readonly seriesId?: ComparisonSeriesId;
}

async function seriesIdOf(command: SeriesActCommand): Promise<ComparisonSeriesId | null> {
  if (command.seriesId !== undefined) return command.seriesId;
  const page = (
    await listComparisonSeries({
      path: { project_uid: command.projectUid, document_uid: command.documentUid },
      query: { limit: 1 },
    })
  ).data;
  return latestSeries(page.items)?.series_id ?? null;
}

/** «Пауза», «Продолжить», «Отменить» and «Досчитать» on the newest series of a document set. */
export function useSeriesAct() {
  return useKeyedCommand<SeriesActCommand, ComparisonSeries | null>({
    signatureOf: (command) =>
      ['series', command.act, command.projectUid, command.documentUid, command.seriesId ?? ''].join('|'),
    send: async (command, idempotencyKey) => {
      const id = await seriesIdOf(command);
      if (id === null) return null;
      const input = { path: { comparison_series_id: id }, idempotencyKey } as const;
      switch (command.act) {
        case 'pause': return (await pauseComparisonSeries(input)).data;
        case 'resume': return (await resumeComparisonSeries(input)).data;
        case 'cancel': return (await cancelComparisonSeries(input)).data;
        case 'finish': return (await finishComparisonSeries(input)).data;
      }
    },
  });
}
