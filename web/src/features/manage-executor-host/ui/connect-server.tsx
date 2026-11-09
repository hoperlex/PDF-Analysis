'use client';

/**
 * «Подключить сервер» (`HOSTS-WEB-01`, plan 2026-11-09 §7.3): one window with two ways in, and **no model is ever asked**.
 *
 *   «Командой в терминале»  a name, then one line to run on the server, «Скопировать», and a live status: «ждём сервер…» →
 *                           «найдено: Opus 5.5, Sonnet 5.5»;
 *   «По SSH»                a host and a user (the port is under «Дополнительно»); the stand makes the key, shows the line
 *                           for `authorized_keys`, then the fingerprint to confirm, then three steps of progress.
 *
 * **What the window never holds.** The line carries a one-time secret that the stand stores only as a hash and shows once. It
 * lives in this component's state from the moment it is issued until the window is closed, and nowhere else: not in the
 * address, not in a storage, not in a log. A pasted private key does not pass through this window at all: a secret is never a
 * value of client code in this application.
 *
 * The window is a native modal `<dialog>`: the browser keeps the focus inside, Esc closes it and the screen behind is inert.
 * Closing unmounts it, which drops the line. The one-line `D-291` warning is in it while the debt is open.
 */

import { useEffect, useReducer, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent, ReactNode } from 'react';

import type { ExecutorAgentInstall, ExecutorHostId, IssuedExecutorEnrollment } from '@/shared/api';
import { newIdempotencyKey } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { CLIENT_DOCUMENTS_LINE, hostFailure } from '@/entities/executor-host';
import { EMPTY_COMMAND_BOX, CopyBox, commandBoxReducer } from '@/features/connect-remote-agent';
import { useCommandKey } from '@/features/manage-executor-connection';
import { formatInstant } from '@/shared/lib';

import { arrivalOf } from '../model/arrival';
import type { Arrival } from '../model/arrival';
import { useArrival } from '../model/use-arrival';
import {
  COMMAND_FIELD,
  COMMAND_GET_LABEL,
  COMMAND_INTRO,
  COMMAND_NEW_LABEL,
  COMMAND_NEW_NOTE,
  COMMAND_ONCE,
  COMMAND_SECRET_NOTE,
  CONNECT_CLOSE_LABEL,
  CONNECT_LABEL,
  CONNECT_TABS_LABEL,
  CONNECT_TITLE,
  NAME_HINT,
  NAME_LABEL,
  SSH_ADVANCED,
  SSH_HOST_LABEL,
  SSH_INTRO,
  SSH_KEY_NOTE,
  SSH_NEEDS_HOST,
  SSH_PORT_LABEL,
  SSH_PORT_PROBLEM,
  SSH_START_LABEL,
  SSH_USER_LABEL,
  TAB_COMMAND,
  TAB_SSH,
} from '../model/words';
import { useCreateExecutorHostAgentInstall, useIssueExecutorHostEnrollment } from '../model/use-manage-executor-host';
import { HostFailure } from './host-failure';
import { InstallSession } from './install-session';
import styles from './manage-executor-host.module.css';

export type ConnectTab = 'command' | 'ssh';
const TABS: readonly ConnectTab[] = ['command', 'ssh'];
const TAB_LABELS: Readonly<Record<ConnectTab, string>> = { command: TAB_COMMAND, ssh: TAB_SSH };

// ---------------------------------------------------------------------------------------- the status line

export function ArrivalStatus({ arrival }: { readonly arrival: Arrival }) {
  return (
    <p className={styles.status} role="status" data-host-arrival={arrival.arrived ? 'found' : 'waiting'}>
      {arrival.text}
    </p>
  );
}

function ArrivalOfHost({ hostId }: { readonly hostId: ExecutorHostId }) {
  return <ArrivalStatus arrival={useArrival(hostId)} />;
}

// ---------------------------------------------------------------------------------------- the command tab

export interface CommandTabViewProps {
  readonly name: string;
  readonly pending: boolean;
  readonly issued: IssuedExecutorEnrollment | null;
  readonly replaced: boolean;
  readonly failure: ExecutionFailure | null;
  readonly problem: string | null;
  readonly onName: (value: string) => void;
  readonly onGet: () => void;
  /** The status of the server the line was issued for. */
  readonly status: ReactNode;
}

