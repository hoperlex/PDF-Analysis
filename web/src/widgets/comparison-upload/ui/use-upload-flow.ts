'use client';

/**
 * The life of one comparison upload in the browser: pick the files, hash them, declare them, send them in parts,
 * stop and continue, and watch the server read them into a proposal.
 *
 * What is held here is what the server cannot hold: the bytes. Everything else is the server's — the batch, each
 * file's state and how many parts it already has, the proposal — and is read back (`useUpload`, `useProposal`). That is
 * what makes the transfer resumable: «Остановить загрузку» aborts the request in flight and keeps the staged parts,
 * «Продолжить загрузку» reads the batch again and sends from the next part of each file, and a reader who reloaded the
 * page picks the same files again, which are matched to the declared ones by SHA-256 and size (`matchFiles`), never by name.
 */

import { useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { ComparisonUpload, ComparisonUploadId, ProjectUid } from '@/shared/api';
import {
  ApiError,
  TransportError,
  completeComparisonUploadFile,
  getComparisonUpload,
  newIdempotencyKey,
  uploadComparisonUploadPart,
} from '@/shared/api';
import type { ComparisonFailure } from '@/entities/version-series';
import { COMPARISON_KEYS, comparisonFailure } from '@/entities/version-series';

import { useCreateUpload, useProposal, useUpload } from '../api/use-upload';
import type { FolderMode, PickedFile, PrecheckProblem } from '../model/files';
import { declaredName, pickFiles, precheck } from '../model/files';
import { sha256Hex } from '../model/hash';
import { matchFiles } from '../model/matching';
import type { TransferFile, TransferPorts } from '../model/transfer';
import { KeyBook, needsTransfer, transferFiles } from '../model/transfer';

export type FlowPhase = 'pick' | 'hashing' | 'sending' | 'stopped' | 'watching';

export interface Progress {
  readonly done: number;
  readonly total: number;
}

/** A refusal that ends the whole batch rather than one file: the batch cannot take a part in its state. */
function classifyTransfer(error: unknown): 'retry' | 'file' | 'batch' {
  if (error instanceof ApiError) {
    if (error.errorCode === 'conflict' && error.details['conflict_reason'] === 'comparison_upload_state') return 'batch';
    return error.retryable ? 'retry' : 'file';
  }
  if (error instanceof TransportError) return error.retryable ? 'retry' : 'file';
  return 'file';
}

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener('abort', () => {
      clearTimeout(timer);
      resolve();
    }, { once: true });
  });
}

