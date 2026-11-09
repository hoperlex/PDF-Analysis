'use client';

/**
 * «Подробнее» of a server (`HOSTS-WEB-01`, plan 2026-11-09 §6 and §7.2; **administrator only**, the read refuses any other
 * role): its places, each client found on it with its login and, for every model, why it cannot be used now, and the tasks
 * running on it. This is the one place an unavailable model is drawn, and it is drawn with its reason: a list never shows
 * what cannot be used, and a screen that blocks an action says why.
 *
 * «Проверить сейчас» reads the state again. The state is derived at read time from the agent's report, so a re-read is the
 * honest check the stand can make; the agent itself re-checks its models on a change and every few hours.
 */

import { useState } from 'react';

import type {
  ExecutorHostDetails,
  ExecutorHostId,
  ExecutorHostProviderDetail,
  ExecutorHostSlotUse,
  ExecutorHostSlots,
  ExecutorProvider,
} from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { executionFailure } from '@/entities/execution';
import {
  ACCESS_LABELS,
  AUTH_STATE_LABELS,
  MODEL_STATE_LABELS,
  PROVIDER_LABELS,
  UNAVAILABLE_REASON_SENTENCES,
  hostFailure,
  modelLabel,
  useExecutorHostDetails,
} from '@/entities/executor-host';
import { useCommandKey } from '@/features/manage-executor-connection';
import { STAGE_ROW_LABELS, rowOfStageKey } from '@/entities/stage-layout';
import { ErrorState, LoadingState } from '@/shared/ui';

import {
  DETAILS_NO_PROVIDERS,
  DETAILS_NO_TASKS,
  DETAILS_PROVIDERS_TITLE,
  DETAILS_RECHECK,
  DETAILS_RECHECK_HINT,
  DETAILS_SLOTS_HINT,
  DETAILS_SLOTS_SAVE,
  DETAILS_SLOTS_TITLE,
  DETAILS_TASKS_TITLE,
} from '../model/words';
import { useSetExecutorHostSlots } from '../model/use-manage-executor-host';
import { HostFailure } from './host-failure';
import styles from './manage-executor-host.module.css';

/** What a task's stage reads as: the row of the layout it belongs to, or the stage key as the server wrote it. */
function stageText(stageKey: string): string {
  const row = rowOfStageKey(stageKey);
  return row === null ? stageKey : STAGE_ROW_LABELS[row];
}

function ProviderBlock({ provider }: { readonly provider: ExecutorHostProviderDetail }) {
  return (
    <li className={styles.item} data-host-provider={provider.provider} data-host-access={provider.access} data-host-auth={provider.auth_state}>
      <strong>{PROVIDER_LABELS[provider.provider]}</strong> · {ACCESS_LABELS[provider.access]} · {AUTH_STATE_LABELS[provider.auth_state]}
      {provider.cli_version === undefined ? null : <> · версия <code>{provider.cli_version}</code></>}
      <ul className={styles.plain}>
        {provider.models.map((model) => (
          <li key={model.model_id} className={styles.item} data-host-model={model.model_id} data-host-model-state={model.state}>
            {modelLabel(model.model_id)} — {MODEL_STATE_LABELS[model.state]}
            {model.reasons.length === 0 ? null : (
              <span className={styles.reason} data-host-model-reasons>
                {': '}
                {model.reasons.map((reason, at) => (
                  <span key={reason} data-host-reason={reason}>{at === 0 ? '' : '; '}{UNAVAILABLE_REASON_SENTENCES[reason]}</span>
                ))}
              </span>
            )}
          </li>
        ))}
      </ul>
    </li>
  );
}

export interface SlotsViewProps {
  readonly slots: readonly ExecutorHostSlotUse[];
  readonly drafts: Readonly<Record<string, string>>;
  readonly pending: boolean;
  readonly problem: string | null;
  readonly failure: ExecutionFailure | null;
  readonly onDraft: (provider: ExecutorProvider, value: string) => void;
  readonly onSave: () => void;
}