export function CommandTabView({ name, pending, issued, replaced, failure, problem, onName, onGet, status }: CommandTabViewProps) {
  return (
    <div data-connect-panel="command">
      {issued === null ? (
        <form className="am-form" onSubmit={(event: FormEvent) => { event.preventDefault(); onGet(); }}>
          <div className="am-form__field">
            <label htmlFor="connect-name">{NAME_LABEL}</label>
            <input id="connect-name" name="display_name" type="text" required maxLength={120} autoComplete="off" value={name} onChange={(event) => onName(event.currentTarget.value)} />
            <span className="am-form__hint">{NAME_HINT}</span>
          </div>
          {problem === null ? null : <p className="am-form__problem" role="alert">{problem}</p>}
          <button className="am-button" type="submit" disabled={pending} data-connect-get>{COMMAND_GET_LABEL}</button>
        </form>
      ) : (
        <section role="group" aria-label={COMMAND_FIELD} data-connect-command-shown data-connect-command-replaced={replaced ? 'yes' : 'no'}>
          <p>{COMMAND_INTRO}</p>
          <CopyBox value={issued.command} label={COMMAND_FIELD} variant="line" name="host-command" />
          <p className="am-note" role="alert" data-connect-command-once>{COMMAND_ONCE}</p>
          <p className="am-form__hint">
            Действует до <time dateTime={issued.enrollment.expires_at}>{formatInstant(issued.enrollment.expires_at)}</time>.
          </p>
          {replaced ? <p className="am-note" role="status">{COMMAND_NEW_NOTE}</p> : null}
          <details className={styles.fold}>
            <summary>Пакет агента</summary>
            <p className="am-form__hint">
              Версия <code>{issued.package_version}</code>, контрольная сумма SHA-256 <code>{issued.package_sha256}</code> проверяется самой командой.
            </p>
            <p className="am-form__hint">{COMMAND_SECRET_NOTE}</p>
          </details>
          {status}
          <button className="am-button am-button--quiet" type="button" disabled={pending} data-connect-new onClick={onGet}>{COMMAND_NEW_LABEL}</button>
        </section>
      )}
      {failure === null ? null : <HostFailure failure={failure} />}
    </div>
  );
}

function CommandTab() {
  const issue = useIssueExecutorHostEnrollment();
  const [box, dispatch] = useReducer(commandBoxReducer, EMPTY_COMMAND_BOX);
  const [name, setName] = useState('');
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function get() {
    const trimmed = name.trim();
    if (trimmed === '') {
      setProblem('Укажите название сервера.');
      return;
    }
    setProblem(null);
    setFailure(null);
    try {
      // Always a new key: the same key would be answered `enrollment_shown_once`, since the secret was not stored.
      dispatch({ type: 'issued', issued: await issue.mutateAsync({ displayName: trimmed, idempotencyKey: newIdempotencyKey() }) });
    } catch (error) {
      setFailure(hostFailure(error, true, true));
    } finally {
      issue.reset();
    }
  }

  const hostId = box.issued?.enrollment.host_id ?? null;
  return (
    <CommandTabView
      name={name}
      pending={issue.isPending}
      issued={box.issued}
      replaced={box.replaced}
      failure={failure}
      problem={problem}
      onName={setName}
      onGet={() => void get()}
      status={hostId === null ? null : <ArrivalOfHost hostId={hostId} />}
    />
  );
}

// ---------------------------------------------------------------------------------------- the SSH tab

export interface SshFormViewProps {
  readonly pending: boolean;
  readonly problem: string | null;
  readonly failure: ExecutionFailure | null;
  readonly onSubmit: (form: FormData) => void;
}

export function SshFormView({ pending, problem, failure, onSubmit }: SshFormViewProps) {
  return (
    <form className="am-form" data-connect-panel="ssh" onSubmit={(event) => { event.preventDefault(); onSubmit(new FormData(event.currentTarget)); }}>
      <p>{SSH_INTRO}</p>
      <div className="am-form__field">
        <label htmlFor="connect-ssh-host">{SSH_HOST_LABEL}</label>
        <input id="connect-ssh-host" name="ssh_host" type="text" required maxLength={253} autoComplete="off" spellCheck={false} />
      </div>
      <div className="am-form__field">
        <label htmlFor="connect-ssh-user">{SSH_USER_LABEL}</label>
        <input id="connect-ssh-user" name="ssh_user" type="text" required maxLength={64} autoComplete="off" spellCheck={false} />
      </div>
      <details className={styles.fold}>
        <summary>{SSH_ADVANCED}</summary>
        <div className="am-form__field">
          <label htmlFor="connect-ssh-port">{SSH_PORT_LABEL}</label>
          <input id="connect-ssh-port" name="ssh_port" type="number" min={1} max={65535} defaultValue={22} />
        </div>
        <p className="am-form__hint">{SSH_KEY_NOTE}</p>
      </details>
      {problem === null ? null : <p className="am-form__problem" role="alert">{problem}</p>}
      <button className="am-button" type="submit" disabled={pending} data-connect-ssh-start>{SSH_START_LABEL}</button>
      {failure === null ? null : <HostFailure failure={failure} />}
    </form>
  );
}

/** What the SSH form asks, read: a host and a user, a port. The access is always a key the stand makes; no model. */
export function readSshForm(form: FormData):
  | { readonly ok: true; readonly host: string; readonly user: string; readonly port: number }
  | { readonly ok: false; readonly problem: string } {
  const text = (name: string): string => {
    const value = form.get(name);
    return typeof value === 'string' ? value.trim() : '';
  };
  const host = text('ssh_host');
  const user = text('ssh_user');
  if (host === '' || user === '') return { ok: false, problem: SSH_NEEDS_HOST };
  const port = Number(text('ssh_port') === '' ? '22' : text('ssh_port'));
  if (!Number.isInteger(port) || port < 1 || port > 65535) return { ok: false, problem: SSH_PORT_PROBLEM };
  return { ok: true, host, user, port };
}

