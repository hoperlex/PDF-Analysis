'use client';

/**
 * «Удалённый Ubuntu-агент» (`EXEC2-WEB-WIZARD-01`): a name and a model, then the two equal ways to
 * install the agent.
 *
 * The two cards are the same panel with the same button (`PathChoiceView`); choosing one validates
 * the name and the model, keeps them, and opens that path's screen (`AgentEnrollmentFlow`). Nothing is
 * created by choosing. The connection is made by the path's own button — «Начать установку» or
 * «Получить команду» — and only then, so a person who changes their mind leaves nothing behind. Going
 * back keeps what was typed; a connection that was already made is reused by the next attempt
 * (`useEnsureConnection`), whichever path it is.
 */

import { useRef, useState } from 'react';
import type { FormEvent } from 'react';

import type { ExecutorPinnedModel } from '@/shared/api';

import { agentRevisionRequest, readIdentity } from '../model/agent-settings';
import type { AgentIdentity } from '../model/agent-settings';
import { useEnsureConnection } from '../model/use-ensure-connection';
import {
  IDENTITY_BILLING_NOTE,
  IDENTITY_GATEWAY_HINT,
  IDENTITY_GATEWAY_LABEL,
  IDENTITY_MODEL_LABEL,
  IDENTITY_NAME_LABEL,
  IDENTITY_TITLE,
  KIND_CHOICES,
  NO_PINNED_MODELS,
  WIZARD_BACK_LABEL,
} from '../model/words';
import { AgentEnrollmentFlow } from './agent-enrollment-flow';
import { PathChoiceView } from './choices';
import type { PathChoice } from './choices';
import { IdentityFields } from './identity-fields';
import styles from './connect-remote-agent.module.css';

export interface AgentSetupProps {
  readonly pinnedModels: readonly ExecutorPinnedModel[];
  readonly onBack: () => void;
}

export function AgentSetup({ pinnedModels, onBack }: AgentSetupProps) {
  const connection = useEnsureConnection();
  const form = useRef<HTMLFormElement>(null);
  const [identity, setIdentity] = useState<AgentIdentity | undefined>(undefined);
  const [path, setPath] = useState<PathChoice | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  function choose(next: PathChoice) {
    if (form.current === null) return;
    const reading = readIdentity(new FormData(form.current), pinnedModels);
    if (!reading.ok) {
      setProblem(reading.problem);
      return;
    }
    setProblem(null);
    setIdentity(reading.identity);
    setPath(next);
  }

  function ignore(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
  }

  if (path !== null && identity !== undefined) {
    return (
      <section className={styles.group} aria-label={KIND_CHOICES.agent.title} data-wizard-step="agent-flow" data-agent-path-chosen={path}>
        <p className="am-form__hint">
          Подключение «{identity.displayName}», модель <code>{identity.pinId}</code>.
        </p>
        <AgentEnrollmentFlow
          path={path}
          ensure={() => connection.ensure({ kind: 'pull', displayName: identity.displayName, body: agentRevisionRequest(identity) })}
          onBack={() => setPath(null)}
        />
      </section>
    );
  }

  return (
    <section className={styles.group} aria-label={KIND_CHOICES.agent.title} data-wizard-step="agent">
      <h3>{KIND_CHOICES.agent.title}</h3>
      {pinnedModels.length === 0 ? (
        <p className="am-note" role="status" data-agent-no-models>{NO_PINNED_MODELS}</p>
      ) : (
        <>
          <form className={`am-form am-form--two ${styles.form}`} ref={form} onSubmit={ignore} data-agent-identity-form>
            <h4>{IDENTITY_TITLE}</h4>
            <IdentityFields
              pinnedModels={pinnedModels}
              idPrefix="agent-identity"
              nameLabel={IDENTITY_NAME_LABEL}
              modelLabel={IDENTITY_MODEL_LABEL}
              gatewayLabel={IDENTITY_GATEWAY_LABEL}
              gatewayHint={IDENTITY_GATEWAY_HINT}
              initial={identity}
            />
            <p className="am-form__hint">{IDENTITY_BILLING_NOTE}</p>
            {problem !== null ? <p className="am-form__problem" role="alert" data-agent-problem>{problem}</p> : null}
          </form>
          <PathChoiceView onChoose={choose} />
        </>
      )}
      <p>
        <button className="am-button am-button--quiet" type="button" onClick={onBack}>{WIZARD_BACK_LABEL}</button>
      </p>
    </section>
  );
}
