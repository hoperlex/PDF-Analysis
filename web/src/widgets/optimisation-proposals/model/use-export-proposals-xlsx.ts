'use client';

/**
 * Download one pass's proposals as the workbook an expert edits and loads back (`UI-B-15`).
 *
 * The same rules as the CSV beside it (`use-export-proposals-csv`): synchronous by contract, nothing is created or
 * polled, and the file's bytes -- the columns, the identity first, the decision in force -- are the server's alone; the
 * browser never builds a workbook from cached proposals. Plain component state rather than a query-cache mutation.
 */

import { useCallback, useRef, useState } from 'react';

import type { OptimisationPassId } from '@/shared/api';
import { exportOptimisationProposalsXlsx } from '@/shared/api';
import type { DownloadSink } from '@/features/export-run';
import { browserDownloadSink, deliverDownload } from '@/features/export-run';
import { proposalsXlsxFileName } from '@/entities/optimisation-proposal';

interface Outcome {
  readonly isPending: boolean;
  readonly error: unknown;
  readonly correlationId: string | null;
  readonly lastFileName: string | null;
}

const IDLE: Outcome = { isPending: false, error: null, correlationId: null, lastFileName: null };

export interface ExportProposalsXlsxApi extends Outcome {
  readonly download: () => void;
  readonly reset: () => void;
}

export interface ExportProposalsXlsxArgs {
  readonly passId: OptimisationPassId;
  /** Injected by tests. Production uses the browser sink. */
  readonly sink?: DownloadSink;
}

export function useExportProposalsXlsx({ passId, sink }: ExportProposalsXlsxArgs): ExportProposalsXlsxApi {
  const [outcome, setOutcome] = useState<Outcome>(IDLE);
  const sequence = useRef(0);

  const download = useCallback(() => {
    sequence.current += 1;
    const mine = sequence.current;
    setOutcome((current) => ({ ...current, isPending: true, error: null }));
    void (async () => {
      try {
        const response = await exportOptimisationProposalsXlsx({ path: { optimisation_pass_id: passId } });
        const fileName = proposalsXlsxFileName(passId);
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
  }, [passId, sink]);

  const reset = useCallback(() => {
    sequence.current += 1;
    setOutcome(IDLE);
  }, []);

  return { download, reset, ...outcome };
}
