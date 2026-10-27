'use client';

/**
 * The administrator's commands on a preset (`ANALYSIS-PRESETS-01`): save, revise, archive.
 *
 * Each takes the idempotency key its caller minted for the intent and reuses it on an explicit
 * repeat; `retry: false`, so nothing here repeats a write on its own. Every command refreshes the
 * one list the settings screen and the start control read; none of them changes a number any other
 * screen shows. The server checks the role again on every write.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { AnalysisPreset, ExecutorConnectionId, PresetId } from '@/shared/api';
import { archiveAnalysisPreset, createAnalysisPreset, reviseAnalysisPreset } from '@/shared/api';
import { ANALYSIS_PRESETS_KEY } from '@/entities/analysis-preset';

export interface PresetSettings {
  readonly name: string;
  readonly executorConnectionId: ExecutorConnectionId;
}

function useRefreshPresets() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: ANALYSIS_PRESETS_KEY });
  };
}

export function useCreateAnalysisPreset() {
  const refresh = useRefreshPresets();
  return useMutation<AnalysisPreset, unknown, PresetSettings & { idempotencyKey: string }>({
    mutationFn: async ({ name, executorConnectionId, idempotencyKey }) =>
      (await createAnalysisPreset({
        body: { name, executor_connection_id: executorConnectionId },
        idempotencyKey,
      })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useReviseAnalysisPreset() {
  const refresh = useRefreshPresets();
  return useMutation<AnalysisPreset, unknown, PresetSettings & { presetId: PresetId; idempotencyKey: string }>({
    mutationFn: async ({ presetId, name, executorConnectionId, idempotencyKey }) =>
      (await reviseAnalysisPreset({
        path: { preset_id: presetId },
        body: { name, executor_connection_id: executorConnectionId },
        idempotencyKey,
      })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useArchiveAnalysisPreset() {
  const refresh = useRefreshPresets();
  return useMutation<AnalysisPreset, unknown, { presetId: PresetId; idempotencyKey: string }>({
    mutationFn: async ({ presetId, idempotencyKey }) =>
      (await archiveAnalysisPreset({ path: { preset_id: presetId }, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}
