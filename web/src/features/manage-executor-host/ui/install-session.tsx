'use client';

/**
 * The session of an install over SSH (`HOSTS-WEB-01`, plan 2026-11-09 §7.3): the line to add to `authorized_keys`, the
 * fingerprint to confirm, and three steps of progress. Then the status of the server itself, «ждём сервер…» → «найдено: …».
 *
 * **The fingerprint is confirmed by value and on purpose.** The worker reads the server's host key and stops in
 * `awaiting_host_key`; there is no trust on first use. The screen shows the fingerprint it observed, says to compare it with
 * the one the server itself shows, and enables the button only after the person ticks that they did. The stand refuses any
 * other fingerprint, so a stale tab cannot confirm a key it did not show.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import { useQuery } from '@tanstack/react-query';

import type { ExecutorAgentInstall, ExecutorHostId } from '@/shared/api';
import { getExecutorHostAgentInstall, queryKeys } from '@/shared/api';
import { AGENT_INSTALL_POLL_MS } from '@/shared/config';
import type { ExecutionFailure } from '@/entities/execution';
import { hostFailure } from '@/entities/executor-host';
import { CopyBox, INSTALL_FAILURE_SENTENCES } from '@/features/connect-remote-agent';
import { useCommandKey } from '@/features/manage-executor-connection';

import {
  FINGERPRINT_CHECK,
  FINGERPRINT_CONFIRM,
  FINGERPRINT_HINT,
  FINGERPRINT_TITLE,
  FINGERPRINT_WAITING,
  INSTALL_FAILED_FALLBACK,
  INSTALL_RETRY,
  INSTALL_STEP_IDS,
  INSTALL_STEP_LABELS,
  KEY_LINE_HINT,
  KEY_LINE_TITLE,
  STEP_STATE_MARKS,
  STEP_STATE_WORDS,
  installSteps,
} from '../model/words';
import type { InstallStepState } from '../model/words';
import { useConfirmExecutorHostAgentInstallHostKey } from '../model/use-manage-executor-host';
import { HostFailure } from './host-failure';
import styles from './manage-executor-host.module.css';

const STEP_CLASS: Readonly<Record<InstallStepState, string>> = {
  done: styles.stepDone,
  current: styles.stepCurrent,
  todo: styles.stepTodo,
  failed: styles.stepFailed,
};

export interface InstallSessionViewProps {
  readonly install: ExecutorAgentInstall;
  readonly confirming: boolean;
  readonly confirmFailure: ExecutionFailure | null;
  readonly onConfirm: (fingerprint: string) => void;
  readonly onRetry: () => void;
  /** The status of the server once the install has finished. */
  readonly children?: ReactNode | undefined;
}

