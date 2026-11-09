'use client';

/**
 * «API-провайдер» (`EXEC2-WEB-WIZARD-01`): the OpenRouter preset, an `http_api` connection with the
 * gateway's address and the `openai_chat` format filled in.
 *
 * The form asks for what a person decides — a name, a pinned model, the name OpenRouter calls it — and
 * prints the rest as fixed facts, so nothing is hidden: the address, the format, a direct connection,
 * and tariffs from the pinned model. Saving creates the connection and its first revision
 * (`useEnsureConnection`; a refused revision leaves the connection, and the next press saves the
 * settings onto it instead of creating a second one).
 *
 * **The key is not entered here, and that is deliberate.** `setExecutorSecret` has no caller in
 * `web/src`: a key set from a component would be a JavaScript value, in state, in a bundle, one
 * careless dependency away from leaving the page. The key is typed into the server-rendered form of
 * `features/set-executor-secret`, which posts natively to the BFF door, and this screen sends the
 * person there with a link to that form for this connection. After the key is saved, the card's
 * «Проверить» runs the probe.
 */

import { useState } from 'react';
import type { FormEvent } from 'react';

import type { ExecutorConnectionId, ExecutorPinnedModel } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { BILLING_LABELS, FLAVOUR_LABELS, TRANSPORT_LABELS } from '@/entities/executor-connection';
import { CommandFailure } from '@/features/manage-executor-connection';
import { executorSecretScreenUrl } from '@/features/set-executor-secret';

import { OPENROUTER_BASE_URL, openRouterRevisionRequest, readIdentity } from '../model/agent-settings';
import { agentFailure } from '../model/failure';
import { useEnsureConnection } from '../model/use-ensure-connection';
import {
  NO_PINNED_MODELS,
  OPENROUTER_DEFAULT_NAME,
  OPENROUTER_FIXED_TITLE,
  OPENROUTER_GATEWAY_HINT,
  OPENROUTER_GATEWAY_LABEL,
  OPENROUTER_INTRO,
  OPENROUTER_KEY_LINK_LABEL,
  OPENROUTER_KEY_TEXT,
  OPENROUTER_KEY_TITLE,
  OPENROUTER_MODEL_LABEL,
  OPENROUTER_NAME_LABEL,
  OPENROUTER_SUBMIT_LABEL,
  OPENROUTER_TITLE,
  WIZARD_BACK_LABEL,
} from '../model/words';
import { IdentityFields } from './identity-fields';
import styles from './connect-remote-agent.module.css';

export interface OpenRouterSetupProps {
  readonly pinnedModels: readonly ExecutorPinnedModel[];
  readonly onBack: () => void;
}

/** The facts the preset fixes, printed so nothing about the connection is hidden. */
export function OpenRouterFixedFacts() {
  return (
    <dl className={styles.facts} aria-label={OPENROUTER_FIXED_TITLE} data-openrouter-fixed>
      <dt>Адрес</dt>
      <dd><code>{OPENROUTER_BASE_URL}</code></dd>
      <dt>Формат запросов</dt>
      <dd data-executor-flavour="openai_chat">{FLAVOUR_LABELS.openai_chat}</dd>
      <dt>Способ связи</dt>
      <dd>{TRANSPORT_LABELS.direct}</dd>
      <dt>Тарификация</dt>
      <dd>{BILLING_LABELS.metered}</dd>
    </dl>
  );
}

/** The step after the connection exists: where the key is entered. A view driven by props. */
export function OpenRouterKeyStep({ connectionId, name }: { readonly connectionId: ExecutorConnectionId; readonly name: string }) {
  return (
    <section role="group" aria-label={OPENROUTER_KEY_TITLE} data-openrouter-key-step={connectionId}>
      <h4>{OPENROUTER_KEY_TITLE}</h4>
      <p className="am-note" role="status">Подключение «{name}» создано. {OPENROUTER_KEY_TEXT}</p>
      <p>
        <a className="am-button" href={executorSecretScreenUrl(connectionId)} data-openrouter-key-link>
          {OPENROUTER_KEY_LINK_LABEL}
        </a>
      </p>
    </section>
  );
}

export function OpenRouterSetup({ pinnedModels, onBack }: OpenRouterSetupProps) {
  const connection = useEnsureConnection();
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const [made, setMade] = useState<{ readonly id: ExecutorConnectionId; readonly name: string } | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const reading = readIdentity(new FormData(event.currentTarget), pinnedModels);
    if (!reading.ok) {
      setProblem(reading.problem);
      return;
    }
    setProblem(null);
    setFailure(null);
    setPending(true);
    try {
      const id = await connection.ensure({
        kind: 'http_api',
        displayName: reading.identity.displayName,
        body: openRouterRevisionRequest(reading.identity),
      });
      setMade({ id, name: reading.identity.displayName });
    } catch (error) {
      setFailure(agentFailure(error, true));
    } finally {
      setPending(false);
    }
  }

  if (made !== null) return <OpenRouterKeyStep connectionId={made.id} name={made.name} />;

  return (
    <section aria-label={OPENROUTER_TITLE} data-wizard-step="api">
      <form className={`am-form am-form--two ${styles.form}`} onSubmit={(event) => void submit(event)} data-openrouter-form>
        <h3>{OPENROUTER_TITLE}</h3>
        <p className="am-form__hint">{OPENROUTER_INTRO}</p>
        <OpenRouterFixedFacts />
        {pinnedModels.length === 0 ? (
          <p className="am-note" role="status">{NO_PINNED_MODELS}</p>
        ) : (
          <IdentityFields
            pinnedModels={pinnedModels}
            idPrefix="openrouter"
            nameLabel={OPENROUTER_NAME_LABEL}
            modelLabel={OPENROUTER_MODEL_LABEL}
            gatewayLabel={OPENROUTER_GATEWAY_LABEL}
            gatewayHint={OPENROUTER_GATEWAY_HINT}
            defaultName={OPENROUTER_DEFAULT_NAME}
          />
        )}
        {problem !== null ? <p className="am-form__problem" role="alert" data-agent-problem>{problem}</p> : null}
        <div className="am-form__row">
          <button className="am-button" type="submit" disabled={pending || pinnedModels.length === 0}>{OPENROUTER_SUBMIT_LABEL}</button>
          <button className="am-button am-button--quiet" type="button" disabled={pending} onClick={onBack}>{WIZARD_BACK_LABEL}</button>
        </div>
        {failure !== null ? <CommandFailure failure={failure} /> : null}
      </form>
    </section>
  );
}
