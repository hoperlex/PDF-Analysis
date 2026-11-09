'use client';

/**
 * Path B (`EXEC2-WEB-WIZARD-01`, ADR-0026 decisions 4 and 6): the one command that installs the agent.
 *
 * **The command is shown once.** The stand keeps only a one-way hash of the grant's secret, so no
 * screen and no operation can show the command again. It lives in this component's state from the
 * moment it is issued until the person closes the box (the mutation keeps no copy, `gcTime: 0`, and
 * is reset at once), and nowhere else: not in the address, not in a storage, not in a log. Closing
 * the box drops it, and the box says so before it is closed.
 *
 * **«Новая команда» replaces, it does not add.** A new grant revokes the previous unredeemed one, so
 * only the command on the screen works; the box says that too. Every press is a new intent with a new
 * idempotency key: a repeat of the same key is answered `enrollment_shown_once`, since the secret was
 * not stored and cannot be shown again, so a key is never held for a repeat. After an unknown outcome
 * the person presses «Новая команда» again, which is safe for the reason above.
 *
 * `EnrollmentCommandView` is a view driven by props; `EnrollmentCommandControl` issues the command
 * and holds it for one reading.
 */

import { useReducer, useState } from 'react';

import type { ExecutorConnectionId, IssuedExecutorEnrollment } from '@/shared/api';
import { newIdempotencyKey } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { formatInstant } from '@/shared/lib';
import { CommandFailure, useIssueExecutorEnrollment } from '@/features/manage-executor-connection';

import { EMPTY_COMMAND_BOX, commandBoxReducer } from '../model/command-box';
import { agentFailure } from '../model/failure';
import {
  COMMAND_CLOSE_LABEL,
  COMMAND_FIELD_LABEL,
  COMMAND_NEW_HINT,
  COMMAND_NEW_LABEL,
  COMMAND_NEW_NOTE,
  COMMAND_NO_SECRET_NOTE,
  COMMAND_SHOWN_ONCE,
  COMMAND_SHOWN_TITLE,
} from '../model/words';
import { CopyBox } from './copy-box';
import styles from './connect-remote-agent.module.css';

export interface EnrollmentCommandViewProps {
  readonly issued: IssuedExecutorEnrollment;
  /** This command replaced an earlier one that was shown in the same box. */
  readonly replaced: boolean;
  readonly pending: boolean;
  readonly failure: ExecutionFailure | null;
  readonly onNewCommand: () => void;
  readonly onClose: () => void;
}

export function EnrollmentCommandView({
  issued, replaced, pending, failure, onNewCommand, onClose,
}: EnrollmentCommandViewProps) {
  return (
    <section role="group" aria-label={COMMAND_SHOWN_TITLE} data-agent-command-shown data-agent-command-replaced={replaced ? 'yes' : 'no'}>
      <p className="am-note" role="alert" data-agent-command-once>
        <strong>{COMMAND_SHOWN_ONCE}</strong>
      </p>
      {replaced ? <p className="am-note" role="status" data-agent-command-new-note>{COMMAND_NEW_NOTE}</p> : null}
      <CopyBox value={issued.command} label={COMMAND_FIELD_LABEL} variant="block" name="enrollment-command" />
      <p className="am-form__hint">
        Действует до <time dateTime={issued.enrollment.expires_at}>{formatInstant(issued.enrollment.expires_at)}</time>{' '}
        и только один раз.
      </p>
      <details className={styles.fold}>
        <summary>Версия пакета и проверка</summary>
        <p className="am-form__hint">
          Версия пакета агента <code>{issued.package_version}</code>, контрольная сумма
          SHA-256 <code>{issued.package_sha256}</code> проверяется самой командой.
        </p>
        <p className="am-form__hint">{COMMAND_NO_SECRET_NOTE}</p>
      </details>
      <div className="am-form__row">
        <button className="am-button am-button--quiet" type="button" disabled={pending} data-agent-command-new onClick={onNewCommand}>
          {COMMAND_NEW_LABEL}
        </button>
        <button className="am-button" type="button" data-agent-command-close onClick={onClose}>{COMMAND_CLOSE_LABEL}</button>
        <span className="am-form__hint">{COMMAND_NEW_HINT}</span>
      </div>
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </section>
  );
}

export interface EnrollmentCommandControlProps {
  /**
   * Makes sure the connection exists and returns its id: the wizard creates the connection here, a
   * card returns its own at once. Only the id leaves this component's parent; the command never does.
   */
  readonly resolveConnection: () => Promise<ExecutorConnectionId>;
  /** The label of the button that issues the first command. After one was shown it reads «Новая команда». */
  readonly startLabel: string;
  /** Told the connection's id once it exists, so the parent can show the agent's progress. */
  readonly onConnection?: ((connectionId: ExecutorConnectionId) => void) | undefined;
}

export function EnrollmentCommandControl({ resolveConnection, startLabel, onConnection }: EnrollmentCommandControlProps) {
  const issue = useIssueExecutorEnrollment();
  // The command lives in this reducer's state and nowhere else (`model/command-box.ts`).
  const [box, dispatch] = useReducer(commandBoxReducer, EMPTY_COMMAND_BOX);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function press() {
    setFailure(null);
    setPending(true);
    try {
      let connectionId: ExecutorConnectionId;
      try {
        connectionId = await resolveConnection();
      } catch (error) {
        // Nothing was issued: the sentence is the connection's own, not the one for a lost command.
        setFailure(agentFailure(error, true));
        return;
      }
      onConnection?.(connectionId);
      try {
        // Always a new key: the same key would be answered `enrollment_shown_once`.
        const next = await issue.mutateAsync({ connectionId, idempotencyKey: newIdempotencyKey() });
        dispatch({ type: 'issued', issued: next });
      } catch (error) {
        setFailure(agentFailure(error, true, true));
      }
    } finally {
      issue.reset();
      setPending(false);
    }
  }

  function close() {
    // The value is dropped here and nowhere else holds it.
    dispatch({ type: 'closed' });
    setFailure(null);
  }

  if (box.issued !== null) {
    return (
      <EnrollmentCommandView
        issued={box.issued}
        replaced={box.replaced}
        pending={pending}
        failure={failure}
        onNewCommand={() => void press()}
        onClose={close}
      />
    );
  }
  return (
    <>
      <button className="am-button" type="button" disabled={pending} data-agent-command-start onClick={() => void press()}>
        {box.everShown ? COMMAND_NEW_LABEL : startLabel}
      </button>
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </>
  );
}