export function InstallSessionView({ install, confirming, confirmFailure, onConfirm, onRetry, children }: InstallSessionViewProps) {
  const [checked, setChecked] = useState(false);
  const fingerprint = install.observed_host_key_fingerprint;
  const steps = installSteps(install.state, {
    fingerprintSeen: fingerprint !== undefined,
    confirmed: install.host_key_confirmed_at !== undefined,
  });
  const showLine = install.access === 'generated_key' && install.authorized_keys_line !== undefined
    && install.state !== 'succeeded' && install.state !== 'failed' && install.key_removed_at === undefined;

  return (
    <section role="group" aria-label="Установка по SSH" data-install-state={install.state}>
      <p>
        Сервер <code>{install.ssh_user}@{install.ssh_host}:{install.ssh_port}</code>
      </p>
      <ol className={styles.steps} data-install-steps>
        {INSTALL_STEP_IDS.map((id) => {
          const state = steps[id];
          return (
            <li key={id} className={`${styles.step} ${STEP_CLASS[state]}`} data-install-step={id} data-install-step-state={state}>
              <span className={styles.stepMark} role="img" aria-label={STEP_STATE_WORDS[state]}>{STEP_STATE_MARKS[state]}</span>
              <span>{INSTALL_STEP_LABELS[id]}</span>
            </li>
          );
        })}
      </ol>

      {showLine && install.authorized_keys_line !== undefined ? (
        <div role="group" aria-label={KEY_LINE_TITLE} data-install-key-line>
          <p className="am-note">{KEY_LINE_HINT}</p>
          <CopyBox value={install.authorized_keys_line} label={KEY_LINE_TITLE} variant="block" name="host-authorized-keys" />
        </div>
      ) : null}

      {install.state === 'awaiting_host_key' ? (
        <div role="group" aria-label={FINGERPRINT_TITLE} data-install-fingerprint>
          <p className="am-note">{FINGERPRINT_HINT}</p>
          {fingerprint === undefined ? (
            <p>{FINGERPRINT_WAITING}</p>
          ) : (
            <>
              <p>{FINGERPRINT_TITLE}: <code data-install-fingerprint-value>{fingerprint}</code></p>
              <label className="am-form__field">
                <span>
                  <input type="checkbox" checked={checked} onChange={(event) => setChecked(event.currentTarget.checked)} data-install-fingerprint-check />{' '}
                  {FINGERPRINT_CHECK}
                </span>
              </label>
              <button className="am-button" type="button" disabled={!checked || confirming} data-install-fingerprint-confirm onClick={() => onConfirm(fingerprint)}>
                {FINGERPRINT_CONFIRM}
              </button>
            </>
          )}
          {confirmFailure === null ? null : <HostFailure failure={confirmFailure} />}
        </div>
      ) : null}

      {install.state === 'failed' ? (
        <div role="group" aria-label="Установка не удалась" data-install-failure={install.failure_reason ?? 'unknown'}>
          <p className="am-form__problem" role="alert">
            {install.failure_reason === undefined ? INSTALL_FAILED_FALLBACK : INSTALL_FAILURE_SENTENCES[install.failure_reason]}
          </p>
          <button className="am-button" type="button" data-install-retry onClick={onRetry}>{INSTALL_RETRY}</button>
        </div>
      ) : null}

      {install.state === 'succeeded' ? children : null}
    </section>
  );
}

export interface InstallSessionProps {
  readonly hostId: ExecutorHostId;
  readonly initial: ExecutorAgentInstall;
  readonly onRetry: () => void;
  readonly children?: ReactNode | undefined;
}

function installIsMoving(install: ExecutorAgentInstall | undefined): boolean {
  return install !== undefined && (install.state === 'requested' || install.state === 'scanning' || install.state === 'installing');
}

export function InstallSession({ hostId, initial, onRetry, children }: InstallSessionProps) {
  // Re-read while the worker moves, from the answer of the command that created the session; it stops by itself at the
  // person's step and at the end.
  const read = useQuery<ExecutorAgentInstall>({
    queryKey: [...queryKeys.execution.all(), 'host-install', initial.install_id],
    queryFn: async () => (await getExecutorHostAgentInstall({ path: { host_id: hostId, install_id: initial.install_id } })).data,
    initialData: initial,
    staleTime: 0,
    refetchInterval: (query) => (installIsMoving(query.state.data) ? AGENT_INSTALL_POLL_MS : false),
  });
  const confirm = useConfirmExecutorHostAgentInstallHostKey();
  const keys = useCommandKey();
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const install = read.data;

  async function confirmFingerprint(fingerprint: string) {
    setFailure(null);
    try {
      await confirm.mutateAsync({
        hostId, installId: install.install_id, hostKeyFingerprint: fingerprint,
        idempotencyKey: keys.keyFor(`${install.install_id}:${fingerprint}`),
      });
      keys.release();
    } catch (error) {
      const failed = hostFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <InstallSessionView install={install} confirming={confirm.isPending} confirmFailure={failure} onConfirm={(fp) => void confirmFingerprint(fp)} onRetry={onRetry}>
      {children}
    </InstallSessionView>
  );
}
