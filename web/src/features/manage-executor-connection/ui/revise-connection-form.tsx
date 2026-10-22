'use client';

/**
 * «Изменить настройки» — a new revision (`reviseExecutorConnection`, `EXEC-HTTP-01`).
 *
 * A revision is immutable and carries the full settings, never a patch, so the form starts from
 * the current revision and sends everything. A new revision is unusable until a probe passes on
 * it.
 *
 * **The warning that matters:** a key opens only for the destination it was entered for. A
 * revision that changes the address, the way of connecting or the SSH endpoint leaves the
 * current key unreadable for it, and the key is write-only, so it cannot be carried over — it
 * must be pasted again. The form recomputes the destination from what is typed and says so
 * *before* the button is pressed, and again after saving, with the way to the key form.
 */

import { useState } from 'react';
import type { FormEvent } from 'react';

import type {
  ExecutorConnection,
  ExecutorPinnedModel,
  ExecutorRevision,
} from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { connectionFailure } from '@/entities/executor-connection';
import { executorSecretScreenUrl } from '@/features/set-executor-secret';

import { draftMovesTheKey, readRevision } from '../model/settings';
import { useCommandKey } from '../model/use-command-key';
import { useReviseExecutorConnection } from '../model/use-manage-executor-connection';
import { CommandFailure } from './command-failure';
import { SettingsFields } from './settings-fields';

export interface ReviseConnectionFormProps {
  readonly connection: ExecutorConnection;
  /** The current revision; absent when the connection has no settings yet. */
  readonly revision: ExecutorRevision | undefined;
  readonly pinnedModels: readonly ExecutorPinnedModel[];
  /** The connection holds a key that a moved destination would strand. */
  readonly holdsKey: boolean;
  readonly onClose: () => void;
}

export function ReviseConnectionForm({
  connection, revision, pinnedModels, holdsKey, onClose,
}: ReviseConnectionFormProps) {
  const revise = useReviseExecutorConnection();
  const keys = useCommandKey();
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const [moves, setMoves] = useState(false);
  const [saved, setSaved] = useState<{ readonly no: number; readonly moved: boolean } | null>(null);

  function watch(event: FormEvent<HTMLFormElement>) {
    if (revision === undefined) return;
    setMoves(draftMovesTheKey(connection.kind, revision, new FormData(event.currentTarget), pinnedModels));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const reading = readRevision(connection.kind, new FormData(event.currentTarget), pinnedModels);
    if (!reading.ok) {
      setProblem(reading.problem);
      return;
    }
    setProblem(null);
    setFailure(null);
    try {
      const made = await revise.mutateAsync({
        connectionId: connection.connection_id,
        body: reading.body,
        idempotencyKey: keys.keyFor(JSON.stringify([connection.connection_id, reading.body])),
      });
      keys.release();
      setSaved({ no: made.revision_no, moved: moves });
    } catch (error) {
      const failed = connectionFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  if (saved !== null) {
    return (
      <section aria-label="Настройки сохранены" data-executor-revised>
        <p className="am-note" role="status">
          Настройки сохранены: версия {saved.no}. Новая версия не годится в работу, пока проверка на
          ней не пройдёт.
          {saved.moved && holdsKey
            ? ' Адрес или способ связи изменились, поэтому прежний ключ больше не открывается: вставьте его заново.'
            : ' Нажмите «Проверить».'}
        </p>
        {saved.moved && holdsKey ? (
          <p><a className="am-button" href={executorSecretScreenUrl(connection.connection_id)}>Ввести ключ заново</a></p>
        ) : null}
        <button className="am-button am-button--quiet" type="button" onClick={onClose}>Закрыть</button>
      </section>
    );
  }

  return (
    <form className="am-form" onSubmit={(event) => void submit(event)} onChange={watch} data-executor-revise-form={connection.connection_id}>
      <h3>Изменить настройки: «{connection.display_name}»</h3>
      <SettingsFields
        kind={connection.kind}
        pinnedModels={pinnedModels}
        initial={revision}
        idPrefix={`executor-revise-${connection.connection_id}`}
      />
      {moves && holdsKey ? (
        <p className="am-note" role="alert" data-executor-key-moves>
          Адрес, способ связи или узел SSH изменены. Ключ привязан к прежнему адресу и для нового
          не откроется: после сохранения его нужно вставить заново.
        </p>
      ) : (
        <p className="am-form__hint">
          Если изменить адрес, способ связи или узел SSH, ключ, введённый для прежнего адреса,
          перестанет открываться, и его придётся вставить заново.
        </p>
      )}
      {problem !== null ? <p className="am-form__problem" role="alert" data-executor-problem>{problem}</p> : null}
      <div className="am-form__row">
        <button className="am-button" type="submit" disabled={revise.isPending || pinnedModels.length === 0}>
          Сохранить настройки
        </button>
        <button className="am-button am-button--quiet" type="button" disabled={revise.isPending} onClick={onClose}>
          Отмена
        </button>
      </div>
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </form>
  );
}
