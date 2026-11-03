'use client';

/**
 * Path A, the session (`EXEC2-WEB-WIZARD-01`, ADR-0026 decision 7): what the stand is doing on the
 * server, and the one step that is the person's — confirming the host key.
 *
 *     запрошена → читается отпечаток → нужно подтверждение → устанавливается → установлена | не удалась
 *
 * **The fingerprint is confirmed by value and on purpose.** The worker reads the server's host key and
 * stops in `awaiting_host_key`; there is no trust on first use. The screen shows the observed
 * fingerprint, says to compare it with the one the server itself shows, and enables the button only
 * after the person ticks that they did. The stand refuses a fingerprint that is not the observed one
 * (`host_key_changed`), so a stale tab cannot confirm a key it did not show.
 *
 * The wizard only creates sessions with a key the stand made (`generated_key`). A session read back
 * from the API may say `pasted_key` — someone created it over the API — and is shown as that, with no
 * line to add, because there is none. `SshInstallSessionView` is a view driven by props;
 * `SshInstallSession` reads the session (a bounded re-read while the worker moves, `useAgentInstall`)
 * and sends the confirmation.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import type { ExecutorAgentInstall, ExecutorAgentInstallState, ExecutorConnectionId } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { executionFailure } from '@/entities/execution';
import { ErrorState } from '@/shared/ui';
import {
  CommandFailure,
  useCommandKey,
  useConfirmExecutorAgentInstallHostKey,
} from '@/features/manage-executor-connection';

import { agentFailure } from '../model/failure';
import { useAgentInstall } from '../model/use-agent-polls';
import {
  AUTHORIZED_KEYS_HINT,
  AUTHORIZED_KEYS_TITLE,
  FINGERPRINT_CHECK_LABEL,
  FINGERPRINT_CONFIRM_LABEL,
  FINGERPRINT_HINT,
  FINGERPRINT_TITLE,
  INSTALL_FAILED_TITLE,
  INSTALL_FAILURE_SENTENCES,
  INSTALL_RETRY_LABEL,
  INSTALL_STATE_HINTS,
  INSTALL_STATE_LABELS,
  KEY_NOT_REMOVED_NOTE,
  KEY_REMOVED_NOTE,
  SSH_ACCESS_LABELS,
  SSH_FORM_TITLE,
} from '../model/words';
import { CopyBox } from './copy-box';

const BADGE: Readonly<Record<ExecutorAgentInstallState, string>> = {
  requested: 'pending',
  scanning: 'pending',
  awaiting_host_key: 'degraded',
  installing: 'active',
  succeeded: 'ok',
  failed: 'failed',
};

export interface SshInstallSessionViewProps {
  readonly install: ExecutorAgentInstall;
  readonly confirming: boolean;
  readonly confirmFailure: ExecutionFailure | null;
  readonly onConfirm: (fingerprint: string) => void;
  readonly onRetry: () => void;
  /** What follows a finished install: the agent's registration progress. */
  readonly children?: ReactNode | undefined;
}