export function useUploadFlow(projectUid: ProjectUid, initialUploadId: ComparisonUploadId | null = null) {
  const client = useQueryClient();
  const create = useCreateUpload();
  const [picked, setPicked] = useState<readonly PickedFile[]>([]);
  const [skipped, setSkipped] = useState(0);
  const [compare, setCompare] = useState(false);
  const [phase, setPhase] = useState<FlowPhase>(initialUploadId === null ? 'pick' : 'watching');
  const [hashing, setHashing] = useState<Progress | null>(null);
  const [uploadId, setUploadId] = useState<ComparisonUploadId | null>(initialUploadId);
  const [progress, setProgress] = useState<ReadonlyMap<string, Progress>>(new Map());
  const [fileFailures, setFileFailures] = useState<ReadonlyMap<string, ComparisonFailure>>(new Map());
  const [missing, setMissing] = useState<readonly string[]>([]);
  const [failure, setFailure] = useState<ComparisonFailure | null>(null);
  const [problem, setProblem] = useState<PrecheckProblem | null>(null);

  const hashes = useRef(new Map<File, string>());
  const local = useRef(new Map<string, Blob>());
  const keys = useRef(new KeyBook(newIdempotencyKey));
  const controller = useRef<AbortController | null>(null);

  const upload = useUpload(uploadId);
  const proposal = useProposal(uploadId, upload.data);

  const hashAll = async (files: readonly PickedFile[]): Promise<void> => {
    setPhase('hashing');
    for (let index = 0; index < files.length; index += 1) {
      const entry = files[index] as PickedFile;
      setHashing({ done: index, total: files.length });
      if (!hashes.current.has(entry.file)) hashes.current.set(entry.file, await sha256Hex(entry.file));
    }
    setHashing(null);
  };

  const refresh = async (id: ComparisonUploadId): Promise<ComparisonUpload> => {
    const fresh = (await getComparisonUpload({ path: { comparison_upload_id: id } })).data;
    client.setQueryData([...COMPARISON_KEYS.uploads('one'), id], fresh);
    return fresh;
  };

  const run = async (id: ComparisonUploadId, current: ComparisonUpload): Promise<void> => {
    const files: TransferFile[] = [];
    const lacking: string[] = [];
    for (const file of current.files ?? []) {
      const probe = { state: file.state, failureReason: file.failure_reason };
      if (!needsTransfer(probe)) continue;
      const blob = local.current.get(file.file_id);
      if (blob === undefined) lacking.push(file.file_id);
      else files.push({ fileId: file.file_id, sizeBytes: file.size_bytes, state: file.state, partsStaged: file.parts_staged, failureReason: file.failure_reason, blob });
    }
    setMissing(lacking);
    if (files.length === 0) {
      setPhase(lacking.length > 0 ? 'stopped' : 'watching');
      return;
    }
    const abort = new AbortController();
    controller.current = abort;
    setPhase('sending');
    setFileFailures(new Map());
    const ports: TransferPorts = {
      putPart: async (fileId, partNumber, body, idempotencyKey, signal) => {
        await uploadComparisonUploadPart(
          { path: { comparison_upload_id: id, comparison_upload_file_id: fileId }, query: { part_number: partNumber }, body, idempotencyKey },
          { signal },
        );
      },
      complete: async (fileId, idempotencyKey, signal) => {
        await completeComparisonUploadFile(
          { path: { comparison_upload_id: id, comparison_upload_file_id: fileId }, idempotencyKey },
          { signal },
        );
      },
      mintKey: newIdempotencyKey,
      classify: classifyTransfer,
      sleep,
    };
    const outcome = await transferFiles(
      files,
      ports,
      {
        onProgress: (fileId, done, total) => setProgress((held) => new Map(held).set(fileId, { done, total })),
        onFileDone: () => void client.invalidateQueries({ queryKey: COMPARISON_KEYS.all }),
        onFileFailed: (fileId, error) => setFileFailures((held) => new Map(held).set(fileId, comparisonFailure(error))),
      },
      keys.current,
      abort.signal,
    );
    controller.current = null;
    void client.invalidateQueries({ queryKey: COMPARISON_KEYS.all });
    setPhase(outcome === 'stopped' ? 'stopped' : 'watching');
  };

  return {
    phase,
    picked,
    skipped,
    compare,
    hashing,
    uploadId,
    upload,
    proposal,
    progress,
    fileFailures,
    missing,
    failure,
    problem,
    creating: create.isPending,
    setCompare,
    add: (files: Iterable<File>, mode: FolderMode | 'files'): void => {
      const added = pickFiles(files, mode);
      setPicked((held) => [...held, ...added.files]);
      setSkipped((held) => held + added.skipped);
      setProblem(null);
    },
    removeGroup: (group: string): void => setPicked((held) => held.filter((entry) => entry.group !== group)),
    clear: (): void => {
      setPicked([]);
      setSkipped(0);
      setProblem(null);
    },
    /** Hash the picked files, declare them, and send them. */
    send: async (): Promise<void> => {
      const found = precheck(picked);
      setProblem(found);
      if (found !== null) return;
      setFailure(null);
      try {
        await hashAll(picked);
        const declarations = picked.map((entry) => ({
          display_name: declaredName(entry.path),
          size_bytes: entry.file.size,
          sha256: hashes.current.get(entry.file) as string,
        }));
        const created = await create.mutateAsync({
          projectUid,
          request: { files: declarations, ...(compare ? { compare_after_preparation: true } : {}) },
        });
        setUploadId(created.upload_id);
        client.setQueryData([...COMPARISON_KEYS.uploads('one'), created.upload_id], created);
        const matching = matchFiles(
          (created.files ?? []).map((file) => ({ fileId: file.file_id, sha256: file.sha256, sizeBytes: file.size_bytes, displayName: file.display_name })),
          picked.map((entry) => ({
            sha256: hashes.current.get(entry.file) as string,
            sizeBytes: entry.file.size,
            displayName: declaredName(entry.path),
            value: entry.file as Blob,
          })),
        );
        for (const match of matching.matched) local.current.set(match.fileId, match.value);
        await run(created.upload_id, created);
      } catch (error) {
        setFailure(comparisonFailure(error));
        setPhase('pick');
      }
    },
    stop: (): void => controller.current?.abort(),
    /** Read the batch again and send what it still lacks; files picked again after a reload are matched first. */
    continueSending: async (again: readonly PickedFile[] = []): Promise<void> => {
      if (uploadId === null) return;
      setFailure(null);
      try {
        const current = await refresh(uploadId);
        if (again.length > 0) {
          await hashAll(again);
          const matching = matchFiles(
            (current.files ?? []).map((file) => ({ fileId: file.file_id, sha256: file.sha256, sizeBytes: file.size_bytes, displayName: file.display_name })),
            again.map((entry) => ({
              sha256: hashes.current.get(entry.file) as string,
              sizeBytes: entry.file.size,
              displayName: declaredName(entry.path),
              value: entry.file as Blob,
            })),
          );
          for (const match of matching.matched) local.current.set(match.fileId, match.value);
        }
        await run(uploadId, current);
      } catch (error) {
        setFailure(comparisonFailure(error));
        setPhase('stopped');
      }
    },
    /** Open an unfinished upload again: the bytes are asked for only when a file still lacks parts. */
    attach: (id: ComparisonUploadId): void => {
      setUploadId(id);
      setFailure(null);
      setPhase('stopped');
    },
    forget: (): void => {
      setUploadId(null);
      setPhase('pick');
      setPicked([]);
      setProgress(new Map());
      setFileFailures(new Map());
      setMissing([]);
      local.current.clear();
    },
  };
}

export type UploadFlow = ReturnType<typeof useUploadFlow>;
