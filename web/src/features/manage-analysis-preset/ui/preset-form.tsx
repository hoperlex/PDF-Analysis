'use client';

/**
 * The form of a preset (`ANALYSIS-PRESETS-01`): a name and an executor. It saves a new preset or,
 * given one, a new version of it — the full settings, never a patch; the earlier version is kept.
 *
 * The executor list is the connections the screen has read, every one that is not archived. A
 * connection that cannot serve a run now is still listed, with the reason in its label: a preset
 * may be saved ahead of the probe that makes it usable, and the start control says when it cannot be
 * chosen. The control is offered to an administrator only; the server checks the role again.
 *
 * One idempotency key per intent. The signature carries the preset (or «new») and both fields, so
 * an unchanged retry after an unknown outcome repeats the same command, and an edit is another one.
 */

import { useId, useState } from 'react';

import type { AnalysisPreset, ExecutorConnectionId } from '@/shared/api';
import { presetFailure } from '@/entities/analysis-preset';
import type { ExecutorChoice } from '@/entities/executor-connection';
import { executorChoiceLabel } from '@/entities/executor-connection';
import { LoadingState } from '@/shared/ui';

import { useCommandKey } from '../model/use-command-key';
import { useCreateAnalysisPreset, useReviseAnalysisPreset } from '../model/use-manage-analysis-preset';
import { PresetCommandFailure } from './preset-failure';

export interface PresetFormProps {
  /** The preset to revise; absent for a new one. */
  readonly preset?: AnalysisPreset | undefined;
  readonly choices: readonly ExecutorChoice[];
  /** Called after the server accepted the command, so the screen can close the form. */
  readonly onSaved?: (() => void) | undefined;
}

const NEW = 'new';

export function PresetForm({ preset, choices, onSaved }: PresetFormProps) {
  const [name, setName] = useState(preset?.name ?? '');
  const [connection, setConnection] = useState<ExecutorConnectionId | ''>(preset?.executor_connection_id ?? '');
  const nameId = useId();
  const connectionId = useId();
  const key = useCommandKey();
  const create = useCreateAnalysisPreset();
  const revise = useReviseAnalysisPreset();
  const mutation = preset === undefined ? create : revise;
  const live = choices.filter((choice) => !choice.archived);
  const ready = name.trim() !== '' && connection !== '';

  const send = () => {
    if (connection === '') return;
    const settings = { name, executorConnectionId: connection };
    const idempotencyKey = key.keyFor(`${preset?.preset_id ?? NEW}\u0000${name}\u0000${connection}`);
    const done = {
      onSuccess: () => {
        key.release();
        if (preset === undefined) {
          setName('');
          setConnection('');
        }
        onSaved?.();
      },
    };
    if (preset === undefined) create.mutate({ ...settings, idempotencyKey }, done);
    else revise.mutate({ ...settings, presetId: preset.preset_id, idempotencyKey }, done);
  };

  const failure = mutation.error === null || mutation.error === undefined ? null : presetFailure(mutation.error, true);

  return (
    <form
      className="am-form"
      data-preset-form={preset === undefined ? 'create' : 'revise'}
      onSubmit={(event) => {
        event.preventDefault();
        if (ready) send();
      }}
    >
      <div className="am-form__field">
        <label htmlFor={nameId}>Название пресета</label>
        <input
          id={nameId}
          type="text"
          maxLength={120}
          value={name}
          disabled={mutation.isPending}
          onChange={(event) => {
            setName(event.target.value);
            mutation.reset();
          }}
        />
        <p className="am-form__hint">До 120 знаков. Названия действующих пресетов не повторяются.</p>
      </div>
      <div className="am-form__field">
        <label htmlFor={connectionId}>Исполнитель</label>
        <select
          id={connectionId}
          value={connection}
          disabled={mutation.isPending}
          onChange={(event) => {
            setConnection(event.target.value);
            mutation.reset();
          }}
        >
          <option value="">Выберите исполнителя</option>
          {live.map((choice) => (
            <option key={choice.connectionId} value={choice.connectionId}>
              {executorChoiceLabel(choice)}
            </option>
          ))}
        </select>
        {live.length === 0 ? (
          <p className="am-form__hint" role="status">
            Подключений для выбора пока нет: сначала добавьте подключение на экране «Исполнители», вкладка «Подключения».
          </p>
        ) : null}
      </div>
      <div>
        <button type="button" className="am-button" disabled={!ready || mutation.isPending} onClick={send}>
          {preset === undefined ? 'Сохранить пресет' : 'Сохранить новую версию'}
        </button>
      </div>
      {mutation.isPending ? <LoadingState what="сохранение пресета" /> : null}
      {failure === null ? null : <PresetCommandFailure failure={failure} />}
    </form>
  );
}
