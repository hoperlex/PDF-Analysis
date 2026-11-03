/**
 * The pieces of the lifecycle panel that are views of the data alone (`EXEC2-WEB-WIZARD-01`): one row
 * of the path, the list of official clients with their login, and the two blocks of guidance a person
 * needs when a client is missing or not signed in.
 *
 * None of them holds state or sends a command; the panel (`agent-lifecycle-panel.tsx`) composes them
 * and owns the actions. The official login commands are shown in a copy box and are never composed
 * into a sentence (`R-149b`): the person signs in as the agent's service user, on their own device,
 * through the client's documented flow, and nothing is entered into this application.
 */

import type { ReactNode } from 'react';

import type { RunnerCliName } from '@/shared/api';

import type { AgentLifecycle, AgentStepId, AgentStepState, CliReading } from '../model/lifecycle';
import { stepSentence } from '../model/step-sentences';
import {
  CLI_AUTH_LABELS,
  LOGIN_COMMANDS,
  LOGIN_COMMAND_LABEL,
  LOGIN_GUIDANCE_TEXT,
  LOGIN_GUIDANCE_TITLE,
  MISSING_CLI_TEXT,
  MISSING_CLI_TITLE,
  RECHECK_HINT,
  RECHECK_LABEL,
  STEP_LABELS,
  STEP_STATE_LABELS,
  UNKNOWN_LOGIN_TEXT,
} from '../model/words';
import { CopyBox } from './copy-box';
import styles from './connect-remote-agent.module.css';

const TONE: Readonly<Record<AgentStepState, string>> = {
  done: 'ok',
  waiting: 'pending',
  attention: 'failed',
  inert: 'inert',
};

/** The name of an official client: a product name for one, the command's own name for the other. */
export function CliName({ cli }: { readonly cli: RunnerCliName }) {
  return cli === 'claude' ? <>Claude Code</> : <code>{cli}</code>;
}

export interface StepRowProps {
  readonly lifecycle: AgentLifecycle;
  readonly id: AgentStepId;
  readonly children?: ReactNode | undefined;
}

export function StepRow({ lifecycle, id, children }: StepRowProps) {
  const step = lifecycle.steps[id];
  return (
    <li
      className={styles.step}
      data-agent-step={id}
      data-agent-step-state={step.state}
      data-agent-step-reason={step.reason}
    >
      <span className={styles.stepHead}>
        <span className={`am-badge am-badge--${TONE[step.state]}`}>{STEP_STATE_LABELS[step.state]}</span>
        <strong>{STEP_LABELS[id]}</strong>
      </span>
      <p className="am-form__hint">{stepSentence(lifecycle, id)}</p>
      {children}
    </li>
  );
}

/**
 * The clients the agent reported. `installed` lists every client with its version or «не найден»;
 * `login` lists only the installed ones, each with the state its own official mechanism reported.
 */
export function CliList({ clis, mode }: { readonly clis: readonly CliReading[]; readonly mode: 'installed' | 'login' }) {
  const shown = mode === 'login' ? clis.filter((item) => item.installed) : clis;
  if (shown.length === 0) return null;
  return (
    <ul className={styles.clis} aria-label={mode === 'installed' ? STEP_LABELS.installed : STEP_LABELS.login} data-agent-clis={mode}>
      {shown.map((item) => (
        <li
          key={item.cli}
          data-agent-cli={item.cli}
          data-agent-cli-installed={item.installed ? 'yes' : 'no'}
          data-agent-cli-auth={item.installed ? item.auth : 'none'}
        >
          <CliName cli={item.cli} />:{' '}
          {mode === 'installed'
            ? item.installed
              ? `найден${item.version === null ? '' : `, версия ${item.version}`}`
              : 'не найден'
            : CLI_AUTH_LABELS[item.auth]}
        </li>
      ))}
    </ul>
  );
}

export interface RecheckProps {
  readonly onRecheck: () => void;
}

function Recheck({ onRecheck }: RecheckProps) {
  return (
    <div className={styles.actions}>
      <button className="am-button am-button--quiet" type="button" data-agent-recheck onClick={onRecheck}>
        {RECHECK_LABEL}
      </button>
      <span className="am-form__hint">{RECHECK_HINT}</span>
    </div>
  );
}

/** No official client was found on the server. The agent installs none: the person does. */
export function MissingCliGuidance({ onRecheck }: RecheckProps) {
  return (
    <div role="group" aria-label={MISSING_CLI_TITLE} data-agent-missing-cli>
      <p className="am-note">{MISSING_CLI_TEXT}</p>
      <Recheck onRecheck={onRecheck} />
    </div>
  );
}

/**
 * A client is installed and its login is not valid (or cannot be read). Shows the official login
 * command of each such client, then «Проверить снова».
 */
export function LoginGuidance({ clis, onRecheck }: { readonly clis: readonly CliReading[]; readonly onRecheck: () => void }) {
  const open = clis.filter((item) => item.installed && item.auth !== 'valid');
  if (open.length === 0) return null;
  return (
    <div role="group" aria-label={LOGIN_GUIDANCE_TITLE} data-agent-login-guidance>
      <p className="am-note">
        {LOGIN_GUIDANCE_TEXT}
        {open.some((item) => item.auth === 'unknown') ? ` ${UNKNOWN_LOGIN_TEXT}` : ''}
      </p>
      {open.map((item) => (
        <div key={item.cli} data-agent-login-command={item.cli}>
          <p>
            <CliName cli={item.cli} />: {CLI_AUTH_LABELS[item.auth]}
          </p>
          <CopyBox value={LOGIN_COMMANDS[item.cli]} label={LOGIN_COMMAND_LABEL} variant="line" name={`login-${item.cli}`} />
        </div>
      ))}
      <Recheck onRecheck={onRecheck} />
    </div>
  );
}