export function SshInstallSessionView({
  install, confirming, confirmFailure, onConfirm, onRetry, children,
}: SshInstallSessionViewProps) {
  const [checked, setChecked] = useState(false);
  const state = install.state;
  const fingerprint = install.observed_host_key_fingerprint;
  const finished = state === 'succeeded' || state === 'failed';
  const showLine = install.access === 'generated_key' && install.authorized_keys_line !== undefined
    && !finished && install.key_removed_at === undefined;

  return (
    <section role="group" aria-label={SSH_FORM_TITLE} data-agent-install={state} data-agent-install-id={install.install_id}>
      <h3>{SSH_FORM_TITLE}</h3>
      <p>
        <span className={`am-badge am-badge--${BADGE[state]}`}>{INSTALL_STATE_LABELS[state]}</span>{' '}
        сервер <code>{install.ssh_user}@{install.ssh_host}:{install.ssh_port}</code>
      </p>
      <p className="am-form__hint">{INSTALL_STATE_HINTS[state]}</p>
      <p className="am-form__hint" data-agent-install-access={install.access}>Доступ: {SSH_ACCESS_LABELS[install.access]}.</p>

      {showLine && install.authorized_keys_line !== undefined ? (
        <div role="group" aria-label={AUTHORIZED_KEYS_TITLE} data-agent-authorized-keys>
          <p className="am-note">{AUTHORIZED_KEYS_HINT}</p>
          <CopyBox value={install.authorized_keys_line} label={AUTHORIZED_KEYS_TITLE} variant="block" name="authorized-keys" />
        </div>
      ) : null}

      {state === 'awaiting_host_key' ? (
        <div role="group" aria-label={FINGERPRINT_TITLE} data-agent-fingerprint>
          <p className="am-note">{FINGERPRINT_HINT}</p>
          {fingerprint === undefined ? (
            <p>Отпечаток ещё не получен: страница обновится сама.</p>
          ) : (
            <>
              <p>{FINGERPRINT_TITLE}: <code data-agent-fingerprint-value>{fingerprint}</code></p>
              <label className="am-form__field">
                <span>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => setChecked(event.target.checked)}
                    data-agent-fingerprint-check
                  />{' '}
                  {FINGERPRINT_CHECK_LABEL}
                </span>
              </label>
              <button
                className="am-button"
                type="button"
                disabled={!checked || confirming}
                data-agent-fingerprint-confirm
                onClick={() => onConfirm(fingerprint)}
              >
                {FINGERPRINT_CONFIRM_LABEL}
              </button>
            </>
          )}
          {confirmFailure !== null ? <CommandFailure failure={confirmFailure} /> : null}
        </div>
      ) : null}

      {state === 'succeeded' ? (
        <>
          <p className="am-note" role="status" data-agent-key-removed={install.key_removed_at === undefined ? 'no' : 'yes'}>
            {install.key_removed_at === undefined ? KEY_NOT_REMOVED_NOTE : KEY_REMOVED_NOTE}
          </p>
          {children}
        </>
      ) : null}

      {state === 'failed' ? (
        <div role="group" aria-label={INSTALL_FAILED_TITLE} data-agent-install-failure={install.failure_reason ?? 'unknown'}>
          <p className="am-form__problem" role="alert">
            {install.failure_reason === undefined
              ? 'Установка не удалась, причина не названа.'
              : INSTALL_FAILURE_SENTENCES[install.failure_reason]}
          </p>
          <button className="am-button" type="button" data-agent-install-retry onClick={onRetry}>{INSTALL_RETRY_LABEL}</button>
        </div>
      ) : null}
    </section>
  );
}

export interface SshInstallSessionProps {
  readonly connectionId: ExecutorConnectionId;
  readonly initial: ExecutorAgentInstall;
  readonly onRetry: () => void;
  readonly children?: ReactNode | undefined;
}

export function SshInstallSession({ connectionId, initial, onRetry, children }: SshInstallSessionProps) {
  const read = useAgentInstall(connectionId, initial.install_id, initial);
  const confirm = useConfirmExecutorAgentInstallHostKey();
  const keys = useCommandKey();
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const install = read.data ?? initial;

  async function confirmFingerprint(fingerprint: string) {
    setFailure(null);
    try {
      await confirm.mutateAsync({
        connectionId,
        installId: install.install_id,
        hostKeyFingerprint: fingerprint,
        idempotencyKey: keys.keyFor(`${install.install_id}:${fingerprint}`),
      });
      keys.release();
    } catch (error) {
      const failed = agentFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <>
      <SshInstallSessionView
        install={install}
        confirming={confirm.isPending}
        confirmFailure={failure}
        onConfirm={(fingerprint) => void confirmFingerprint(fingerprint)}
        onRetry={onRetry}
      >
        {children}
      </SshInstallSessionView>
      {read.isError ? (
        <ErrorState
          title="Состояние установки не прочитано"
          detail={executionFailure(read.error, false).detail}
          onRetry={() => void read.refetch()}
        />
      ) : null}
    </>
  );
}
