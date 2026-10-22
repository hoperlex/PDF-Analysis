'use client';

/**
 * «Создать ключ» (`generateExecutorSshKey`, `EXEC-HTTP-01`): the application makes the SSH key
 * pair, seals the private half to the connection's SSH endpoint and shows the public half.
 *
 * **The public half and its `authorized_keys` line are shown once, here, with a copy button.**
 * The private half never leaves the server. The line carries the `restrict` option, so the key
 * opens nothing but what the forced command on the remote machine allows; the person adds it
 * to the file of a dedicated low-privilege user (the runbook says how). The public key stays
 * visible on the connection's card afterwards, because it is public; the line is rebuilt from
 * it by hand if needed, which is why it is shown once and not stored.
 *
 * A second key replaces the first: the old one stops opening the moment the new one is sealed.
 */

import { useState } from 'react';

import type { ExecutorConnectionId, ExecutorSshKey } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { connectionFailure } from '@/entities/executor-connection';

import { useCommandKey } from '../model/use-command-key';
import { useGenerateExecutorSshKey } from '../model/use-manage-executor-connection';
import { CommandFailure } from './command-failure';

export interface SshKeyControlProps {
  readonly connectionId: ExecutorConnectionId;
  /** The connection already holds a generated key, which a new one would replace. */
  readonly hasKey: boolean;
}

function CopyLine({ label, value }: { readonly label: string; readonly value: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      // No clipboard permission: the text stays selectable in the box above.
      setCopied(false);
    }
  }
  return (
    <div className="am-form__field">
      <strong>{label}</strong>
      <textarea readOnly rows={3} value={value} spellCheck={false} onFocus={(event) => event.currentTarget.select()} />
      <div className="am-form__row">
        <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => void copy()}>
          Скопировать
        </button>
        {copied ? <span role="status" className="am-form__hint">Скопировано.</span> : null}
      </div>
    </div>
  );
}

export function SshKeyControl({ connectionId, hasKey }: SshKeyControlProps) {
  const generate = useGenerateExecutorSshKey();
  const keys = useCommandKey();
  const [shown, setShown] = useState<ExecutorSshKey | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function press() {
    setFailure(null);
    try {
      setShown(await generate.mutateAsync({ connectionId, idempotencyKey: keys.keyFor(connectionId) }));
      keys.release();
    } catch (error) {
      const failed = connectionFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <>
      <button
        className="am-button am-button--quiet"
        type="button"
        data-executor-ssh-key={connectionId}
        disabled={generate.isPending}
        onClick={() => void press()}
      >
        {hasKey ? 'Создать новый ключ' : 'Создать ключ'}
      </button>
      {hasKey && shown === null ? (
        <p className="am-form__hint">Новый ключ заменит прежний: прежний перестанет подходить сразу.</p>
      ) : null}
      {shown !== null ? (
        <section role="group" aria-label="Созданный ключ" data-executor-ssh-key-shown>
          <p className="am-note">
            Ключ создан. Скопируйте строку сейчас: она показывается один раз. Добавьте её в файл
            authorized_keys отдельного пользователя с ограниченными правами на удалённой машине.
            Закрытая половина ключа запечатана на стенде и никогда не показывается.
          </p>
          <CopyLine label="Открытый ключ" value={shown.public_key} />
          <CopyLine label="Строка для файла authorized_keys" value={shown.authorized_keys_line} />
        </section>
      ) : null}
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </>
  );
}
