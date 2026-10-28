'use client';

/**
 * «Пресеты запуска» in «Настройки анализа» (`ANALYSIS-PRESETS-01`, `R-146av`): the named, saved
 * choices of how a run starts.
 *
 * A run start takes one setting per run — the executor — so a preset is a name and an executor. The
 * screen says so, and says what is not in it: the cost limit of a run is one setting of the stand
 * for every run, and is not chosen per run.
 *
 * Any role reads the list (the people who start runs choose from it); only an administrator is shown
 * the controls, and the server checks every write. A change is a new version of the preset: the
 * earlier version is kept, and a run says which version it used. An archived preset is listed apart
 * and cannot be chosen again.
 */

import type { AnalysisPreset, Role } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import {
  PRESET_STATE_LABELS,
  executorPhrase,
  presetBlocker,
  presetExecutor,
  presetFailure,
  useAnalysisPresets,
} from '@/entities/analysis-preset';
import { canExecute } from '@/entities/execution';
import {
  executorChoices,
  useExecutorConnectionDetails,
  useExecutorConnections,
} from '@/entities/executor-connection';
import type { ExecutorChoice } from '@/entities/executor-connection';
import { ArchivePresetControl, PresetForm } from '@/features/manage-analysis-preset';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

export interface AnalysisPresetsProps {
  readonly roles: readonly Role[];
}

function PresetCard({
  preset,
  choices,
  canManage,
}: {
  readonly preset: AnalysisPreset;
  readonly choices: readonly ExecutorChoice[];
  readonly canManage: boolean;
}) {
  const blocker = presetBlocker(preset, choices);
  const archived = preset.state === 'archived';
  return (
    <li className="am-state" style={{ marginBottom: '0.5rem' }} data-preset-state={preset.state}>
      <p className="am-state__title">
        <strong data-preset-name>{preset.name}</strong> · {PRESET_STATE_LABELS[preset.state]} · версия{' '}
        {preset.revision_no}
      </p>
      <div className="am-state__detail">
        <p data-preset-executor>Исполнитель: {executorPhrase(presetExecutor(preset, choices))}</p>
        {archived || blocker === null ? null : (
          <p data-preset-blocker role="status">
            Сейчас этим пресетом прогон не запустить: {blocker}.
          </p>
        )}
        <p>
          {archived ? 'Убран в архив' : 'Изменён'} {formatInstant(preset.revised_at)}
        </p>
        {canManage && !archived ? (
          <>
            <details data-preset-revise>
              <summary>Изменить</summary>
              <PresetForm preset={preset} choices={choices} />
            </details>
            <ArchivePresetControl preset={preset} />
          </>
        ) : null}
      </div>
    </li>
  );
}

export function AnalysisPresets({ roles }: AnalysisPresetsProps) {
  const presets = useAnalysisPresets();
  const list = useExecutorConnections();
  const items = list.data?.items ?? [];
  const settings = useExecutorConnectionDetails(
    items.filter((item) => item.archived_at === undefined).map((item) => item.connection_id),
  );
  const canManage = canExecute(roles, 'connections');
  const choices = executorChoices(items, settings.details);

  const body = (() => {
    if (presets.isPending) return <LoadingState what="пресеты" />;
    if (presets.isError) {
      const failure = presetFailure(presets.error, false);
      return (
        <div data-analysis-presets-failure={failure.kind}>
          <ErrorState
            title="Пресеты не прочитаны"
            detail={failure.detail}
            correlationId={failure.correlationId}
            onRetry={() => void presets.refetch()}
          />
        </div>
      );
    }
    const all = presets.data.items;
    const active = all.filter((preset) => preset.state === 'active');
    const archived = all.filter((preset) => preset.state === 'archived');
    return (
      <>
        {active.length === 0 ? (
          <EmptyState
            title="Пресетов нет"
            detail={
              canManage
                ? 'Сохраните первый пресет ниже: название и исполнитель.'
                : 'Администратор ещё не сохранил ни одного пресета.'
            }
          />
        ) : (
          <ol aria-label="Пресеты" style={{ listStyle: 'none', margin: 0, padding: 0 }} data-preset-list>
            {active.map((preset) => (
              <PresetCard key={preset.preset_id} preset={preset} choices={choices} canManage={canManage} />
            ))}
          </ol>
        )}
        {archived.length === 0 ? null : (
          <details data-preset-archive-list>
            <summary>Архив пресетов ({archived.length})</summary>
            <ol aria-label="Пресеты в архиве" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {archived.map((preset) => (
                <PresetCard key={preset.preset_id} preset={preset} choices={choices} canManage={false} />
              ))}
            </ol>
          </details>
        )}
        {canManage ? (
          <details className="am-section" open={active.length === 0} data-preset-create>
            <summary>Сохранить пресет</summary>
            <PresetForm choices={choices} />
          </details>
        ) : null}
      </>
    );
  })();

  return (
    <section className="am-section" aria-label="Пресеты запуска" data-analysis-presets>
      <h2>Пресеты запуска</h2>
      <p className="am-note">
        Пресет — сохранённый выбор того, как запускается прогон: название и исполнитель. Эксперт выбирает пресет при
        запуске вместо того, чтобы выбирать исполнителя вручную; прогон идёт на исполнителе пресета и помнит, какой
        версией пресета он запущен. Предел стоимости прогона задаётся на стенде один для всех прогонов и в пресет не
        входит.
      </p>
      <p>
        <button className="am-button am-button--quiet" type="button" onClick={() => void presets.refetch()}>
          Обновить пресеты
        </button>
      </p>
      {body}
    </section>
  );
}
