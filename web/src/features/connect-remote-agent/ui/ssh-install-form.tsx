'use client';

/**
 * Path A, the first screen (`EXEC2-WEB-WIZARD-01`, ADR-0026 decision 7): where the stand installs the
 * agent. The form asks for a host, a port and a user, and for nothing else.
 *
 * **No secret is asked for, anywhere.** There is no password field and no private-key field. The one
 * way in the wizard offers is a key the stand makes itself: the private half stays on the stand and
 * the administrator adds the public line the session then shows. This is the secret-door rule of the
 * application (`features/set-executor-secret`): a secret is never a value of client code, so a pasted
 * private key does not travel through this browser. The fixed access is printed, not chosen.
 *
 * The form sends nothing itself: it hands the posted form to `onSubmit`, and the run component above
 * it creates the connection if there is none, starts the install and shows the session.
 */

import type { FormEvent } from 'react';

import type { ExecutionFailure } from '@/entities/execution';
import { CommandFailure, FIELD_NAMES, SSH_PORT_DEFAULT } from '@/features/manage-executor-connection';

import {
  SSH_ACCESS_FORM_TEXT,
  SSH_ACCESS_FORM_TITLE,
  SSH_ACCESS_LEGEND,
  SSH_FORM_INTRO,
  SSH_FORM_TITLE,
  SSH_HOST_LABEL,
  SSH_PORT_LABEL,
  SSH_PRIVATE_RANGE_HINT,
  SSH_SUBMIT_LABEL,
  SSH_USER_LABEL,
  WIZARD_BACK_LABEL,
} from '../model/words';
import styles from './connect-remote-agent.module.css';

export interface SshInstallFormProps {
  readonly pending: boolean;
  /** A problem with what was typed, to fix before pressing again. */
  readonly problem: string | null;
  /** A refusal or an unknown outcome of the command itself. */
  readonly failure: ExecutionFailure | null;
  readonly onSubmit: (form: FormData) => void;
  readonly onBack: () => void;
}

export function SshInstallForm({ pending, problem, failure, onSubmit, onBack }: SshInstallFormProps) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(new FormData(event.currentTarget));
  }

  return (
    <form className={`am-form am-form--two ${styles.form}`} onSubmit={submit} data-agent-ssh-form>
      <h3>{SSH_FORM_TITLE}</h3>
      <p className="am-form__hint">{SSH_FORM_INTRO}</p>
      <details className={styles.fold}>
        <summary>Если сервер в частной сети</summary>
        <p className="am-form__hint" data-agent-private-range-hint>{SSH_PRIVATE_RANGE_HINT}</p>
      </details>
      <div className="am-form__field am-form__field--wide">
        <label htmlFor="agent-ssh-host">{SSH_HOST_LABEL}</label>
        <input id="agent-ssh-host" name={FIELD_NAMES.sshHost} type="text" required maxLength={253} autoComplete="off" spellCheck={false} />
      </div>
      <div className="am-form__field">
        <label htmlFor="agent-ssh-port">{SSH_PORT_LABEL}</label>
        <input id="agent-ssh-port" name={FIELD_NAMES.sshPort} type="number" required min={1} max={65535} defaultValue={SSH_PORT_DEFAULT} />
      </div>
      <div className="am-form__field">
        <label htmlFor="agent-ssh-user">{SSH_USER_LABEL}</label>
        <input id="agent-ssh-user" name={FIELD_NAMES.sshUser} type="text" required maxLength={64} autoComplete="off" spellCheck={false} />
      </div>
      <div className="am-note" role="group" aria-label={SSH_ACCESS_LEGEND} data-agent-access="generated_key">
        <strong>{SSH_ACCESS_FORM_TITLE}</strong>
        <p className="am-form__hint">{SSH_ACCESS_FORM_TEXT}</p>
      </div>
      {problem !== null ? <p className="am-form__problem" role="alert" data-agent-problem>{problem}</p> : null}
      <div className="am-form__row">
        <button className="am-button" type="submit" disabled={pending} data-agent-ssh-submit>{SSH_SUBMIT_LABEL}</button>
        <button className="am-button am-button--quiet" type="button" disabled={pending} onClick={onBack}>{WIZARD_BACK_LABEL}</button>
      </div>
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </form>
  );
}
