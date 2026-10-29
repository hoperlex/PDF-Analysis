'use client';

/**
 * The effective matrix of a document set, its edit history, and the commands that change it
 * (`getComparisonMatrix`, `listComparisonMatrixEdits`, `prepareComparisonMatrix`,
 * `applyComparisonMatrixEdits`, `undoComparisonMatrixEdit`).
 *
 * The matrix is polled every 1.5 s while it is being built (`version-comparison.js:785`). The two
 * edit commands carry the revision the caller saw; the draft that holds the edits and rebases on a
 * stale answer is `model/draft.ts`.
 */

import { useQuery } from '@tanstack/react-query';

import type {
  ApplyComparisonMatrixEditsRequest,
  ComparisonMatrix,
  ComparisonMatrixEditList,
  ComparisonMatrixPreparation,
  ComparisonMatrixRevision,
  DocumentUid,
  ProjectUid,
} from '@/shared/api';
import {
  applyComparisonMatrixEdits,
  getComparisonMatrix,
  listComparisonMatrixEdits,
  prepareComparisonMatrix,
  undoComparisonMatrixEdit,
} from '@/shared/api';

import { revisionKey } from '../model/draft';

import { COMPARISON_KEYS } from './keys';
import { useKeyedCommand } from './use-keyed-command';

export const MATRIX_BUILD_POLL_MS = 1_500;
/** The history is read in one page; a set with more edits shows the newest. */
export const EDIT_HISTORY_LIMIT = 200;

export function useComparisonMatrix(projectUid: ProjectUid, documentUid: DocumentUid | null) {
  return useQuery<ComparisonMatrix>({
    queryKey: COMPARISON_KEYS.matrix(projectUid, documentUid ?? 'none'),
    queryFn: async () =>
      (await getComparisonMatrix({ path: { project_uid: projectUid, document_uid: documentUid as DocumentUid } })).data,
    enabled: documentUid !== null,
    refetchInterval: (query) => (query.state.data?.state === 'building' ? MATRIX_BUILD_POLL_MS : false),
    retry: false,
  });
}

export function useComparisonEdits(projectUid: ProjectUid, documentUid: DocumentUid | null) {
  return useQuery<ComparisonMatrixEditList>({
    queryKey: COMPARISON_KEYS.edits(projectUid, documentUid ?? 'none'),
    queryFn: async () =>
      (
        await listComparisonMatrixEdits({
          path: { project_uid: projectUid, document_uid: documentUid as DocumentUid },
          query: { limit: EDIT_HISTORY_LIMIT },
        })
      ).data,
    enabled: documentUid !== null,
    retry: false,
  });
}

export interface PrepareCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
}

/** «Подготовить» and «Повторить»: the missing or failed profiles, then the build. */
export function usePrepareMatrix() {
  return useKeyedCommand<PrepareCommand, ComparisonMatrixPreparation>({
    signatureOf: (command) => ['prepare', command.projectUid, command.documentUid].join('|'),
    send: async (command, idempotencyKey) =>
      (
        await prepareComparisonMatrix({
          path: { project_uid: command.projectUid, document_uid: command.documentUid },
          idempotencyKey,
        })
      ).data,
  });
}

export interface ApplyEditsCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly request: ApplyComparisonMatrixEditsRequest;
}

/** The signature of a batch: the document, the revision it rests on and the edits, in order. */
export function applySignature(command: ApplyEditsCommand): string {
  return [
    'apply', command.projectUid, command.documentUid, revisionKey(command.request.base_revision),
    JSON.stringify(command.request.edits),
  ].join('|');
}

export function useApplyMatrixEdits() {
  return useKeyedCommand<ApplyEditsCommand, ComparisonMatrix>({
    signatureOf: applySignature,
    send: async (command, idempotencyKey) =>
      (
        await applyComparisonMatrixEdits({
          path: { project_uid: command.projectUid, document_uid: command.documentUid },
          body: command.request,
          idempotencyKey,
        })
      ).data,
  });
}

export interface UndoEditCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly baseRevision: ComparisonMatrixRevision;
}

export function useUndoMatrixEdit() {
  return useKeyedCommand<UndoEditCommand, ComparisonMatrix>({
    signatureOf: (command) =>
      ['undo', command.projectUid, command.documentUid, revisionKey(command.baseRevision)].join('|'),
    send: async (command, idempotencyKey) =>
      (
        await undoComparisonMatrixEdit({
          path: { project_uid: command.projectUid, document_uid: command.documentUid },
          body: { base_revision: command.baseRevision },
          idempotencyKey,
        })
      ).data,
  });
}
