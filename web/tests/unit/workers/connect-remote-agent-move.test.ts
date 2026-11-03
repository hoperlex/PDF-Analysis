/**
 * `EXEC2-WEB-WIZARD-01` — moving an agent to another server (B2 §11 test 10, ADR-0026 decision 9,
 * `R-149b`): «Перенести на другой сервер» is a new enrollment for the same connection, and the old
 * token is offered for revocation only once the new agent is in the network.
 *
 * The rule (`supersededTokens`) is called with a fixed clock; the panel is rendered in the states the
 * rule produces. Written under `R-149d`: not run in EXEC-2. None of these needs a database.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import {
  AgentLifecyclePanel,
  MOVE_LABEL,
  MOVE_PENDING_NOTE,
  MOVE_TEXT,
  MoveAgentControl,
  OLD_TOKEN_CONFIRM_TEXT,
  OLD_TOKEN_REVOKE_LABEL,
  OLD_TOKEN_TEXT,
  PathChoiceView,
  SupersededTokensView,
  agentLifecycle,
} from '@/features/connect-remote-agent';

import { newClient, renderScreen } from '../screens/harness';
import { connectionId, tokenId } from './executor-fixtures';
import { DAY, HOUR, MINUTE, NOW, agentCase, agentToken, at, later, unseenToken } from './connect-remote-agent-fixtures';
import type { AgentCase } from './connect-remote-agent-fixtures';

const CID = connectionId(66);
const noop = () => undefined;

/** The agent on the old server: registered a day ago, in the network, signed in. */
const OLD = () => agentToken(1, CID, { token_prefix: 'токен-СТАРЫЙ', created_at: at(DAY) });
/** The agent on the new server, registered ten minutes ago. */
const NEW = (over: Parameters<typeof agentToken>[2] = {}) =>
  agentToken(2, CID, { token_prefix: 'токен-НОВЫЙ', created_at: at(10 * MINUTE), ...over });

const redeemed = (token: string) => ({
  state: 'redeemed' as const, redeemed_at: at(10 * MINUTE), runner_token_id: token,
});

const life = (c: AgentCase) => agentLifecycle(c.connection, c.detail, NOW);
const offered = (c: AgentCase) => life(c).supersededTokens.map((token) => token.token_prefix);

function panel(c: AgentCase, canManage = true): string {
  return renderScreen(newClient(), createElement(AgentLifecyclePanel, {
    connection: c.connection, detail: c.detail, canManage, nowMs: NOW,
  }));
}

describe('the old token is offered for revocation once, and only once, the new agent is in the network', () => {
  it('offers nothing while the new command has not been used: the old agent is the only one serving', () => {
    const c = agentCase({
      n: 66, tokens: [OLD()], enrollments: [{ state: 'pending', expires_at: later(10 * MINUTE) }],
    });
    expect(offered(c)).toEqual([]);
    expect(life(c).pendingEnrollment).not.toBeNull();
    // The connection stays ready on the old agent while the new one is being installed.
    expect(life(c).ready).toBe(true);
    const markup = panel(c);
    expect(markup).toContain('data-agent-move-pending');
    expect(markup).toContain(MOVE_PENDING_NOTE);
    expect(markup).not.toContain('data-agent-old-tokens');
  });

  it('offers nothing when the new agent registered but has not called yet, or is not in the network', () => {
    const grant = redeemed(tokenId(2));
    const unseen = agentCase({ n: 66, tokens: [OLD(), unseenToken(2, CID, { created_at: at(10 * MINUTE) })], enrollments: [grant] });
    const offline = agentCase({ n: 66, tokens: [OLD(), NEW({ online: false })], enrollments: [grant] });
    for (const c of [unseen, offline]) {
      expect(offered(c)).toEqual([]);
      expect(panel(c)).not.toContain('data-agent-old-tokens');
    }
  });

  it('offers the old token once the new agent is in the network, and names it', () => {
    const c = agentCase({ n: 66, tokens: [OLD(), NEW()], enrollments: [redeemed(tokenId(2))] });
    expect(offered(c)).toEqual(['токен-СТАРЫЙ']);
    // The agent that serves the connection is the new one.
    expect(life(c).token?.token_id).toBe(tokenId(2));
    const markup = panel(c);
    expect(markup).toContain('data-agent-old-tokens="1"');
    expect(markup).toContain('токен-СТАРЫЙ');
    expect(markup).toContain(OLD_TOKEN_REVOKE_LABEL);
    expect(markup).toContain(OLD_TOKEN_TEXT);
    expect(markup).toContain(`data-agent-old-token-revoke="${tokenId(1)}"`);
  });

  it('shows the offer to an administrator only', () => {
    const c = agentCase({ n: 66, tokens: [OLD(), NEW()], enrollments: [redeemed(tokenId(2))] });
    expect(panel(c, false)).not.toContain('data-agent-old-tokens');
    expect(panel(c, false)).not.toContain('data-agent-move-open');
  });

  it('does not offer a token that is already revoked or has run out', () => {
    const revoked = agentCase({
      n: 66, tokens: [{ ...OLD(), revoked_at: at(MINUTE) }, NEW()], enrollments: [redeemed(tokenId(2))],
    });
    const expired = agentCase({
      n: 66, tokens: [{ ...OLD(), expires_at: at(MINUTE) }, NEW()], enrollments: [redeemed(tokenId(2))],
    });
    expect(offered(revoked)).toEqual([]);
    expect(offered(expired)).toEqual([]);
    expect(panel(revoked)).not.toContain('data-agent-old-tokens');
  });

  it('never offers a token newer than the new agent’s own', () => {
    const newer = agentToken(3, CID, { token_prefix: 'токен-ЕЩЁ-НОВЕЕ', created_at: at(MINUTE) });
    const c = agentCase({ n: 66, tokens: [OLD(), NEW(), newer], enrollments: [redeemed(tokenId(2))] });
    expect(offered(c)).toEqual(['токен-СТАРЫЙ']);
  });

  it('offers nothing when no move is in progress: two tokens issued by hand are not a move', () => {
    const c = agentCase({ n: 66, tokens: [OLD(), NEW()] });
    expect(offered(c)).toEqual([]);
    const lost = agentCase({ n: 66, tokens: [OLD()], enrollments: [redeemed(tokenId(2))] });
    expect(offered(lost)).toEqual([]);
  });

  it('lists several old tokens, newest enrollment’s agent excluded', () => {
    const older = agentToken(4, CID, { token_prefix: 'токен-ДРЕВНИЙ', created_at: at(3 * DAY) });
    const c = agentCase({ n: 66, tokens: [older, OLD(), NEW()], enrollments: [redeemed(tokenId(2))] });
    expect(offered(c).sort()).toEqual(['токен-ДРЕВНИЙ', 'токен-СТАРЫЙ']);
    expect(panel(c)).toContain('data-agent-old-tokens="2"');
  });
});

