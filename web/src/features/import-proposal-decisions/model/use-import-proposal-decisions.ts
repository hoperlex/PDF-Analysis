'use client';

/**
 * Load the expert's decisions back from a pass's own workbook (`UI-B-15`, `importOptimisationProposalDecisions`).
 *
 * One file per intent: the key is minted for the chosen file and reused on a retry of that file, so a double press or a
 * lost answer replays the stored report instead of appending twice. Every changed row is an ordinary decision event, so on
 * success everything a decision moves is re-read: the pass's proposals and counts, each proposal's history and the
 * accepted lists of the sections. A decision touches no finding, so nothing under `findings` or the dashboard is.
 */

import { useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { OptimisationPassId, ProposalDecisionImportReport } from '@/shared/api';
import { importOptimisationProposalDecisions, newIdempotencyKey, queryKeys } from '@/shared/api';

export function useImportProposalDecisions({ passId }: { readonly passId: OptimisationPassId }) {
  const client = useQueryClient();
  const keys = useRef(new WeakMap<File, string>());
  return useMutation<ProposalDecisionImportReport, unknown, { readonly file: File }>({
    mutationFn: async ({ file }) => {
      const key = keys.current.get(file) ?? newIdempotencyKey();
      keys.current.set(file, key);
      return (
        await importOptimisationProposalDecisions({
          path: { optimisation_pass_id: passId },
          body: { file },
          idempotencyKey: key,
        })
      ).data;
    },
    retry: false,
    onSuccess: (report) => {
      if (report.recorded === 0) return;
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.proposalsOf(passId) });
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.allPasses() });
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.allAccepted() });
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.allProposalDecisions() });
    },
  });
}
