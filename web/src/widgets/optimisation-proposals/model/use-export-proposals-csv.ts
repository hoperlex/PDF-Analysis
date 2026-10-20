'use client';

/**
 * Download one pass's proposals as CSV (`W60-OPT-PROPOSALS-01`).
 *
 * The CSV's siblings' rules (`features/export-run`): synchronous by contract, nothing is
 * created, nothing is polled, and the file's bytes — the columns, the formula escaping, the
 * empty cell for an absent saving — are the server's alone; the browser never builds a CSV
 * from cached proposals. Plain component state rather than a query-cache mutation: a download
 * touches no cached answer, so there is nothing to invalidate.
 */

import { useCallback, useRef, useState } from 'react';

import type { OptimisationPassId } from '@/shared/api';
import { exportOptimisationProposalsCsv } from '@/shared/api';
import type { DownloadSink } from '@/features/export-run';
import { browserDownloadSink, deliverDownload } from '@/features/export-run';
import { proposalsCsvFileName } from '@/entities/optimisation-proposal';

interface Outcome {
  readonly isPending: boolean;
  readonly error: unknown;
  readonly correlationId: string | null;
  readonly lastFileName: string | null;
}

const IDLE: Outcome = { isPending: false, error: null, correlationId: null, lastFileName: null };

export interface ExportProposalsCsvApi extends Outcome {
  readonly download: () => void;
  readonly reset: () => void;
}

export interface ExportProposalsCsvArgs {
  readonly passId: OptimisationPassId;
  /** Injected by tests. Production uses the browser sink. */
  readonly sink?: DownloadSink;
}

export function useExportProposalsCsv({ passId, sink }: ExportProposalsCsvArgs): ExportProposalsCsvApi {
  const [outcome, setOutcome] = useState<Outcome>(IDLE);
  // One download at a time; an answer to a superseded request is dropped.
  const sequence = useRef(0);

  const download = useCallback(() => {
    sequence.current += 1;
    const mine = sequence.current;
    setOutcome((current) => ({ ...current, isPending: true, error: null }));
    void (async () => {
      try {
        const response = await exportOptimisationProposalsCsv({ path: { optimisation_pass_id: passId } });
        const fileName = proposalsCsvFileName(passId);
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
