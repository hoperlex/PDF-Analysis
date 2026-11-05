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
 * `EXEC2-WEB-GROUPS-01` (ADR-0026 decisions 12 to 14): three ways to start, chosen with a radio
 * (`../model/start-mode.ts`). «Автоматически (по типу задачи)» sends no selector and is what the control
 * always did; «Группа исполнителей» shows the group select and sends `executor_group_id`;
 * «Конкретное подключение» is the preset and the executor selects above, and sends `preset_id` or
 * `executor_connection_id`. **Exactly one selector is sent**, never two: `startSelectors` is the one place
 * the choice becomes selectors. A mode whose own choice has not been made («Группа исполнителей» with no
 * group) would send nothing, which is «Автоматически» under another name, so it keeps both buttons
 * disabled and says what is missing. Changing a select moves the radio to «Конкретное подключение», and
 * taking the last choice off returns it to «Автоматически»: the radio always says what will be sent.
 *
 * There is no provider-mode selector and, on failure, no offer to start the run "in recorded mode
 * instead" — the mode this deployment is configured for is shown on the run and never chosen
 * here. There is no cancel and no re-run carryover: `P3-WEB-01` rules both out for PC-01.
 */

import { useId, useState } from 'react';

import type { ExecutorConnectionId, ExecutorGroupId, PresetId, ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { CostApproval, ErrorState, LoadingState } from '@/shared/ui';
import { routes, useIntentKey } from '@/shared/lib';
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

import type { StartChoice, StartMode } from '../model/start-mode';
import {
  START_CHOICE_MISSING,
  START_MODES,
  START_MODE_HINTS,
  START_MODE_LABELS,
  chooseMode,
  startChoiceComplete,
  startSelectors,
} from '../model/start-mode';
import { startRunIntent } from '../model/start-run-intent';
import { useStartRun } from '../model/use-start-run';
import { useRunCostApproval } from '../model/use-run-cost-approval';

import type { ExecutorListReading } from './executor-select';
import { ExecutorSelectView } from './executor-select';
import { GroupSelect } from './group-select';
import type { PresetListReading } from './preset-select';
import { PresetSelectView } from './preset-select';
import { StartRunFailureView } from './start-run-failure';
import styles from './start-run-control.module.css';
import { useMayActAsExpert } from '@/entities/account';

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

function StartRunControlInner({ projectUid, versionUid, onStarted }: StartRunControlProps) {
  const [mode, setMode] = useState<StartMode>('auto');
  const [chosen, setChosen] = useState<ExecutorConnectionId | null>(null);
  const [chosenPreset, setChosenPreset] = useState<PresetId | null>(null);
  const [chosenGroup, setChosenGroup] = useState<ExecutorGroupId | null>(null);
  const [relaxedLimits, setRelaxedLimits] = useState(false);
  // What is sent is decided here and nowhere else: at most one of the three selectors, and none for
  // «Автоматически». The raw state above can hold leftovers; the selectors cannot.
  const startChoice: StartChoice = { mode, groupId: chosenGroup, connectionId: chosen, presetId: chosenPreset };
  const selectors = startSelectors(startChoice);
  const complete = startChoiceComplete(startChoice);
  const optionsIntent = startRunIntent(
    versionUid, selectors.executorConnectionId, selectors.presetId, relaxedLimits, undefined, selectors.executorGroupId,
  );
  const cost = useRunCostApproval(optionsIntent);
  const intent = startRunIntent(
    versionUid, selectors.executorConnectionId, selectors.presetId, relaxedLimits, cost.draftConsent,
    selectors.executorGroupId,
  );
  const idempotencyKey = useIntentKey(intent.signature);
  const mutation = useStartRun();
  const selectId = useId();
  const presetSelectId = useId();
  const groupSelectId = useId();
  const modeLabelId = useId();
  const modeName = useId();
  const reading = useExecutorListReading();
  const presetReading = usePresetListReading(reading, chosenPreset);
  const presetName =
    presetReading.phase === 'ready'
      ? presetReading.choices.find((choice) => choice.presetId === chosenPreset)
      : undefined;
  const presetExecutor = presetName?.executorConnectionId ?? null;

  /** The radio: everything that belongs to another mode is dropped, so it cannot be sent from here. */
  const selectMode = (next: StartMode) => {
    const after = chooseMode(startChoice, next);
    setMode(after.mode);
    setChosenGroup(after.groupId);
    setChosen(after.connectionId);
    setChosenPreset(after.presetId);
    mutation.reset();
    cost.reset();
  };

  const send = () => {
    if (!complete || cost.consent === undefined || cost.pending || mutation.isPending) return;
    mutation.mutate(intent.command(idempotencyKey), {
      onSuccess: (run) => onStarted?.(run),
      onError: (error) => {
        if (error instanceof ApiError && error.details?.conflict_reason === 'run_cost_estimate_stale') cost.reset();
      },
    });
  };
  const costFailure = cost.error === null || cost.error === undefined ? null : executionFailure(cost.error, false);
  const comparisonOnlyCost = cost.error instanceof ApiError && cost.error.errorCode === 'analysis_input_invalid'
    && cost.error.details?.reason === 'comparison_only_version';
  const locked = mutation.isPending || cost.pending || comparisonOnlyCost;
  const staleEstimate = mutation.error instanceof ApiError && mutation.error.details?.conflict_reason === 'run_cost_estimate_stale';

  const failure: RunFailure | null =
    mutation.error === null || mutation.error === undefined
      ? null
      : classifyRunFailure(mutation.error);

  return (
    <div className="am-form" data-start-run-control>
      <div className={styles.modes} role="radiogroup" aria-labelledby={modeLabelId} data-start-mode={mode}>
        <p id={modeLabelId} className={styles.modeLabel}>Как выбрать исполнителя</p>
        {START_MODES.map((value) => (
          <label key={value} className={styles.mode}>
            <input
              type="radio"
              name={modeName}
              value={value}
              checked={mode === value}
              disabled={locked}
              data-start-mode-choice={value}
              onChange={() => selectMode(value)}
            />
            {START_MODE_LABELS[value]}
          </label>
        ))}
        <p className="am-form__hint" data-start-mode-hint={mode}>{START_MODE_HINTS[mode]}</p>
      </div>
      {mode === 'group' ? (
        <GroupSelect
          id={groupSelectId}
          value={chosenGroup}
          disabled={locked}
          onChange={(next) => {
            setChosenGroup(next);
            mutation.reset();
            cost.reset();
          }}
        />
      ) : (
        <>
          <PresetSelectView
            id={presetSelectId}
            reading={presetReading}
            value={chosenPreset}
            disabled={locked}
            onChange={(next) => {
              setChosenPreset(next);
              // A preset fills the executor; a hand choice would be a second way to say the same thing.
              setChosen(null);
              // The radio says what will be sent: a preset is «Конкретное подключение», and taking the
              // last choice off returns to «Автоматически».
              setMode(next === null ? 'auto' : 'connection');
              mutation.reset();
              cost.reset();
            }}
          />
          <ExecutorSelectView
            id={selectId}
            reading={reading}
            value={chosenPreset === null ? chosen : presetExecutor}
            disabled={locked}
            needsChoice={mode === 'connection'}
            onChange={(next) => {
              setChosen(next);
              setMode(next === null ? 'auto' : 'connection');
              mutation.reset();
              cost.reset();
            }}
            lockedBy={
              chosenPreset === null
                ? undefined
                : presetFillsExecutorSentence(presetName?.name ?? 'выбранным')
            }
          />
        </>
      )}
      {!complete && mode !== 'auto' ? (
        <p className="am-note" role="status" data-start-choice-missing={mode}>{START_CHOICE_MISSING[mode]}</p>
      ) : null}
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
        Временный режим сбора статистики
      </label>
      <p className="am-note">
        {relaxedLimits
          ? 'Прикладной денежный потолок отключён; фактические вызовы и расход записываются. Ответ до 64 000 токенов за вызов, предел провайдера может быть ниже.'
          : 'Запрос на ответ до 16 000 токенов. Лимит стоимости подтверждается отдельно.'}
      </p>
      <button type="button" className="am-button" disabled={locked || !complete} onClick={() => { mutation.reset(); cost.request(); }}>
        Оценить стоимость
      </button>
      {cost.pending ? <LoadingState what="оценка стоимости" /> : null}
      {costFailure === null ? null : <ErrorState
        title={comparisonOnlyCost ? 'Сервер не принимает этот PDF' : 'Стоимость не оценена'}
        detail={comparisonOnlyCost
          ? 'На этом сервере анализ раздела для PDF без пакета портала недоступен. Сообщите администратору: требуется обновление сервера.'
          : costFailure.detail}
        correlationId={costFailure.correlationId} />}
      {comparisonOnlyCost ? <p className="am-note">
        <a href={routes.stageComparison()}>Сравнение стадий</a>{' · '}
        <a href={routes.versionComparison()}>Сравнение версий</a>
      </p> : null}
      {staleEstimate ? <p role="alert">Оценка стоимости устарела. Получите новую оценку и подтвердите лимит снова.</p> : null}
      {cost.estimate === null ? null : <CostApproval estimate={cost.estimate} ceiling={cost.ceiling} approved={cost.approved}
        uncapped={relaxedLimits}
        disabled={locked} onCeilingChange={cost.setCeiling} onApprovedChange={cost.setApproved} />}
      <button type="button" className="am-button" onClick={send} disabled={locked || !complete || cost.consent === undefined}>
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

/**
 * `R-150e`: offered only to an account that may take an expert's action; the server refuses it
 * to anyone else. While the account is not known yet the control stays drawn.
 */
export function StartRunControl(props: Parameters<typeof StartRunControlInner>[0]) {
  const mayAct = useMayActAsExpert();
  if (!mayAct) return <p className="am-note" data-expert-only="StartRunControl">Запускать анализ может эксперт.</p>;
  return <StartRunControlInner {...props} />;
}
