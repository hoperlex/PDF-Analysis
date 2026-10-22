'use client';

/**
 * Confirming the host key a probe observed (`EXEC-HTTP-01`, plan T-6).
 *
 * The host key is pinned: there is no trust on first use in the call path. A first probe of an
 * SSH connection ends `host_key_unpinned` and carries the key the remote machine presented; a
 * later one that sees another key ends `host_key_changed`. This control shows the observed key
 * and, on a press, saves it into a **new revision** (the full settings again, with the host key
 * set), which is unusable until probed. The person confirms a fingerprint they trust, from the
 * machine's own side; pressing without checking it is the one step this screen cannot do for
 * them, and the sentence beside the button says so.
 */

import { useState } from 'react';

import type { ExecutorConnectionId, ExecutorRevision } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { connectionFailure } from '@/entities/executor-connection';

import { requestFromRevision } from '../model/settings';
import { useCommandKey } from '../model/use-command-key';
import { useReviseExecutorConnection } from '../model/use-manage-executor-connection';
import { CommandFailure } from './command-failure';

export interface HostKeyControlProps {
  readonly connectionId: ExecutorConnectionId;
  readonly revision: ExecutorRevision;
  /** The key the last probe observed. */
  readonly observedHostKey: string;
  /** The probe saw a key different from the one pinned. */
  readonly changed: boolean;
}

export function HostKeyControl({ connectionId, revision, observedHostKey, changed }: HostKeyControlProps) {
  const revise = useReviseExecutorConnection();
  const keys = useCommandKey();
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const [savedNo, setSavedNo] = useState<number | null>(null);

  async function pin() {
    setFailure(null);
    const body = requestFromRevision(revision, { host_key: observedHostKey });
    try {
      const saved = await revise.mutateAsync({
        connectionId, body, idempotencyKey: keys.keyFor(JSON.stringify([connectionId, observedHostKey])),
      });
      keys.release();
      setSavedNo(saved.revision_no);
    } catch (error) {
      const failed = connectionFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <section aria-label="Отпечаток узла" data-executor-host-key={changed ? 'changed' : 'unpinned'}>
      <p className="am-note">
        {changed
          ? 'Узел представился другим отпечатком, чем закреплённый. Закрепляйте новый, только если сами сменили ключ узла.'
          : 'Узел ещё не закреплён. Сверьте отпечаток ниже с тем, что показывает сама удалённая машина, и закрепите его.'}
      </p>
      <p>Увиденный отпечаток: <code>{observedHostKey}</code></p>
      {savedNo !== null ? (
        <p className="am-note" role="status">
          Отпечаток закреплён в версии настроек {savedNo}. Нажмите «Проверить» ещё раз.
        </p>
      ) : (
        <button className="am-button" type="button" disabled={revise.isPending} onClick={() => void pin()}>
          Закрепить этот отпечаток
        </button>
      )}
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </section>
  );
}