function SshTab() {
  const create = useCreateExecutorHostAgentInstall();
  const keys = useCommandKey();
  const [install, setInstall] = useState<ExecutorAgentInstall | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function start(form: FormData) {
    const read = readSshForm(form);
    if (!read.ok) {
      setProblem(read.problem);
      return;
    }
    setProblem(null);
    setFailure(null);
    try {
      // The server is named after its host: the person is asked nothing that the host already says.
      const made = await create.mutateAsync({
        displayName: read.host, sshHost: read.host, sshPort: read.port, sshUser: read.user, access: 'generated_key',
        idempotencyKey: keys.keyFor(JSON.stringify([read.host, read.port, read.user])),
      });
      keys.release();
      setInstall(made);
    } catch (error) {
      const failed = hostFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  if (install !== null && install.host_id !== undefined) {
    return (
      <div data-connect-panel="ssh">
        <InstallSession hostId={install.host_id} initial={install} onRetry={() => setInstall(null)}>
          <ArrivalOfHost hostId={install.host_id} />
        </InstallSession>
      </div>
    );
  }
  return <SshFormView pending={create.isPending} problem={problem} failure={failure} onSubmit={(form) => void start(form)} />;
}

// ---------------------------------------------------------------------------------------- the window

export interface ConnectWindowViewProps {
  readonly tab: ConnectTab;
  readonly onTab: (tab: ConnectTab) => void;
  readonly onClose: () => void;
  readonly children: ReactNode;
}

export function ConnectWindowView({ tab, onTab, onClose, children }: ConnectWindowViewProps) {
  const buttons = useRef<Partial<Record<ConnectTab, HTMLButtonElement | null>>>({});
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
    event.preventDefault();
    const next = tab === 'command' ? 'ssh' : 'command';
    onTab(next);
    buttons.current[next]?.focus();
  };
  return (
    <div data-connect-window>
      <div className={styles.header}>
        <h2 className={styles.title}>{CONNECT_TITLE}</h2>
        <button className="am-button am-button--quiet am-button--small" type="button" data-connect-close onClick={onClose}>{CONNECT_CLOSE_LABEL}</button>
      </div>
      <p className="am-note" data-connect-notice="client-documents">{CLIENT_DOCUMENTS_LINE}</p>
      <div role="tablist" aria-label={CONNECT_TABS_LABEL} className={styles.tablist}>
        {TABS.map((id) => (
          <button
            key={id}
            ref={(element) => { buttons.current[id] = element; }}
            type="button"
            role="tab"
            id={`connect-tab-${id}`}
            aria-selected={id === tab}
            aria-controls="connect-panel"
            tabIndex={id === tab ? 0 : -1}
            className={styles.tab}
            data-connect-tab={id}
            onClick={() => onTab(id)}
            onKeyDown={onKeyDown}
          >
            {TAB_LABELS[id]}
          </button>
        ))}
      </div>
      <div role="tabpanel" id="connect-panel" aria-labelledby={`connect-tab-${tab}`} className={styles.panel}>
        {children}
      </div>
    </div>
  );
}

export interface ConnectWindowProps {
  readonly onClose: () => void;
  /** A static render opens the dialog at once; the browser opens it with `showModal`. */
  readonly staticOpen?: boolean | undefined;
  readonly initialTab?: ConnectTab | undefined;
}

export function ConnectWindow({ onClose, staticOpen = false, initialTab = 'command' }: ConnectWindowProps) {
  const dialog = useRef<HTMLDialogElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const [tab, setTab] = useState<ConnectTab>(initialTab);

  useEffect(() => {
    const element = dialog.current;
    if (element === null || typeof element.showModal !== 'function') return;
    if (!element.open) element.showModal();
    const closed = () => closeRef.current();
    element.addEventListener('close', closed);
    return () => {
      element.removeEventListener('close', closed);
      if (element.open) element.close();
    };
  }, []);

  return (
    <dialog ref={dialog} className={styles.window} aria-label={CONNECT_TITLE} open={staticOpen ? true : undefined} data-connect-dialog>
      <ConnectWindowView tab={tab} onTab={setTab} onClose={onClose}>
        {tab === 'command' ? <CommandTab /> : <SshTab />}
      </ConnectWindowView>
    </dialog>
  );
}

/** The button «Подключить сервер» and the window it opens. Administrator only: the caller does not draw it for anyone else. */
export function ConnectServer() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="am-button" type="button" data-connect-open onClick={() => setOpen(true)}>{CONNECT_LABEL}</button>
      {open ? <ConnectWindow onClose={() => setOpen(false)} /> : null}
    </>
  );
}

export { arrivalOf };
