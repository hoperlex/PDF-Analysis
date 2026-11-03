'use client';

/**
 * «Перенести на другой сервер» (`EXEC2-WEB-WIZARD-01`, ADR-0026 decision 9, `R-149b`).
 *
 * Moving an agent is **a new enrollment for the same connection**: the connection's name, settings,
 * routes and history stay, and the new host gets its own runner token through path A or path B,
 * exactly as a first install does (`AgentEnrollmentFlow` with an `ensure` that returns the existing
 * connection). Nothing is copied from the old host. Signing in to the official clients on the new host
 * is done there, again, by the client's own flow.
 *
 * **The old token is revoked on purpose, and only once the new agent is in the network.** Until then
 * the old agent is the only one serving. When the lifecycle reports tokens it has superseded
 * (`supersededTokens`), `SupersededTokens` names each, says when it was last seen, and offers
 * «Отозвать прежний токен» behind a confirmation. Work in flight follows the existing semantics:
 * what the old agent holds returns to the queue or expires, and a reply whose outcome is unknown is
 * never sent again. Revoking is the existing `revokeRunnerToken`; nothing new is invented here.
 */

import { useState } from 'react';

import type { ExecutorConnection, RunnerTokenMetadata } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { formatInstant } from '@/shared/lib';
import { CommandFailure, useCommandKey, useRevokeRunnerToken } from '@/features/manage-executor-connection';

import { agentFailure } from '../model/failure';
import {
  MOVE_CANCEL_LABEL,
  MOVE_LABEL,
  MOVE_TEXT,
  MOVE_TITLE,
  OLD_TOKEN_CONFIRM_LABEL,
  OLD_TOKEN_CONFIRM_TEXT,
  OLD_TOKEN_REVOKE_LABEL,
  OLD_TOKEN_TEXT,
  OLD_TOKEN_TITLE,
} from '../model/words';
import { AgentEnrollmentFlow } from './agent-enrollment-flow';
import { PathChoiceView } from './choices';
import type { PathChoice } from './choices';

export function MoveAgentControl({ connection }: { readonly connection: ExecutorConnection }) {
  const [open, setOpen] = useState(false);
  const [path, setPath] = useState<PathChoice | null>(null);

  if (!open) {
    return (
      <button className="am-button am-button--quiet" type="button" data-agent-move-open onClick={() => setOpen(true)}>
        {MOVE_LABEL}
      </button>
    );
  }
  return (
    <section role="group" aria-label={MOVE_TITLE} data-agent-move={connection.connection_id}>
      <h4>{MOVE_TITLE}</h4>
      <p className="am-note">{MOVE_TEXT}</p>
      {path === null ? (
        <PathChoiceView onChoose={setPath} />
      ) : (
        <AgentEnrollmentFlow
          path={path}
          ensure={async () => connection.connection_id}
          onBack={() => setPath(null)}
        />
      )}
      <p>
        <button
          className="am-button am-button--quiet"
          type="button"
          onClick={() => { setOpen(false); setPath(null); }}
        >
          {MOVE_CANCEL_LABEL}
        </button>
      </p>
    </section>
  );
}

export interface SupersededTokensViewProps {
  readonly tokens: readonly RunnerTokenMetadata[];
  readonly asking: RunnerTokenMetadata | null;
  readonly pending: boolean;
  readonly failure: ExecutionFailure | null;
  readonly onAsk: (token: RunnerTokenMetadata) => void;
  readonly onConfirm: (token: RunnerTokenMetadata) => void;
  readonly onCancel: () => void;
}

export function SupersededTokensView({
  tokens, asking, pending, failure, onAsk, onConfirm, onCancel,
}: SupersededTokensViewProps) {
  return (
    <section role="group" aria-label={OLD_TOKEN_TITLE} data-agent-old-tokens={tokens.length}>
      <h4>{OLD_TOKEN_TITLE}</h4>
      <p className="am-note">{OLD_TOKEN_TEXT}</p>
      <ul>
        {tokens.map((token) => (
          <li key={token.token_id} data-agent-old-token={token.token_id}>
            <code>{token.token_prefix}…</code>
            {token.last_seen_at === undefined ? ', обращений не было' : (
              <>, последнее обращение <time dateTime={token.last_seen_at}>{formatInstant(token.last_seen_at)}</time></>
            )}{' '}
            <button
              className="am-button am-button--quiet am-button--small"
              type="button"
              disabled={pending}
              data-agent-old-token-revoke={token.token_id}
              onClick={() => onAsk(token)}
            >
              {OLD_TOKEN_REVOKE_LABEL}
            </button>
          </li>
        ))}
      </ul>
      {asking !== null ? (
        <div role="group" aria-label={OLD_TOKEN_CONFIRM_LABEL} data-agent-old-token-confirm={asking.token_id}>
          <p className="am-note">{OLD_TOKEN_CONFIRM_TEXT}</p>
          <button className="am-button" type="button" disabled={pending} onClick={() => onConfirm(asking)}>
            {failure?.kind === 'unknown_outcome' ? 'Повторить с тем же ключом' : OLD_TOKEN_CONFIRM_LABEL}
          </button>{' '}
          <button className="am-button am-button--quiet" type="button" disabled={pending} onClick={onCancel}>
            {MOVE_CANCEL_LABEL}
          </button>
        </div>
      ) : null}
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </section>
  );
}

export interface SupersededTokensProps {
  readonly connection: ExecutorConnection;
  readonly tokens: readonly RunnerTokenMetadata[];
}

export function SupersededTokens({ connection, tokens }: SupersededTokensProps) {
  const revoke = useRevokeRunnerToken();
  const keys = useCommandKey();
  const [asking, setAsking] = useState<RunnerTokenMetadata | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function confirm(token: RunnerTokenMetadata) {
    setFailure(null);
    try {
      await revoke.mutateAsync({
        connectionId: connection.connection_id,
        tokenId: token.token_id,
        idempotencyKey: keys.keyFor(token.token_id),
      });
      keys.release();
      setAsking(null);
    } catch (error) {
      const failed = agentFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <SupersededTokensView
      tokens={tokens}
      asking={asking}
      pending={revoke.isPending}
      failure={failure}
      onAsk={(token) => { setAsking(token); setFailure(null); }}
      onConfirm={(token) => void confirm(token)}
      onCancel={() => { setAsking(null); setFailure(null); keys.release(); }}
    />
  );
}
