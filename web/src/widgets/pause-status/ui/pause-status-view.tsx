'use client';

/**
 * The pause state in the frame's top strip, as pure markup (`R-151f`, `UI-PARITY-P0E`; one button, two items:
 * `ADR-0029` decision 8, plan «Прецеденты» §5).
 *
 * The strip carries ONE control, «Пауза», and it opens a menu of two items: «Выдача анализа» (the queue's pause) and
 * «Векторы» (the night encoder's pause). What is paused shows as a badge, and only while it is paused: «Выдача
 * приостановлена» and «Векторы на паузе». Nothing else of the vectors (the window, its state, the queued counts) is
 * drawn here: one pause, one badge.
 *
 * Who sees what: the badges are for everyone the queue is open to (`expert`, `admin`); the button is for those who may pause
 * (`mayToggle`, an administrator). A viewer never gets the strip (`offersPauseStatus`).
 *
 * The queue's pause is confirmed in place, as it always was (it stops every new run). The vectors' pause is not: it
 * stops nothing that runs, the intents keep queuing, and a second choice undoes it.
 */

import Link from 'next/link';
import type { ComponentType } from 'react';

import type { VectorsPause } from '@/entities/execution';
import { VECTORS_PAUSED_LABEL, vectorsPausedHint } from '@/entities/execution';
import type { ExecutionDispatchStatus } from '@/shared/api';
import { routes } from '@/shared/lib';
import type { MenuItem, MenuProps } from '@/shared/ui';
import { Menu } from '@/shared/ui';

import styles from './pause-status.module.css';

export const PAUSED_LABEL = 'Выдача приостановлена';
export const UNREAD_LABEL = 'Состояние выдачи не прочитано';

/** The one button. */
export const PAUSE_BUTTON_LABEL = 'Пауза';

/** What each menu item names, and what a choice does to it. */
export function dispatchItemLabel(paused: boolean): string {
  return `Выдача анализа — ${paused ? 'возобновить' : 'приостановить'}`;
}

export function vectorsItemLabel(vectors: VectorsPause): string {
  if (vectors.kind === 'unread') return 'Векторы — состояние не прочитано';
  return `Векторы — ${vectors.paused ? 'возобновить' : 'приостановить'}`;
}

export interface PauseStatusViewProps {
  /** The pause state, or `undefined` before the first read settles. */
  readonly status: ExecutionDispatchStatus | undefined;
  /** The latest read failed. */
  readonly failed: boolean;
  /** Whether this session may pause and resume. */
  readonly mayToggle: boolean;
  /** The pending confirmation of the queue's pause, if its item was chosen. */
  readonly asking: boolean;
  /** A command is on its way. */
  readonly busy: boolean;
  /** Why the last command was refused, worded for a person. */
  readonly error: string | null;
  /** The queue's item was chosen: ask before pausing or resuming. */
  readonly onAsk: () => void;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
  /** The vectors' pause; `undefined` while the first read is in flight (no badge, no item). */
  readonly vectors?: VectorsPause | undefined;
  /** The vectors' item was chosen: pause or resume them, at once. */
  readonly onToggleVectors?: (() => void) | undefined;
  /**
   * What draws the menu. In the shell it is `Menu`, which holds its own open state; an instrument that renders one
   * static pass cannot click, so it passes a view drawn open instead.
   */
  readonly menu?: ComponentType<MenuProps> | undefined;
}

function sinceLabel(changedAt: string | undefined): string {
  if (changedAt === undefined) return '';
  const at = new Date(changedAt);
  if (Number.isNaN(at.getTime())) return '';
  return `с ${at.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
}

/** The items of the one button's menu, in order: the queue, then the vectors (absent until their first read settles). */
export function pauseMenuProps(
  status: ExecutionDispatchStatus,
  vectors: VectorsPause | undefined,
  onAsk: () => void,
  onToggleVectors: (() => void) | undefined,
): MenuProps {
  const queue: MenuItem = { kind: 'action', label: dispatchItemLabel(status.paused), onChoose: onAsk };
  const rest: MenuItem[] = vectors === undefined ? [] : [{
    kind: 'action',
    label: vectorsItemLabel(vectors),
    // An unread state offers no switch: a switch would pick its direction from a state nobody read.
    ...(vectors.kind === 'read' ? { onChoose: onToggleVectors } : {}),
  }];
  return {
    label: PAUSE_BUTTON_LABEL,
    trigger: (
      <span className={styles.face}>
        {PAUSE_BUTTON_LABEL}
        <span className={styles.caret} aria-hidden="true">▾</span>
      </span>
    ),
    items: [queue, ...rest],
  };
}

export function PauseStatusView({
  status, failed, mayToggle, asking, busy, error, onAsk, onConfirm, onCancel, vectors, onToggleVectors, menu = Menu,
}: PauseStatusViewProps) {
  if (status === undefined) {
    return failed ? (
      <span className={styles.status} role="status" data-pause-status="unread">
        <span className="am-badge am-badge--inert">{UNREAD_LABEL}</span>
      </span>
    ) : null;
  }
  const paused = status.paused;
  const pausedVectors = vectors?.kind === 'read' && vectors.paused ? vectors : null;
  if (!paused && pausedVectors === null && !mayToggle) return null;
  const question = paused ? 'Возобновить выдачу задач?' : 'Приостановить выдачу задач?';
  const Drawn = menu;
  return (
    <span className={styles.status} data-pause-status={paused ? 'paused' : 'running'}>
      {paused ? (
        <Link className={styles.link} href={routes.queue()} title={sinceLabel(status.changed_at)}>
          <span className="am-badge am-badge--pending" role="status">{PAUSED_LABEL}</span>
        </Link>
      ) : null}
      {pausedVectors !== null ? (
        <span
          className="am-badge am-badge--pending"
          role="status"
          data-pause-vectors="paused"
          title={vectorsPausedHint(sinceLabel(pausedVectors.since))}
        >
          {VECTORS_PAUSED_LABEL}
        </span>
      ) : null}
      {mayToggle && !asking ? (
        <span className={styles.menu} data-pause-menu="">
          <Drawn {...pauseMenuProps(status, vectors, onAsk, onToggleVectors)} />
        </span>
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