export function SlotsView({ slots, drafts, pending, problem, failure, onDraft, onSave }: SlotsViewProps) {
  return (
    <section role="group" aria-label={DETAILS_SLOTS_TITLE} data-host-slots>
      <p className={styles.detailsTitle}>{DETAILS_SLOTS_TITLE}</p>
      <p className="am-form__hint">{DETAILS_SLOTS_HINT}</p>
      <ul className={styles.plain}>
        {slots.map((slot) => (
          <li key={slot.provider} className={styles.item} data-host-slot={slot.provider}>
            <label>
              {PROVIDER_LABELS[slot.provider]} · {ACCESS_LABELS[slot.access]}: занято {slot.in_use} из{' '}
              <input
                className={styles.slotInput}
                type="number"
                min={1}
                max={16}
                value={drafts[slot.provider] ?? String(slot.slots)}
                aria-label={`Мест: ${PROVIDER_LABELS[slot.provider]}`}
                onChange={(event) => onDraft(slot.provider, event.currentTarget.value)}
              />
            </label>
          </li>
        ))}
      </ul>
      {problem === null ? null : <p className="am-form__problem" role="alert">{problem}</p>}
      <button className="am-button am-button--quiet" type="button" disabled={pending || slots.length === 0} data-host-slots-save onClick={onSave}>
        {DETAILS_SLOTS_SAVE}
      </button>
      {failure === null ? null : <HostFailure failure={failure} />}
    </section>
  );
}

export interface HostDetailsViewProps {
  readonly details: ExecutorHostDetails;
  readonly rechecking: boolean;
  readonly onRecheck: () => void;
  /** The places and their save; absent, the places are only listed. */
  readonly slots?: SlotsViewProps | undefined;
}

export function HostDetailsView({ details, rechecking, onRecheck, slots }: HostDetailsViewProps) {
  return (
    <section className={styles.details} role="group" aria-label={`Подробнее: ${details.host.display_name}`} data-host-details>
      <div className="am-form__row">
        <button className="am-button am-button--quiet am-button--small" type="button" disabled={rechecking} data-host-recheck onClick={onRecheck}>
          {DETAILS_RECHECK}
        </button>
        <span className="am-form__hint">{DETAILS_RECHECK_HINT}</span>
      </div>
      {slots === undefined ? null : <SlotsView {...slots} />}
      <div>
        <p className={styles.detailsTitle}>{DETAILS_PROVIDERS_TITLE}</p>
        {details.providers.length === 0 ? (
          <p className="am-note">{DETAILS_NO_PROVIDERS}</p>
        ) : (
          <ul className={styles.plain}>
            {details.providers.map((provider) => <ProviderBlock key={`${provider.provider}:${provider.access}`} provider={provider} />)}
          </ul>
        )}
      </div>
      <div>
        <p className={styles.detailsTitle}>{DETAILS_TASKS_TITLE}</p>
        {details.tasks.length === 0 ? (
          <p className="am-note">{DETAILS_NO_TASKS}</p>
        ) : (
          <ul className={styles.plain}>
            {details.tasks.map((task) => (
              <li key={task.task_id} className={styles.item} data-host-task>
                Прогон <code>{task.run_id}</code>
                {task.stage_key === undefined ? null : <> · {stageText(task.stage_key)}</>}
                {' · '}{modelLabel(task.model_id)} · с <time dateTime={task.since}>{new Date(task.since).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</time>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export function HostDetails({ hostId }: { readonly hostId: ExecutorHostId }) {
  const read = useExecutorHostDetails(hostId, true);
  const setSlots = useSetExecutorHostSlots();
  const keys = useCommandKey();
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  if (read.isPending) return <LoadingState what="сведения о сервере" />;
  if (read.data === undefined) {
    const failed = executionFailure(read.error, false);
    return (
      <ErrorState title="Сведения о сервере не прочитаны" detail={failed.detail} correlationId={failed.correlationId} onRetry={() => void read.refetch()} />
    );
  }

  async function save(details: ExecutorHostDetails) {
    setFailure(null);
    const changed: ExecutorHostSlots = {};
    for (const slot of details.slots) {
      const draft = drafts[slot.provider];
      if (draft === undefined) continue;
      const value = Number(draft);
      if (!Number.isInteger(value) || value < 1 || value > 16) {
        setProblem('Число мест — целое от 1 до 16.');
        return;
      }
      if (value !== slot.slots) changed[slot.provider] = value;
    }
    setProblem(null);
    if (Object.keys(changed).length === 0) return;
    try {
      await setSlots.mutateAsync({ hostId, slots: changed, idempotencyKey: keys.keyFor(JSON.stringify(changed)) });
      keys.release();
      setDrafts({});
    } catch (error) {
      const failed = hostFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  const details = read.data;
  return (
    <HostDetailsView
      details={details}
      rechecking={read.isFetching}
      onRecheck={() => void read.refetch()}
      slots={{
        slots: details.slots,
        drafts,
        pending: setSlots.isPending,
        problem,
        failure,
        onDraft: (provider, value) => setDrafts((current) => ({ ...current, [provider]: value })),
        onSave: () => void save(details),
      }}
    />
  );
}
