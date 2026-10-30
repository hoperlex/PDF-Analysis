'use client';

/**
 * Start one run over one published version, on the executor the person chooses.
 *
 * `EXEC-PAR-WEB-01`: the control offers «Исполнитель» — «По умолчанию (маршрут)» or one of the
 * connections that can serve a run now (`./executor-select.tsx`). The choice goes out as
 * `executor_connection_id` and only when a connection is chosen; the default is the absence of
 * the field (`../model/start-run-intent.ts`). It is part of the intent: the same version on
 * another executor is another request, so the idempotency key is minted for the version *and* the
 * choice. A connection that stops being usable between choosing and starting refuses the start;
 * the choice stays on the page, the refusal is said as itself and carries a retry under the same
 * key (`./start-run-failure.tsx`). The control never picks another executor, or the route, after
 * a refusal — changing the choice is the person's act, and a changed choice clears the old
 * refusal, which was about the old one.
 *
 * The list of connections is read with the existing hooks of `entities/executor-connection`
 * (open to every role). It adds no polling of its own; when it cannot be read the select says so
 * and the start on the default still works.
 *
 * `ANALYSIS-PRESETS-01`: «Пресет» comes first (`./preset-select.tsx`). A chosen preset fills the
 * executor: the executor select shows the preset's executor, locked, and the request carries
 * `preset_id` and not the executor. Choosing a preset clears a hand-chosen executor, and taking the
 * preset off returns to «По умолчанию (маршрут)». The preset is part of the intent, so the same
 * version with another preset is another request. The server reads the preset's current version when
 * the run starts; the run page says which version it used.
 *
 * There is no provider-mode selector and, on failure, no offer to start the run "in recorded mode
 * instead" — the mode this deployment is configured for is shown on the run and never chosen
 * here. There is no cancel and no re-run carryover: `P3-WEB-01` rules both out for PC-01.
 */

import { useId, useState } from 'react';

