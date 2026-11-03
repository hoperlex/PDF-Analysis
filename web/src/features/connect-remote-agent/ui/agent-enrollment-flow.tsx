'use client';

/**
 * Installing the agent for one connection, by the path the person chose (`EXEC2-WEB-WIZARD-01`).
 *
 * The same component serves a **new** agent connection (the wizard) and an **existing** one (moving
 * the agent to another server): the only difference is `ensure`, which creates the connection first
 * in the wizard and returns the connection's id at once when it is moved. Both paths end in the same
 * enrollment and the same lifecycle.
 *
 * - **Path A, over SSH.** The form (`SshInstallForm`) → create the connection if there is none → start
 *   the install (`createExecutorAgentInstall`) → the session (`SshInstallSession`). A failed session
 *   offers «Повторить установку», which returns to the form and starts another install for **the same
 *   connection**; no second connection is made.
 * - **Path B, a command.** One button → create the connection if there is none → issue the grant →
 *   the command, shown once (`EnrollmentCommandControl`).
 *
 * Both show the line of the agent's progress under them; the full lifecycle is the card's.
 */

import { useState } from 'react';

import type { ExecutorAgentInstall, ExecutorConnectionId } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { useCommandKey, useCreateExecutorAgentInstall } from '@/features/manage-executor-connection';

import { installSignature, readInstall } from '../model/agent-settings';
import { agentFailure } from '../model/failure';
import { COMMAND_GET_LABEL, COMMAND_START_INTRO, COMMAND_START_TITLE, WIZARD_BACK_LABEL } from '../model/words';
import { AgentProgressLine } from './agent-progress-line';
import type { PathChoice } from './choices';
import { EnrollmentCommandControl } from './enrollment-command';
import { SshInstallForm } from './ssh-install-form';
import { SshInstallSession } from './ssh-install-session';

export interface AgentEnrollmentFlowProps {
  readonly path: PathChoice;
  /** Makes sure the connection exists and returns its id. */
  readonly ensure: () => Promise<ExecutorConnectionId>;
  readonly onBack: () => void;
}

function SshRun({ ensure, onBack }: Omit<AgentEnrollmentFlowProps, 'path'>) {
  const install = useCreateExecutorAgentInstall();
  const keys = useCommandKey();
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const [session, setSession] = useState<{ readonly connectionId: ExecutorConnectionId; readonly install: ExecutorAgentInstall } | null>(null);

  async function submit(form: FormData) {
    const reading = readInstall(form);
    if (!reading.ok) {
      setProblem(reading.problem);
      return;
    }
    setProblem(null);
    setFailure(null);
    setPending(true);
    try {
      const connectionId = await ensure();
      const made = await install.mutateAsync({
        connectionId,
        body: reading.body,
        idempotencyKey: keys.keyFor(installSignature(connectionId, reading.body)),
      });
      keys.release();
      setSession({ connectionId, install: made });
    } catch (error) {
      const failed = agentFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    } finally {
      setPending(false);
    }
  }

  if (session !== null) {
    return (
      <SshInstallSession
        connectionId={session.connectionId}
        initial={session.install}
        onRetry={() => { setSession(null); setFailure(null); setProblem(null); }}
      >
        <AgentProgressLine connectionId={session.connectionId} />
      </SshInstallSession>
    );
  }
  return (
    <SshInstallForm pending={pending} problem={problem} failure={failure} onSubmit={(form) => void submit(form)} onBack={onBack} />
  );
}

function CommandRun({ ensure, onBack }: Omit<AgentEnrollmentFlowProps, 'path'>) {
  // Only the connection's id is held here. The command itself lives in the control below and in
  // nothing else, so closing its box leaves no copy behind.
  const [connectionId, setConnectionId] = useState<ExecutorConnectionId | null>(null);
  return (
    <section className="am-form" aria-label={COMMAND_START_TITLE} data-agent-command-run>
      <h3>{COMMAND_START_TITLE}</h3>
      {connectionId === null ? <p className="am-form__hint">{COMMAND_START_INTRO}</p> : null}
      <EnrollmentCommandControl resolveConnection={ensure} startLabel={COMMAND_GET_LABEL} onConnection={setConnectionId} />
      {connectionId === null ? (
        <p>
          <button className="am-button am-button--quiet" type="button" onClick={onBack}>{WIZARD_BACK_LABEL}</button>
        </p>
      ) : (
        <AgentProgressLine connectionId={connectionId} />
      )}
    </section>
  );
}

export function AgentEnrollmentFlow({ path, ensure, onBack }: AgentEnrollmentFlowProps) {
  return path === 'ssh' ? <SshRun ensure={ensure} onBack={onBack} /> : <CommandRun ensure={ensure} onBack={onBack} />;
}
