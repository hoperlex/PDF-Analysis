'use client';

/**
 * «Новое подключение» (`createExecutorConnection` then `reviseExecutorConnection`,
 * `EXEC-HTTP-01`).
 *
 * A connection is created with a name and a kind only; its settings are its first revision. The
 * form asks for both at once and sends them in that order, each under its own idempotency key.
 * If the connection is created and the settings are refused, the connection exists without
 * settings: the form says so, keeps the name, and the next press saves the settings onto the
 * connection already created instead of creating a second one.
 *
 * The key is not here. It is entered after the settings, from the connection's card, through a
 * form that is never a JavaScript value.
 */

import { useState } from 'react';
import type { FormEvent } from 'react';

import type { ExecutorConnectionId, ExecutorKind, ExecutorPinnedModel } from '@/shared/api';
import { EXECUTOR_KIND_VALUES } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { KIND_DESCRIPTIONS, KIND_LABELS, connectionFailure } from '@/entities/executor-connection';

import { FIELD_NAMES, readRevision } from '../model/settings';
import { useCommandKey } from '../model/use-command-key';
import {
  useCreateExecutorConnection,
  useReviseExecutorConnection,
} from '../model/use-manage-executor-connection';
import { CommandFailure } from './command-failure';
import { SettingsFields } from './settings-fields';

export interface CreateConnectionFormProps {
  readonly pinnedModels: readonly ExecutorPinnedModel[];
}

export function CreateConnectionForm({ pinnedModels }: CreateConnectionFormProps) {
  const create = useCreateExecutorConnection();
  const revise = useReviseExecutorConnection();
  const createKeys = useCommandKey();
  const reviseKeys = useCommandKey();
  const [kind, setKind] = useState<ExecutorKind>('http_api');
  const [generation, setGeneration] = useState(0);
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  /** The connection created by an earlier press whose settings were then refused. */
  const [half, setHalf] = useState<{ readonly id: ExecutorConnectionId; readonly name: string } | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const busy = create.isPending || revise.isPending;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = half?.name ?? String(form.get(FIELD_NAMES.displayName) ?? '').trim();
    if (name === '' || name.length > 120) {
      setProblem('Укажите название подключения: до 120 символов.');
      return;
    }
    const reading = readRevision(kind, form, pinnedModels);
    if (!reading.ok) {
      setProblem(reading.problem);
      return;
    }
    setProblem(null);
    setFailure(null);
    setDone(null);

    let id = half?.id ?? null;
    if (id === null) {
      try {
        const connection = await create.mutateAsync({
          kind, displayName: name, idempotencyKey: createKeys.keyFor(JSON.stringify([kind, name])),
        });
        createKeys.release();
        id = connection.connection_id;
        setHalf({ id, name });
      } catch (error) {
        const failed = connectionFailure(error, true);
        if (failed.kind !== 'unknown_outcome') createKeys.release();
        setFailure(failed);
        return;
      }
    }
    try {
      await revise.mutateAsync({
        connectionId: id, body: reading.body,
        idempotencyKey: reviseKeys.keyFor(JSON.stringify([id, reading.body])),
      });
      reviseKeys.release();
      setHalf(null);
      setDone(name);
      setGeneration((current) => current + 1);
    } catch (error) {
      const failed = connectionFailure(error, true);
      if (failed.kind !== 'unknown_outcome') reviseKeys.release();
      setFailure(failed);
    }
  }

  return (
    <form className="am-form" key={generation} onSubmit={(event) => void submit(event)} data-executor-create-form>
      <h2>Новое подключение</h2>
      {half !== null ? (
        <p className="am-note" role="status" data-executor-create-half>
          Подключение «{half.name}» создано, но настройки не сохранены. Исправьте поля и нажмите
          «Сохранить настройки»: второе подключение не появится.
        </p>
      ) : (
        <>
          <div className="am-form__field">
            <label htmlFor="executor-create-name">Название</label>
            <input id="executor-create-name" name={FIELD_NAMES.displayName} type="text" required maxLength={120} autoComplete="off" />
          </div>
          <div className="am-form__field">
            <label htmlFor="executor-create-kind">Вид подключения</label>
            <select
              id="executor-create-kind"
              name={FIELD_NAMES.kind}
              value={kind}
              onChange={(event) => setKind(event.target.value as ExecutorKind)}
            >
              {EXECUTOR_KIND_VALUES.map((value) => (
                <option key={value} value={value}>{KIND_LABELS[value]}</option>
              ))}
            </select>
            <p className="am-form__hint">{KIND_DESCRIPTIONS[kind]}</p>
          </div>
        </>
      )}
      <SettingsFields kind={kind} pinnedModels={pinnedModels} idPrefix="executor-create" />
      {problem !== null ? <p className="am-form__problem" role="alert" data-executor-problem>{problem}</p> : null}
      <div className="am-form__row">
        <button className="am-button" type="submit" disabled={busy || pinnedModels.length === 0}>
          {half !== null ? 'Сохранить настройки' : 'Создать подключение'}
        </button>
      </div>
      {done !== null ? (
        <p className="am-note" role="status" data-executor-created>
          Подключение «{done}» создано. Теперь введите ключ в его карточке и нажмите «Проверить».
        </p>
      ) : null}
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </form>
  );
}
