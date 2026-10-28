'use client';

/**
 * «В архив» (`ANALYSIS-PRESETS-01`): retire a preset for good. One-way — nothing follows an archive,
 * and the name is free again — so the button asks once before it sends. A run that used the preset
 * keeps pointing at the version it used.
 */

import { useState } from 'react';

import type { AnalysisPreset } from '@/shared/api';
import { presetFailure } from '@/entities/analysis-preset';
import { LoadingState } from '@/shared/ui';

import { useCommandKey } from '../model/use-command-key';
import { useArchiveAnalysisPreset } from '../model/use-manage-analysis-preset';
import { PresetCommandFailure } from './preset-failure';

export function ArchivePresetControl({ preset }: { readonly preset: AnalysisPreset }) {
  const [asking, setAsking] = useState(false);
  const key = useCommandKey();
  const archive = useArchiveAnalysisPreset();
  const failure = archive.error === null || archive.error === undefined ? null : presetFailure(archive.error, true);

  if (!asking) {
    return (
      <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setAsking(true)}>
        В архив
      </button>
    );
  }
  return (
    <div data-preset-archive="asking">
      <p className="am-note" role="status">
        Пресет «{preset.name}» уйдёт в архив насовсем: выбрать его для прогона будет нельзя, а название освободится.
        Прогоны, которые его использовали, останутся как были.
      </p>
      <button
        type="button"
        className="am-button am-button--small"
        disabled={archive.isPending}
        onClick={() =>
          archive.mutate(
            { presetId: preset.preset_id, idempotencyKey: key.keyFor(preset.preset_id) },
            { onSuccess: () => key.release() },
          )
        }
      >
        Убрать в архив
      </button>{' '}
      <button
        type="button"
        className="am-button am-button--quiet am-button--small"
        disabled={archive.isPending}
        onClick={() => {
          setAsking(false);
          archive.reset();
        }}
      >
        Не убирать
      </button>
      {archive.isPending ? <LoadingState what="архивирование пресета" /> : null}
      {failure === null ? null : <PresetCommandFailure failure={failure} />}
    </div>
  );
}
