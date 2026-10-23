/**
 * `EXEC-CANDIDATE-2` (`EXEC-PULL-01` on the screen) — the runner tokens of a `pull` connection,
 * as a person reads them: the token shown once, the list the server keeps afterwards, «на связи»,
 * the open tasks, and who may issue and revoke.
 *
 * Rendered, not read from source: the static render keeps every `useState` at its start, so the
 * panel is judged before anything is pressed; the box a fresh token appears in is a view of its
 * own and is rendered directly.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { IssuedRunnerToken, Role } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import {
  RUNNER_ONLINE_WINDOW_MS,
  RUNNER_TOKEN_STATE_LABELS,
  connectionRunnerIsOnline,
  hasLiveRunnerToken,
  routeBlocker,
  runnerTokenIsOnline,
  runnerTokenState,
  sortedRunnerTokens,
} from '@/entities/executor-connection';
import { IssuedTokenView } from '@/features/manage-executor-connection';
import { WEB_ROOT, walkFiles } from '../../guards/lib/repo';
import { ExecutorConnections } from '@/widgets/executor-connections';

import { newClient, renderScreen } from '../screens/harness';
import { PULL_BARE, PULL_CASES, PULL_ONLINE, PULL_QUIET, READY, ago, runnerToken, seedExecutors, tokenId } from './executor-fixtures';

function connections(roles: Role[], cases = PULL_CASES): string {
  const client = newClient();
  seedExecutors(client, cases);
  client.setQueryData(queryKeys.account.me(), { roles });
  return renderScreen(client, createElement(ExecutorConnections, { roles }));
}

const NOW = Date.parse('2026-10-22T10:00:00Z');
const CID = PULL_ONLINE.connection.connection_id;
const at = (milliseconds: number): string => new Date(NOW - milliseconds).toISOString();
const later = (milliseconds: number): string => new Date(NOW + milliseconds).toISOString();

describe('«на связи» is a call in the last minute', () => {
  const live = { expires_at: later(86_400_000) };

  it('is on for a live token seen 59 seconds ago and off at 60', () => {
    expect(RUNNER_ONLINE_WINDOW_MS).toBe(60_000);
    expect(runnerTokenIsOnline({ ...live, last_seen_at: at(59_999) }, NOW)).toBe(true);
    expect(runnerTokenIsOnline({ ...live, last_seen_at: at(60_000) }, NOW)).toBe(false);
    expect(runnerTokenIsOnline({ ...live }, NOW)).toBe(false);
  });

  it('is never on for a revoked or an expired token, however recent its last call', () => {
    expect(runnerTokenIsOnline({ ...live, last_seen_at: at(1_000), revoked_at: at(500) }, NOW)).toBe(false);
    expect(runnerTokenIsOnline({ expires_at: at(1), last_seen_at: at(1_000) }, NOW)).toBe(false);
    expect(runnerTokenState({ expires_at: at(1), revoked_at: at(10) }, NOW)).toBe('revoked');
    expect(runnerTokenState({ expires_at: at(1) }, NOW)).toBe('expired');
    expect(runnerTokenState(live, NOW)).toBe('active');
  });

  it('is on for the connection when any one of its tokens is', () => {
    const one = (last: string) => ({
      runner_tokens: [
        runnerToken({ token_id: tokenId(1), connection_id: CID, expires_at: later(1000), last_seen_at: at(900_000) }),
        runnerToken({ token_id: tokenId(2), connection_id: CID, expires_at: later(1000), last_seen_at: last }),
      ],
    });
    expect(connectionRunnerIsOnline(one(at(5_000)), NOW)).toBe(true);
    expect(connectionRunnerIsOnline(one(at(120_000)), NOW)).toBe(false);
    expect(connectionRunnerIsOnline({}, NOW)).toBe(false);
    expect(connectionRunnerIsOnline(undefined, NOW)).toBe(false);
  });

  it('lists the newest token first and says all three states in Russian', () => {
    const tokens = [
      runnerToken({ token_id: tokenId(1), connection_id: CID, created_at: at(3000) }),
      runnerToken({ token_id: tokenId(2), connection_id: CID, created_at: at(1000) }),
      runnerToken({ token_id: tokenId(3), connection_id: CID, created_at: at(2000) }),
    ];
    expect(sortedRunnerTokens(tokens).map((token) => token.token_id)).toEqual([tokenId(2), tokenId(3), tokenId(1)]);
    expect(Object.values(RUNNER_TOKEN_STATE_LABELS)).toEqual(['действует', 'отозван', 'срок истёк']);
  });

  it('knows a connection that holds a live token, which is what a re-read of the card is for', () => {
    expect(hasLiveRunnerToken(PULL_ONLINE.detail, Date.now())).toBe(true);
    expect(hasLiveRunnerToken(READY.detail, Date.now())).toBe(false);
    expect(hasLiveRunnerToken(PULL_BARE.detail, Date.now())).toBe(false);
    expect(hasLiveRunnerToken(undefined, Date.now())).toBe(false);
    const revokedOnly = { ...PULL_ONLINE.detail, runner_tokens: (PULL_ONLINE.detail.runner_tokens ?? []).filter((token) => token.revoked_at !== undefined) };
    expect(hasLiveRunnerToken(revokedOnly, Date.now())).toBe(false);
  });
});

describe('what the panel shows an administrator', () => {
  const markup = connections(['admin']);

  it('shows a connection that is «на связи», with its open tasks, its tokens and where it was last seen', () => {
    expect(markup).toContain(`data-executor-runner-panel="${CID}"`);
    expect(markup).toContain('data-executor-runner-online="yes"');
    expect(markup).toContain('data-executor-open-tasks="2"');
    expect(markup).toContain('data-executor-heading-online="yes"');
    for (const text of ['токен-ЖИВ1', 'токен-ОТЗ2', 'токен-СРОК', '203.0.113.7', 'последнее обращение', 'обращений ещё не было']) {
      expect(markup, text).toContain(text);
    }
    for (const state of ['active', 'revoked', 'expired']) expect(markup).toContain(`data-executor-runner-token-state="${state}"`);
  });

  it('offers «Отозвать» for a live token only, and «Выпустить токен» to issue a new one', () => {
    expect(markup).toContain('Выпустить токен');
    // PULL_ONLINE holds one live token, PULL_QUIET one: two buttons in all, none for the revoked or the expired.
    expect(markup.match(/data-executor-runner-token-revoke=/g)?.length).toBe(2);
    const revokedRow = /<li[^>]*data-executor-runner-token-state="revoked"[\s\S]*?<\/li>/.exec(markup)?.[0] ?? '';
    expect(revokedRow).not.toBe('');
    expect(revokedRow).not.toContain('Отозвать');
    const expiredRow = /<li[^>]*data-executor-runner-token-state="expired"[\s\S]*?<\/li>/.exec(markup)?.[0] ?? '';
    expect(expiredRow).not.toContain('Отозвать');
  });

  it('says a client last seen ten minutes ago is not «на связи», and one with no token has none', () => {
    const quiet = connections(['admin'], [PULL_QUIET]);
    expect(quiet).toContain('data-executor-runner-online="no"');
    expect(quiet).toContain('data-executor-open-tasks="1"');
    expect(quiet).not.toContain('data-executor-heading-online');
    expect(quiet).toContain('не на связи');
    const bare = connections(['admin'], [PULL_BARE]);
    expect(bare).toContain('data-executor-runner-tokens="none"');
    expect(bare).toContain('Токенов ещё нет');
    expect(bare).toContain('data-executor-open-tasks="0"');
  });

  it('warns that the single slot is busy while a client thinks, and that nothing falls back', () => {
    expect(markup).toContain('единственный процесс стенда ждёт его ответа');
    expect(markup).toContain('не переходит на другое подключение');
  });

  it('is ready to be routed once its probe passed, with no key to enter and no key link', () => {
    expect(routeBlocker(PULL_ONLINE.connection, PULL_ONLINE.detail.revisions[0])).toBeNull();
    expect(routeBlocker(PULL_BARE.connection, PULL_BARE.detail.revisions[0])).toBe('not_probed');
    const ready = connections(['admin'], [PULL_ONLINE]);
    expect(ready).toContain('data-executor-ready="yes"');
    expect(ready).not.toContain('data-executor-key-link');
    expect(ready).toContain('нет вводимого ключа');
    // The probe was taken by a runner that declared its model: the screen says so.
    expect(ready).toContain('модель заявлена исполнителем');
  });

  it('never prints a token value: nothing but a prefix is in the markup', () => {
    expect(markup).not.toContain('<textarea');
    expect(markup).not.toContain('data-executor-runner-token-value');
    expect(markup).not.toContain('data-executor-runner-token-shown');
  });
});

describe('what an expert sees', () => {
  it('reads the tokens, «на связи» and the open tasks, and is given no control', () => {
    const expert = connections(['expert']);
    expect(expert).toContain('data-executor-runner-online="yes"');
    expect(expert).toContain('data-executor-open-tasks="2"');
    expect(expert).toContain('токен-ЖИВ1');
    for (const text of ['Выпустить токен', 'Отозвать', 'data-executor-runner-issue', 'data-executor-runner-days']) {
      expect(expert, text).not.toContain(text);
    }
  });

  it('is shown no panel for a connection of another kind', () => {
    expect(connections(['admin'], [READY])).not.toContain('data-executor-runner-panel');
  });
});

describe('the token, shown once', () => {
  const issued: IssuedRunnerToken = {
    token: 'токен-значение-для-показа',
    runner_token: runnerToken({ token_id: tokenId(9), connection_id: CID, token_prefix: 'токен-НОВ9', expires_at: later(30 * 86_400_000) }),
  };
  const markup = renderScreen(newClient(), createElement(IssuedTokenView, { issued, onClose: () => undefined }));

  it('puts the value in a read-only box with a copy button, beside a warning that it will not be shown again', () => {
    expect(markup).toContain('data-executor-runner-token-shown');
    expect(markup).toMatch(/<textarea[^>]*readOnly[^>]*>токен-значение-для-показа<\/textarea>/);
    expect(markup).toContain('data-executor-runner-token-copy');
    expect(markup).toContain('Скопировать');
    expect(markup).toContain('показан один раз и больше не будет показан');
    expect(markup).toContain('data-executor-runner-token-close');
    // The warning is an alert, so a reader of the page hears it.
    expect(markup).toContain('role="alert"');
  });

  it('says where the value goes, and that it is never a file or an address', () => {
    expect(markup).toContain('через переменную окружения');
    expect(markup).toContain('не записывайте его в файл, в адрес и в сообщение');
  });
});

describe('the screen never reaches the runner channel', () => {
  const RUNNER_OPERATIONS = ['claimExecutorTask', 'extendExecutorTaskClaim', 'submitExecutorTaskAnswer', 'failExecutorTask', 'getExecutorTaskImage'];

  it('calls none of the four operations a runner uses from anywhere under web/src', () => {
    const offenders: string[] = [];
    for (const file of walkFiles(join(WEB_ROOT, 'src'), (name) => /\.(ts|tsx)$/.test(name))) {
      if (file.includes(`${join('shared', 'api', 'generated')}`)) continue;
      const text = readFileSync(file, 'utf8');
      for (const operation of RUNNER_OPERATIONS) if (text.includes(operation)) offenders.push(`${file}: ${operation}`);
    }
    expect(offenders).toEqual([]);
  });

  it('keeps no token value in the browser: nothing stores it', () => {
    const panel = readFileSync(join(WEB_ROOT, 'src/features/manage-executor-connection/ui/runner-token-panel.tsx'), 'utf8');
    for (const forbidden of ['localStorage', 'sessionStorage', 'document.cookie', 'indexedDB', 'console.']) {
      expect(panel, forbidden).not.toContain(forbidden);
    }
    // The issue mutation is dropped as soon as it settles.
    const hooks = readFileSync(join(WEB_ROOT, 'src/features/manage-executor-connection/model/use-manage-executor-connection.ts'), 'utf8');
    expect(hooks).toContain('gcTime: 0');
  });
});

// A clock-independent check of the helper the fixtures use.
describe('the fixtures', () => {
  it('keep the live token recent and the other one old', () => {
    expect(Date.now() - Date.parse(PULL_ONLINE.detail.runner_tokens![0]!.last_seen_at!)).toBeLessThan(RUNNER_ONLINE_WINDOW_MS);
    expect(Date.now() - Date.parse(PULL_QUIET.detail.runner_tokens![0]!.last_seen_at!)).toBeGreaterThan(RUNNER_ONLINE_WINDOW_MS);
    expect(ago(1)).toMatch(/Z$/);
  });
});