import type { ExecutorConnectionId, PresetId, ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { CostApproval, ErrorState, LoadingState } from '@/shared/ui';
import { useIntentKey } from '@/shared/lib';
import type { RunFailure } from '@/entities/audit-run';
import { classifyRunFailure } from '@/entities/audit-run';
import { executionFailure } from '@/entities/execution';
import {
  executorChoices,
  useExecutorConnectionDetails,
  useExecutorConnections,
} from '@/entities/executor-connection';
import {
  presetChoices,
  presetFailure,
  presetFillsExecutorSentence,
  useAnalysisPresets,
} from '@/entities/analysis-preset';

import { startRunIntent } from '../model/start-run-intent';
import { useStartRun } from '../model/use-start-run';
import { useRunCostApproval } from '../model/use-run-cost-approval';

import type { ExecutorListReading } from './executor-select';
import { ExecutorSelectView } from './executor-select';
import type { PresetListReading } from './preset-select';
import { PresetSelectView } from './preset-select';
import { StartRunFailureView } from './start-run-failure';
import styles from './start-run-control.module.css';

export interface StartRunControlProps {
  /** The project the version belongs to, for the link a classification refusal carries. */
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** Called with the 202 reading, so the screen can move to run progress. */
  readonly onStarted?: ((run: RunStatus) => void) | undefined;
}

/**
 * The connections as the select reads them: the list, then the settings of each connection that
 * is not archived (the readiness rule needs the current revision and its probe).
 */
function useExecutorListReading(): ExecutorListReading {
  const list = useExecutorConnections();
  const items = list.data?.items ?? [];
  const settings = useExecutorConnectionDetails(
    items.filter((item) => item.archived_at === undefined).map((item) => item.connection_id),
  );

  if (list.data === undefined && list.isError) {
    const failure = executionFailure(list.error, false);
    return {
      phase: 'failed',
      detail: failure.detail,
      correlationId: failure.correlationId,
      onRetry: () => void list.refetch(),
    };
  }
  if (list.data === undefined || settings.pending) return { phase: 'loading' };
  return { phase: 'ready', choices: executorChoices(items, settings.details) };
}

/**
 * The presets as the select reads them: the list, judged against the executors already read (a
 * preset can start a run only if its executor can serve now). It waits for the executors, because
 * the verdict on each preset is theirs.
 */
function usePresetListReading(executors: ExecutorListReading, chosen: PresetId | null): PresetListReading {
  const presets = useAnalysisPresets();
  if (presets.data === undefined && presets.isError) {
    const failure = presetFailure(presets.error, false);
    return {
      phase: 'failed',
      detail: failure.detail,
      correlationId: failure.correlationId,
      onRetry: () => void presets.refetch(),
    };
  }
  if (presets.data === undefined || executors.phase === 'loading') return { phase: 'loading' };
  // With the executor list unread the verdict on a preset is unknown; every preset is then
  // blocked by the same sentence, and the person can still start without one.
  const choices = executors.phase === 'ready' ? executors.choices : [];
  return { phase: 'ready', choices: presetChoices(presets.data.items, choices, chosen) };
}

export function StartRunControl({ projectUid, versionUid, onStarted }: StartRunControlProps) {
  const [chosen, setChosen] = useState<ExecutorConnectionId | null>(null);
  const [chosenPreset, setChosenPreset] = useState<PresetId | null>(null);
  const [relaxedLimits, setRelaxedLimits] = useState(false);
  const optionsIntent = startRunIntent(versionUid, chosen, chosenPreset, relaxedLimits);
  const cost = useRunCostApproval(optionsIntent);
  const intent = startRunIntent(versionUid, chosen, chosenPreset, relaxedLimits, cost.draftConsent);
  const idempotencyKey = useIntentKey(intent.signature);
  const mutation = useStartRun();
  const selectId = useId();
  const presetSelectId = useId();
  const reading = useExecutorListReading();
  const presetReading = usePresetListReading(reading, chosenPreset);
  const presetName =
    presetReading.phase === 'ready'
      ? presetReading.choices.find((choice) => choice.presetId === chosenPreset)
      : undefined;
  const presetExecutor = presetName?.executorConnectionId ?? null;

  const send = () => {
    if (cost.consent === undefined || cost.pending || mutation.isPending) return;
    mutation.mutate(intent.command(idempotencyKey), {
      onSuccess: (run) => onStarted?.(run),
      onError: (error) => {
        if (error instanceof ApiError && error.details?.conflict_reason === 'run_cost_estimate_stale') cost.reset();
      },
    });
  };
  const costFailure = cost.error === null || cost.error === undefined ? null : executionFailure(cost.error, false);
  const locked = mutation.isPending || cost.pending;
  const staleEstimate = mutation.error instanceof ApiError && mutation.error.details?.conflict_reason === 'run_cost_estimate_stale';

  const failure: RunFailure | null =
    mutation.error === null || mutation.error === undefined
      ? null
      : classifyRunFailure(mutation.error);

  return (
    <div className="am-form" data-start-run-control>
      <PresetSelectView
        id={presetSelectId}
        reading={presetReading}
        value={chosenPreset}
        disabled={locked}
        onChange={(next) => {
          setChosenPreset(next);
          // A preset fills the executor; a hand choice would be a second way to say the same thing.
          setChosen(null);
          mutation.reset();
          cost.reset();
        }}
      />
      <ExecutorSelectView
        id={selectId}
        reading={reading}
        value={chosenPreset === null ? chosen : presetExecutor}
        disabled={locked}
        onChange={(next) => {
          setChosen(next);
          mutation.reset();
          cost.reset();
        }}
        lockedBy={
          chosenPreset === null
            ? undefined
            : presetFillsExecutorSentence(presetName?.name ?? 'выбранным')
        }
      />
      <label className={styles.limitToggle}>
        <input
          type="checkbox"
          checked={relaxedLimits}
          disabled={locked}
          onChange={(event) => {
            setRelaxedLimits(event.currentTarget.checked);
            mutation.reset();
            cost.reset();
          }}
        />
        Повышенные лимиты ИИ-анализа
      </label>
      <p className="am-note">
        {relaxedLimits
          ? 'Запрос на ответ до 64 000 токенов. Провайдер может установить меньший предел. Технический предел объёма входного текста сохраняется. Лимит стоимости подтверждается отдельно.'
          : 'Запрос на ответ до 16 000 токенов. Лимит стоимости подтверждается отдельно.'}
      </p>
      <button type="button" className="am-button" disabled={locked} onClick={() => { mutation.reset(); cost.request(); }}>
        Оценить стоимость
      </button>
      {cost.pending ? <LoadingState what="оценка стоимости" /> : null}
      {costFailure === null ? null : <ErrorState title="Стоимость не оценена" detail={costFailure.detail} correlationId={costFailure.correlationId} />}
      {staleEstimate ? <p role="alert">Оценка стоимости устарела. Получите новую оценку и подтвердите лимит снова.</p> : null}
      {cost.estimate === null ? null : <CostApproval estimate={cost.estimate} ceiling={cost.ceiling} approved={cost.approved}
        disabled={locked} onCeilingChange={cost.setCeiling} onApprovedChange={cost.setApproved} />}
      <button type="button" className="am-button" onClick={send} disabled={locked || cost.consent === undefined}>
        Запустить прогон
      </button>
      <p className="am-note">
        <em>
          Прогон использует тот режим провайдера, на который настроено это развёртывание.
          Он показан на прогоне и никогда не выбирается здесь.
        </em>
      </p>

      {mutation.isPending ? <LoadingState what="запрос на прогон" /> : null}

      {failure === null ? null : (
        <StartRunFailureView
          failure={failure}
          projectUid={projectUid}
          versionUid={versionUid}
          onRetry={send}
        />
      )}
    </div>
  );
}
