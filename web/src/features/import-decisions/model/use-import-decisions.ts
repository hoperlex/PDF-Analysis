'use client';

/**
 * Load the expert's decisions back from the run's own Excel workbook (`R-151d`, `importRunDecisions`).
 *
 * One file per intent: the key is minted for the chosen file and reused on a retry of that file, so a
 * double press or a lost answer replays the stored report instead of appending twice. Every changed
 * row is an ordinary decision event, so on success everything a decision moves is re-read: the run's
 * findings, each finding's detail and history, the decision journal and the dashboard's counts.
 */

import { useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { DecisionImportReport, RunId } from '@/shared/api';
import { importRunDecisions, newIdempotencyKey, queryKeys } from '@/shared/api';

export function useImportDecisions({ runId }: { readonly runId: RunId }) {
  const client = useQueryClient();
  const keys = useRef(new WeakMap<File, string>());
  return useMutation<DecisionImportReport, unknown, { readonly file: File }>({
    mutationFn: async ({ file }) => {
      const key = keys.current.get(file) ?? newIdempotencyKey();
      keys.current.set(file, key);
      return (await importRunDecisions({ path: { run_id: runId }, body: { file }, idempotencyKey: key })).data;
    },
    retry: false,
    onSuccess: (report) => {
      if (report.recorded === 0) return;
      void client.invalidateQueries({ queryKey: queryKeys.runs.findings(runId) });
      void client.invalidateQueries({ queryKey: queryKeys.findings.all() });
      void client.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    },
  });
}
