'use client';

/**
 * The reads and commands of a comparison upload (`createComparisonUpload`, `getComparisonUpload`,
 * `getComparisonUploadProposal`, `listComparisonUploads`, `confirmComparisonUploadSet`, `excludeComparisonUploadSet`,
 * `retryComparisonUploadSet`, `pauseComparisonUpload`, `resumeComparisonUpload`, `cancelComparisonUpload`).
 *
 * An upload is polled every 2 s while it is moving: the proposal appears when every file is read, and a confirmed set
 * goes on to be admitted and prepared on the server. Each command is one intent with one key
 * (`useKeyedCommand`). The parts and completions are sent by the transfer (`model/transfer.ts`), not from here.
 */

import { useQuery } from '@tanstack/react-query';

import type {
  ComparisonProposalSet,
  ComparisonUpload,
  ComparisonUploadId,
  ComparisonUploadPage,
  ComparisonUploadProposal,
  ComparisonUploadSetId,
  ConfirmComparisonUploadSetRequest,
  CreateComparisonUploadRequest,
  ProjectUid,
} from '@/shared/api';
import {
  cancelComparisonUpload,
  confirmComparisonUploadSet,
  createComparisonUpload,
  excludeComparisonUploadSet,
  getComparisonUpload,
  getComparisonUploadProposal,
  listComparisonUploads,
  pauseComparisonUpload,
  resumeComparisonUpload,
  retryComparisonUploadSet,
} from '@/shared/api';
import { COMPARISON_KEYS, uploadIsActive, useKeyedCommand } from '@/entities/version-series';

export const UPLOAD_POLL_MS = 2_000;

function moving(upload: ComparisonUpload | undefined): boolean {
  return upload !== undefined && (upload.state === 'uploading' || upload.state === 'processing');
}

export function useUpload(uploadId: ComparisonUploadId | null) {
  return useQuery<ComparisonUpload>({
    queryKey: [...COMPARISON_KEYS.uploads('one'), uploadId ?? 'none'],
    queryFn: async () => (await getComparisonUpload({ path: { comparison_upload_id: uploadId as ComparisonUploadId } })).data,
    enabled: uploadId !== null,
    refetchInterval: (query) => (moving(query.state.data) ? UPLOAD_POLL_MS : false),
    retry: false,
  });
}

/** The proposal; read while the upload is still being read and once it is proposed. */
export function useProposal(uploadId: ComparisonUploadId | null, upload: ComparisonUpload | undefined) {
  return useQuery<ComparisonUploadProposal>({
    queryKey: [...COMPARISON_KEYS.uploads('proposal'), uploadId ?? 'none'],
    queryFn: async () => (await getComparisonUploadProposal({ path: { comparison_upload_id: uploadId as ComparisonUploadId } })).data,
    enabled: uploadId !== null && upload !== undefined,
    refetchInterval: () => (upload === undefined || upload.state === 'completed' || upload.state === 'cancelled' ? false : UPLOAD_POLL_MS),
    retry: false,
  });
}

/** The unfinished uploads of the project: what a reader can open again. */
export function useUnfinishedUploads(projectUid: ProjectUid) {
  return useQuery<ComparisonUpload[]>({
    queryKey: COMPARISON_KEYS.uploads(projectUid),
    queryFn: async () => {
      const page: ComparisonUploadPage = (await listComparisonUploads({ path: { project_uid: projectUid }, query: { limit: 50 } })).data;
      return page.items.filter((upload) => uploadIsActive(upload.state));
    },
    retry: false,
  });
}

export interface CreateUploadCommand {
  readonly projectUid: ProjectUid;
  readonly request: CreateComparisonUploadRequest;
}

export function useCreateUpload() {
  return useKeyedCommand<CreateUploadCommand, ComparisonUpload>({
    signatureOf: (command) =>
      ['upload', command.projectUid, command.request.compare_after_preparation ?? false, JSON.stringify(command.request.files)].join('|'),
    send: async (command, idempotencyKey) =>
      (await createComparisonUpload({ path: { project_uid: command.projectUid }, body: command.request, idempotencyKey })).data,
  });
}

export interface SetCommand {
  readonly uploadId: ComparisonUploadId;
  readonly setId: ComparisonUploadSetId;
}

export interface ConfirmSetCommand extends SetCommand {
  readonly request: ConfirmComparisonUploadSetRequest;
}

export function useConfirmSet() {
  return useKeyedCommand<ConfirmSetCommand, ComparisonProposalSet>({
    signatureOf: (command) => ['confirm', command.uploadId, command.setId, JSON.stringify(command.request)].join('|'),
    send: async (command, idempotencyKey) =>
      (
        await confirmComparisonUploadSet({
          path: { comparison_upload_id: command.uploadId, comparison_upload_set_id: command.setId },
          body: command.request,
          idempotencyKey,
        })
      ).data,
  });
}

export function useExcludeSet() {
  return useKeyedCommand<SetCommand, ComparisonProposalSet>({
    signatureOf: (command) => ['exclude', command.uploadId, command.setId].join('|'),
    send: async (command, idempotencyKey) =>
      (
        await excludeComparisonUploadSet({
          path: { comparison_upload_id: command.uploadId, comparison_upload_set_id: command.setId },
          idempotencyKey,
        })
      ).data,
  });
}

export function useRetrySet() {
  return useKeyedCommand<SetCommand, ComparisonProposalSet>({
    signatureOf: (command) => ['retry', command.uploadId, command.setId].join('|'),
    send: async (command, idempotencyKey) =>
      (
        await retryComparisonUploadSet({
          path: { comparison_upload_id: command.uploadId, comparison_upload_set_id: command.setId },
          idempotencyKey,
        })
      ).data,
  });
}

export type UploadAct = 'pause' | 'resume' | 'cancel';

export interface UploadActCommand {
  readonly uploadId: ComparisonUploadId;
  readonly act: UploadAct;
}

export function useUploadAct() {
  return useKeyedCommand<UploadActCommand, ComparisonUpload>({
    signatureOf: (command) => ['upload-act', command.act, command.uploadId].join('|'),
    send: async (command, idempotencyKey) => {
      const input = { path: { comparison_upload_id: command.uploadId }, idempotencyKey } as const;
      switch (command.act) {
        case 'pause': return (await pauseComparisonUpload(input)).data;
        case 'resume': return (await resumeComparisonUpload(input)).data;
        case 'cancel': return (await cancelComparisonUpload(input)).data;
      }
    },
  });
}