describe('«Перенести на другой сервер»', () => {
  it('is offered to an administrator for an agent that is registered, and closed until pressed', () => {
    const c = agentCase({ n: 66, tokens: [OLD()] });
    const markup = panel(c);
    expect(markup).toContain('data-agent-move-open');
    expect(markup).toContain(MOVE_LABEL);
    expect(MOVE_LABEL).toBe('Перенести на другой сервер');
    expect(markup).not.toContain('data-agent-move="');
    expect(markup).not.toContain('data-agent-path');
  });

  it('is not offered where there is nothing to move: before registration, to an expert, or on an archived connection', () => {
    expect(panel(agentCase({ n: 66 }))).not.toContain('data-agent-move-open');
    expect(panel(agentCase({ n: 66, enrollments: [{ state: 'pending' }] }))).not.toContain('data-agent-move-open');
    expect(panel(agentCase({ n: 66, tokens: [OLD()] }), false)).not.toContain('data-agent-move-open');
    expect(panel(agentCase({ n: 66, tokens: [OLD()], archived: true }))).not.toContain('data-agent-move-open');
  });

  it('is a button on its own until it is pressed', () => {
    const c = agentCase({ n: 66, tokens: [OLD()] });
    const markup = renderScreen(newClient(), createElement(MoveAgentControl, { connection: c.connection }));
    expect(markup).toContain('data-agent-move-open');
    expect(markup).not.toContain('<form');
  });

  it('offers the same two equal ways to install as a first install does', () => {
    const markup = renderScreen(newClient(), createElement(PathChoiceView, { onChoose: noop }));
    expect(markup).toContain('data-agent-path="ssh"');
    expect(markup).toContain('data-agent-path="command"');
    expect(markup).toContain('Установить по SSH');
    expect(markup).toContain('Выполнить команду на Ubuntu');
  });

  it('says what a move keeps, what it does not copy, and what happens to work in flight', () => {
    expect(MOVE_TEXT).toContain('для того же подключения');
    expect(MOVE_TEXT).toContain('название, настройки, назначения и история остаются');
    expect(MOVE_TEXT).toContain('заново официальным способом, учётные данные не копируются');
    expect(MOVE_TEXT).toContain('отозвать токен прежнего');
    expect(MOVE_TEXT).toContain('исход которого неизвестен, не отправляется повторно');
  });

  it('asks before revoking, and says what happens to work the old agent holds', () => {
    const c = agentCase({ n: 66, tokens: [OLD(), NEW()], enrollments: [redeemed(tokenId(2))] });
    const tokens = life(c).supersededTokens;
    const view = (asking: typeof tokens[number] | null, failure: Parameters<typeof SupersededTokensView>[0]['failure'] = null) =>
      renderScreen(newClient(), createElement(SupersededTokensView, {
        tokens, asking, pending: false, failure, onAsk: noop, onConfirm: noop, onCancel: noop,
      }));
    const first = view(null);
    expect(first).not.toContain('data-agent-old-token-confirm');
    const asked = view(tokens[0] ?? null);
    expect(asked).toContain(`data-agent-old-token-confirm="${tokenId(1)}"`);
    expect(asked).toContain(OLD_TOKEN_CONFIRM_TEXT);
    expect(asked).toContain('Подтвердить отзыв');
    expect(OLD_TOKEN_CONFIRM_TEXT).toContain('вернётся в очередь или истечёт по обычным правилам');
    // After an unknown outcome the same key is pressed again, and the button says so.
    const unknown = view(tokens[0] ?? null, { kind: 'unknown_outcome', detail: 'Исход команды неизвестен.', correlationId: null });
    expect(unknown).toContain('Повторить с тем же ключом');
  });
});

describe('after a move the old probe does not stand for the new server', () => {
  it('asks for the probe again when the passing one is older than the agent now serving', () => {
    const c = agentCase({
      n: 66, tokens: [OLD(), NEW({ created_at: at(HOUR / 2 - 10 * MINUTE) })], enrollments: [redeemed(tokenId(2))],
      probe: { finished_at: at(HOUR / 2) },
    });
    expect(life(c).steps.probe.reason).toBe('stale');
    expect(life(c).ready).toBe(false);
    expect(panel(c)).toContain('на другом сервере');
  });
});
