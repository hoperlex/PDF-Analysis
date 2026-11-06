'use client';

/**
 * The queue's pause state in the frame's top strip (`R-151f`, `UI-PARITY-P0E`).
 *
 * The original keeps «Пауза/Продолжить» in its header. Ours shows the state to everyone the queue is
 * open to (`expert`, `admin`; `viewer` never reads it, `R-150w`) and offers the switch to those who may
 * pause (`canExecute(roles, 'pause')`, an administrator). The original's «interrupt now» mode is not
 * here: it is a later contract.
 *
 * {@link PauseStatusView} is pure markup; {@link PauseStatus} connects it to `getExecutionDispatch`,
 * the account's roles and `setExecutionPaused`. A pause is confirmed in place, never by a native
 * `confirm`, and one idempotency key serves one intent and its retries.
 */

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';

import type { ExecutionDispatchStatus } from '@/shared/api';
import { failureMessage, newIdempotencyKey } from '@/shared/api';
import { routes } from '@/shared/lib';
import { useMe } from '@/entities/account';
import { canExecute, useExecutionDispatch } from '@/entities/execution';
import { usePauseExecution } from '@/features/pause-execution';

import styles from './pause-status.module.css';

export const PAUSED_LABEL = 'Выдача приостановлена';
export const UNREAD_LABEL = 'Состояние выдачи не прочитано';

export interface PauseStatusViewProps {
  /** The pause state, or `undefined` before the first read settles. */
  readonly status: ExecutionDispatchStatus | undefined;
  /** The latest read failed. */
  readonly failed: boolean;
  /** Whether this session may pause and resume. */
  readonly mayToggle: boolean;
  /** The pending confirmation, if the switch was pressed. */
  readonly asking: boolean;
  /** A command is on its way. */
  readonly busy: boolean;
  /** Why the last command was refused, worded for a person. */
  readonly error: string | null;
  readonly onAsk: () => void;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

function sinceLabel(changedAt: string): string {
  const at = new Date(changedAt);
  if (Number.isNaN(at.getTime())) return '';
  return `с ${at.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
}

export function PauseStatusView({
  status, failed, mayToggle, asking, busy, error, onAsk, onConfirm, onCancel,
}: PauseStatusViewProps) {
  if (status === undefined) {
    return failed ? (
      <span className={styles.status} role="status" data-pause-status="unread">
        <span className="am-badge am-badge--inert">{UNREAD_LABEL}</span>
      </span>
    ) : null;
  }
  const paused = status.paused;
  if (!paused && !mayToggle) return null;
  const question = paused ? 'Возобновить выдачу задач?' : 'Приостановить выдачу задач?';
  return (
    <span className={styles.status} data-pause-status={paused ? 'paused' : 'running'}>
      {paused ? (
        <Link className={styles.link} href={routes.queue()} title={sinceLabel(status.changed_at)}>
          <span className="am-badge am-badge--pending" role="status">{PAUSED_LABEL}</span>
        </Link>
      ) : null}
      {mayToggle && !asking ? (
        <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={onAsk}>
          {paused ? 'Возобновить' : 'Пауза'}
        </button>
      ) : null}
      {mayToggle && asking ? (
        <span className={styles.confirm} role="group" aria-label={question}>
          <span className={styles.question}>{question}</span>
          <button type="button" className="am-button" disabled={busy} onClick={onConfirm}>
            {paused ? 'Возобновить' : 'Приостановить'}
          </button>
          <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={onCancel}>
            Отмена
          </button>
        </span>
      ) : null}
      {error !== null ? <span className={styles.error} role="alert">{error}</span> : null}
    </span>
  );
}

/**
 * The indicator as the frame mounts it: nothing until the client has mounted (a server render and the
 * style census have no query client, and the state is not known there anyway), then
 * {@link PauseStatusLive}. Mount it only for a session the queue is open to.
 */
export function PauseStatus() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? <PauseStatusLive /> : null;
}

/** The connected indicator: the pause state, the account's roles and the switch. */
export function PauseStatusLive() {
  const dispatch = useExecutionDispatch();
  const account = useMe();
  const pause = usePauseExecution();
  const [asking, setAsking] = useState(false);
  const intent = useRef<{ readonly paused: boolean; readonly key: string } | null>(null);
  const roles = account.data?.roles ?? [];

  function confirm() {
    const status = dispatch.data;
    if (status === undefined) return;
    const target = !status.paused;
    if (intent.current === null || intent.current.paused !== target) {
      intent.current = { paused: target, key: newIdempotencyKey() };
    }
    pause.mutate(
      { paused: target, idempotencyKey: intent.current.key },
      { onSuccess: () => { intent.current = null; setAsking(false); } },
    );
  }

  return (
    <PauseStatusView
      status={dispatch.data}
      failed={dispatch.isError}
      mayToggle={account.data !== undefined && canExecute(roles, 'pause')}
      asking={asking}
      busy={pause.isPending}
      error={pause.isError ? failureMessage(pause.error).detail : null}
      onAsk={() => { pause.reset(); setAsking(true); }}
      onConfirm={confirm}
      onCancel={() => { pause.reset(); intent.current = null; setAsking(false); }}
    />
  );
}
