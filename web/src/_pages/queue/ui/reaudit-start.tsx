'use client';

/**
 * What the queue draws while a repeated Run is being started (`RUN-START-ONE-01b`, plan v3 §8). The step comes from
 * `../model/reaudit-start.ts`; the sequence (read, agree, send) is the page's.
 *
 * An estimate that charges nothing is agreed to by the click on «Повторный аудит», so the only things drawn on its way
 * are the line while it is read and the line while it is sent: no panel, no tick-box, no second press. An estimate that
 * can charge opens ONE dialog, the same one the start control opens (`@/features/start-run`), with «Запустить» and
 * «Отмена»; its subject names the Run that is repeated.
 */

import type { RunCostEstimate } from '@/shared/api';
import { StartRunCostDialog } from '@/features/start-run';
import { ErrorState, LoadingState } from '@/shared/ui';
import type { ExecutionFailure } from '@/entities/execution';

import type { ReauditStep } from '../model/reaudit-start';
import styles from './queue-page.module.css';

export interface ReauditStartProps {
  readonly step: ReauditStep;
  readonly runId: string;
  /** The estimate and its ceiling, for the `ask` step. */
  readonly estimate: RunCostEstimate | null;
  readonly ceiling: string;
  /** The estimate changed since the person last saw one. */
  readonly changed: boolean;
  /** A command is in flight. */
  readonly busy: boolean;
  /** Why the estimate could not be read (`unreadable`), or why the send failed (`failed`). */
  readonly failure: ExecutionFailure | null;
  readonly onCeilingChange: (value: string) => void;
  /** The dialog's «Запустить». */
  readonly onConfirm: () => void;
  /** «Отмена», in every step in which something can still be left. */
  readonly onCancel: () => void;
  /** Read the estimate again (`unreadable`). */
  readonly onReadAgain: () => void;
  /** Send again under the same key (`failed` with an unknown outcome). */
  readonly onRetry: () => void;
}

export function ReauditStart({
  step, runId, estimate, ceiling, changed, busy, failure, onCeilingChange, onConfirm, onCancel, onReadAgain, onRetry,
}: ReauditStartProps) {
  switch (step) {
    case 'reading':
      return (
        <div data-reaudit-reading="">
          <LoadingState what="стоимость повторного аудита" />
          <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={onCancel}>Отмена</button>
        </div>
      );
    case 'send':
      return <div data-reaudit-sending=""><LoadingState what="запрос на повторный прогон" /></div>;
    case 'ask':
      return estimate === null ? null : (
        <StartRunCostDialog
          estimate={estimate}
          relaxed={false}
          ceiling={ceiling}
          changed={changed}
          busy={busy}
          subject={`Повторный аудит прогона ${runId}.`}
          onCeilingChange={onCeilingChange}
          onConfirm={onConfirm}
          onCancel={onCancel}
        />
      );
    case 'unreadable':
      return (
        <section className={styles.intent} role="group" aria-label="Повторный аудит" data-execution-intent="reaudit">
          {failure === null ? null : (
            <ErrorState title="Стоимость повторного аудита не оценена" detail={failure.detail} correlationId={failure.correlationId} />
          )}
          <button type="button" className="am-button" disabled={busy} onClick={onReadAgain}>Оценить снова</button>{' '}
          <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={onCancel}>Отмена</button>
        </section>
      );
    case 'failed':
      return (
        <section className={styles.intent} role="group" aria-label="Повторный аудит" data-execution-intent="reaudit">
          {failure?.kind === 'unknown_outcome' ? (
            <button type="button" className="am-button" disabled={busy} onClick={onRetry}>Повторить с тем же ключом</button>
          ) : null}{' '}
          <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={onCancel}>Отмена</button>
        </section>
      );
  }
}
