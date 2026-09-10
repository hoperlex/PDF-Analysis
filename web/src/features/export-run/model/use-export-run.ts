'use client';

/**
 * Download the CSV for one run.
 *
 * Synchronous by contract: nothing is created, there is no export identity and there is
 * nothing to poll, so this is a mutation only in the sense that the user asked for it — it
 * holds no polling state and creates no cache entry.
 *
 * The run identity is the one on the route. `exportRunCsv` takes `run_id` and no other
 * parameter, so the project and version this file covers are the ones that run belongs to
 * and cannot be chosen separately or mismatched — they arrive in the file's own
 * `project_uid` and `version_uid` columns.
 *
 * Exportability is `isExportableRunState`, which encodes `OD-11`: `published` and `partial`
 * export, and a `partial` run exports with its degradation visible in the `run_state`
 * column rather than being refused. This only decides whether the control is offered; the
 * server remains the authority and answers `state_transition_not_allowed` if asked anyway.
 */

import { useMutation } from '@tanstack/react-query';

import type { RunId } from '@/shared/api';
import { csvFileName, exportRunCsv } from '@/shared/api';

import type { DownloadSink } from './download-sink';
import { browserDownloadSink, deliverDownload } from './download-sink';

export interface ExportRunArgs {
  readonly runId: RunId;
  /** Injected by tests. Production uses the browser sink. */
  readonly sink?: DownloadSink;
}

export interface ExportRunApi {
  readonly download: () => void;
  readonly isPending: boolean;
  readonly error: unknown;
  readonly correlationId: string | null;
  readonly lastFileName: string | null;
  readonly reset: () => void;
}

export function useExportRun({ runId, sink }: ExportRunArgs): ExportRunApi {
  const mutation = useMutation({
    mutationFn: async () => {
      const response = await exportRunCsv({ path: { run_id: runId } });
      const fileName = csvFileName(runId);
      deliverDownload(sink ?? browserDownloadSink(), response.data, fileName);
      return { fileName, correlationId: response.correlationId };
    },
  });

  return {
    download: () => {
      mutation.mutate();
    },
    isPending: mutation.isPending,
    error: mutation.error,
    correlationId: mutation.data?.correlationId ?? null,
    lastFileName: mutation.data?.fileName ?? null,
    reset: () => {
      mutation.reset();
    },
  };
}
