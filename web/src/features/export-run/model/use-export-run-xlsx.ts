'use client';

/**
 * Download the run's Excel workbook (`W57B-NORMS-CATALOGUE-XLSX-01`).
 *
 * The CSV's sibling, by the same rules (`use-export-run.ts`): synchronous by contract,
 * nothing is created, nothing to poll, and the run identity is the route's. The server is
 * the authority on whether the run exports and on the workbook's sources: it answers
 * `state_transition_not_allowed` for a run that publishes no result,
 * `storage_integrity_error` for a version without verifiable sheet labels and
 * `required_norm_unavailable` for citations that do not verify, and the panel shows the
 * refusal rather than an empty file.
 *
 * Plain component state rather than a query-cache mutation: a download touches no cached
 * answer, so there is nothing to invalidate, and the export panel that owns this button is
 * rendered on screens (and in the guards' static renders) without a query client.
 */

import { useCallback, useRef, useState } from 'react';

import { exportRunXlsx, xlsxFileName } from '@/shared/api';

import { browserDownloadSink, deliverDownload } from './download-sink';
import type { ExportRunApi, ExportRunArgs } from './use-export-run';

interface Outcome {
  readonly isPending: boolean;
  readonly error: unknown;
  readonly correlationId: string | null;
  readonly lastFileName: string | null;
}

const IDLE: Outcome = { isPending: false, error: null, correlationId: null, lastFileName: null };

export function useExportRunXlsx({ runId, sink }: ExportRunArgs): ExportRunApi {
  const [outcome, setOutcome] = useState<Outcome>(IDLE);
  // One download at a time; an answer to a superseded request is dropped.
  const sequence = useRef(0);

  const download = useCallback(() => {
    sequence.current += 1;
    const mine = sequence.current;
    setOutcome((current) => ({ ...current, isPending: true, error: null }));
    void (async () => {
      try {
        const response = await exportRunXlsx({ path: { run_id: runId } });
        const fileName = xlsxFileName(runId);
        deliverDownload(sink ?? browserDownloadSink(), response.data, fileName);
        if (mine === sequence.current) {
          setOutcome({ isPending: false, error: null, correlationId: response.correlationId, lastFileName: fileName });
        }
      } catch (error) {
        if (mine === sequence.current) {
          setOutcome({ isPending: false, error, correlationId: null, lastFileName: null });
        }
      }
    })();
  }, [runId, sink]);

  const reset = useCallback(() => {
    sequence.current += 1;
    setOutcome(IDLE);
  }, []);

  return { download, ...outcome, reset };
}
