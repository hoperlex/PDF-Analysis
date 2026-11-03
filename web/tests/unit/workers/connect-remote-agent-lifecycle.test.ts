/**
 * `EXEC2-WEB-WIZARD-01` — the lifecycle of an agent connection (B2 §11 test 9): one lifecycle for both
 * install paths, read from the connection's detail; the four statuses of ADR-0026 decision 8 stay
 * distinct; the official login guidance and «Проверить снова».
 *
 *     ожидает регистрации → агент в сети → клиент найден → вход действителен / нужен вход
 *       → проба пройдена → готово
 *
 * Two layers. The pure rules (`agentLifecycle`, `agentIsMoving`) are called with a fixed clock. The
 * panel is rendered to static markup in the states each rule produces, because the harness cannot
 * press a button: what a person is shown, and offered, in each state is what is asserted.
 *
 * Written under `R-149d`: not run in EXEC-2. None of these needs a database.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import {
  AGENT_PROBE_HINTS,
  AGENT_STEP_ORDER,
  AgentLifecyclePanel,
  INTEGRATION_NOTE,
  JOIN_WINDOW_MS,
  LOGIN_COMMANDS,
  STEP_LABELS,
  agentIsMoving,
  agentLifecycle,
  currentStep,
  enrollmentIsExpired,
  stepSentence,
} from '@/features/connect-remote-agent';
import type { AgentStepId } from '@/features/connect-remote-agent';
import { RUNNER_CLI_AUTH_STATE_VALUES, RUNNER_CLI_NAME_VALUES } from '@/shared/api';

import { newClient, renderScreen } from '../screens/harness';
import { connectionId } from './executor-fixtures';
import {
  HOUR, MINUTE, NOW, agentCase, agentToken, at, claude, codex, later, unseenToken, withoutOnline,
} from './connect-remote-agent-fixtures';
import type { AgentCase } from './connect-remote-agent-fixtures';

const CID = connectionId(61);

const life = (c: AgentCase, now = NOW) => agentLifecycle(c.connection, c.detail, now);
const reason = (c: AgentCase, id: AgentStepId) => life(c).steps[id].reason;
const state = (c: AgentCase, id: AgentStepId) => life(c).steps[id].state;

/** A ready agent: registered an hour ago, in the network, a signed-in client, a probe after that. */
const READY = () => agentCase({ n: 61, tokens: [agentToken(1, CID)] });

describe('registration: ожидает регистрации', () => {
  it('has not started when there is no grant and no token', () => {
    const c = agentCase({ n: 61 });
    expect(reason(c, 'registration')).toBe('not_started');
    expect(state(c, 'registration')).toBe('waiting');
    expect(reason(c, 'online')).toBe('waiting_registration');
    expect(currentStep(life(c)).id).toBe('registration');
    expect(life(c).ready).toBe(false);
  });

  it('waits while a fresh grant has not been used, and says until when the command works', () => {
    const c = agentCase({ n: 61, enrollments: [{ state: 'pending', expires_at: later(10 * MINUTE) }] });
    expect(reason(c, 'registration')).toBe('waiting');
    expect(life(c).pendingEnrollment).not.toBeNull();
    const sentence = stepSentence(life(c), 'registration');
    expect(sentence).toContain('Ожидает регистрации');
    expect(sentence).toContain('Команда действует до');
  });

  it('is «Команда устарела» when the server says expired, and when the clock has passed a grant it still calls pending', () => {
    const server = agentCase({ n: 61, enrollments: [{ state: 'expired', expires_at: at(MINUTE) }] });
    const clock = agentCase({ n: 61, enrollments: [{ state: 'pending', expires_at: at(1) }] });
    for (const c of [server, clock]) {
      expect(reason(c, 'registration')).toBe('expired');
      expect(state(c, 'registration')).toBe('attention');
      expect(life(c).pendingEnrollment).toBeNull();
      expect(stepSentence(life(c), 'registration')).toContain('Команда устарела');
    }
    const [grant] = clock.detail.enrollments ?? [];
    if (grant === undefined) throw new Error('the fixture carries a grant');
    expect(grant.state).toBe('pending');
    expect(enrollmentIsExpired(grant, NOW)).toBe(true);
  });

  it('says a grant that was replaced or revoked did not register', () => {
    const c = agentCase({ n: 61, enrollments: [{ state: 'revoked', revoked_at: at(MINUTE) }] });
    expect(reason(c, 'registration')).toBe('replaced');
    expect(state(c, 'registration')).toBe('attention');
  });

  it('is registered once a live token exists, whichever path produced it', () => {
    const viaGrant = agentCase({
      n: 61, tokens: [agentToken(1, CID)],
      enrollments: [{ state: 'redeemed', redeemed_at: at(HOUR) }],
    });
    const viaToken = agentCase({ n: 61, tokens: [agentToken(1, CID)] });
    for (const c of [viaGrant, viaToken]) {
      expect(reason(c, 'registration')).toBe('registered');
      expect(state(c, 'registration')).toBe('done');
    }
  });

  it('knows the agent was registered and its token is gone', () => {
    const c = agentCase({
      n: 61, tokens: [agentToken(1, CID, { revoked_at: at(MINUTE) })],
      enrollments: [{ state: 'redeemed', redeemed_at: at(HOUR) }],
    });
    expect(reason(c, 'registration')).toBe('token_gone');
    expect(state(c, 'registration')).toBe('attention');
  });
});

describe('агент в сети', () => {
  it('trusts the server’s online flag over the page’s clock', () => {
    const offline = agentCase({ n: 61, tokens: [agentToken(1, CID, { online: false, last_seen_at: at(5_000) })] });
    const online = agentCase({ n: 61, tokens: [agentToken(1, CID, { online: true, last_seen_at: at(10 * MINUTE) })] });
    expect(reason(offline, 'online')).toBe('offline');
    expect(state(offline, 'online')).toBe('attention');
    expect(reason(online, 'online')).toBe('online');
  });

  it('falls back to the last call, a minute at most, when the server sent no flag', () => {
    const recent = agentCase({ n: 61, tokens: [withoutOnline(agentToken(1, CID, { last_seen_at: at(59_000) }))] });
    const stale = agentCase({ n: 61, tokens: [withoutOnline(agentToken(1, CID, { last_seen_at: at(61_000) }))] });
    expect(reason(recent, 'online')).toBe('online');
    expect(reason(stale, 'online')).toBe('offline');
  });

  it('is waiting, not failed, for an agent that registered and has not called yet', () => {
    const c = agentCase({ n: 61, tokens: [unseenToken(1, CID)] });
    expect(reason(c, 'online')).toBe('never_seen');
    expect(state(c, 'online')).toBe('waiting');
  });

  it('says, for an offline agent, when it was last seen and what to check', () => {
    const c = agentCase({ n: 61, tokens: [agentToken(1, CID, { online: false, last_seen_at: at(10 * MINUTE) })] });
    const sentence = stepSentence(life(c), 'online');
    expect(sentence).toContain('Агент не в сети');
    expect(sentence).toContain('Последнее обращение');
    expect(sentence).toContain('служба агента запущена');
  });
});

describe('клиент найден и вход: CLI missing, login needed', () => {
  it('waits for a report before it says anything about the clients', () => {
    const c = agentCase({ n: 61, tokens: [unseenToken(1, CID)] });
    expect(reason(c, 'installed')).toBe('no_report');
    expect(reason(c, 'login')).toBe('no_client');
    expect(state(c, 'installed')).toBe('waiting');
  });

  it('calls a report with no installed client «CLI missing», and an empty report too', () => {
    for (const clis of [[], [claude('valid', false), codex('valid', false)]]) {
      const c = agentCase({ n: 61, tokens: [agentToken(1, CID, { clis })] });
      expect(reason(c, 'installed')).toBe('missing');
      expect(state(c, 'installed')).toBe('attention');
      expect(reason(c, 'login')).toBe('no_client');
      expect(stepSentence(life(c), 'installed')).toContain('не найден');
    }
  });

  it('finds an installed client and reads its login: valid, needed, or unknown', () => {
    const valid = agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('valid')] })] });
    const needed = agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [codex('login_required')] })] });
    const unknown = agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('unknown')] })] });
    expect(reason(valid, 'installed')).toBe('found');
    expect([reason(valid, 'login'), state(valid, 'login')]).toEqual(['valid', 'done']);
    expect([reason(needed, 'login'), state(needed, 'login')]).toEqual(['login_required', 'attention']);
    expect([reason(unknown, 'login'), state(unknown, 'login')]).toEqual(['unknown', 'waiting']);
    expect(stepSentence(life(needed), 'login')).toContain('Нужен вход');
  });

  it('takes one valid client as a valid login even when another one needs signing in', () => {
    const c = agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('valid'), codex('login_required')] })] });
    expect(reason(c, 'login')).toBe('valid');
    expect(life(c).clis.map((item) => [item.cli, item.auth])).toEqual([['claude', 'valid'], ['codex', 'login_required']]);
  });

  it('never counts a client that is not installed as signed in, whatever it reports', () => {
    const c = agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('valid', false)] })] });
    expect(life(c).clis[0]?.auth).toBe('unknown');
    expect(reason(c, 'login')).toBe('no_client');
  });
});

describe('проба пройдена', () => {
  it('has not run, is running, failed, passed — and is stale when it passed on another host', () => {
    const none = agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: null });
    const open = agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: { state: 'running' } });
    const failed = agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: { outcome: 'timeout' } });
    const passed = READY();
    const stale = agentCase({
      n: 61, tokens: [agentToken(1, CID, { created_at: at(10 * MINUTE) })], probe: { finished_at: at(28 * MINUTE) },
    });
    expect([reason(none, 'probe'), state(none, 'probe')]).toEqual(['not_requested', 'waiting']);
    expect([reason(open, 'probe'), state(open, 'probe')]).toEqual(['open', 'waiting']);
    expect([reason(failed, 'probe'), state(failed, 'probe')]).toEqual(['failed', 'attention']);
    expect([reason(passed, 'probe'), state(passed, 'probe')]).toEqual(['passed', 'done']);
    expect([reason(stale, 'probe'), state(stale, 'probe')]).toEqual(['stale', 'waiting']);
    expect(life(stale).ready).toBe(false);
  });

  it('says «unsupported model» when the client answered with another model', () => {
    const c = agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: { outcome: 'model_mismatch' } });
    const sentence = stepSentence(life(c), 'probe');
    expect(sentence).toContain('Проба не пройдена');
    expect(sentence).toContain('Неподдерживаемая модель');
    expect(sentence).not.toContain('Шлюз');
  });

  it('has an agent wording for every outcome a pull agent’s probe can end in, in Russian', () => {
    for (const outcome of ['no_runner_online', 'model_mismatch', 'credential_refused', 'timeout', 'protocol_error', 'kind_not_served'] as const) {
      expect(AGENT_PROBE_HINTS[outcome], outcome).toMatch(/[А-Яа-я]{4}/);
    }
    const c = agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: { outcome: 'no_runner_online' } });
    expect(stepSentence(life(c), 'probe')).toContain('не в сети или занят');
  });
});

describe('готово, and the four statuses that stay distinct (ADR-0026 decision 8, R-149b)', () => {
  it('is ready when registered, in the network, with a signed-in client and a passed probe', () => {
    const c = READY();
    expect(life(c).ready).toBe(true);
    expect(currentStep(life(c)).id).toBe('ready');
    expect(stepSentence(life(c), 'ready')).toContain('готов принимать задания');
  });

  it('is not ready if any one of the five steps is not done, and not for an archived connection', () => {
    const broken: AgentCase[] = [
      agentCase({ n: 61, tokens: [agentToken(1, CID)], enrollments: [] , probe: null }),
      agentCase({ n: 61, tokens: [agentToken(1, CID, { online: false })] }),
      agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [] })] }),
      agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('login_required')] })] }),
      agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: { outcome: 'timeout' } }),
      agentCase({ n: 61 }),
      agentCase({ n: 61, tokens: [agentToken(1, CID)], archived: true }),
    ];
    for (const c of broken) expect(life(c).ready).toBe(false);
  });

  it('reads the administrator’s mark on its own: no other step moves with it, and «готово» does not wait for it', () => {
    const without = life(READY());
    const withMark = life(agentCase({ n: 61, tokens: [agentToken(1, CID)], mark: true }));
    const others = (l: typeof without) => AGENT_STEP_ORDER.filter((id) => id !== 'authorised').map((id) => l.steps[id]);
    expect(others(withMark)).toEqual(others(without));
    expect(without.steps.authorised).toEqual({ id: 'authorised', reason: 'not_set', state: 'inert' });
    expect(withMark.steps.authorised).toEqual({ id: 'authorised', reason: 'set', state: 'done' });
    expect(without.ready).toBe(true);
    expect(withMark.ready).toBe(true);
  });

  it('does not infer the mark from anything else: a missing client, a bad login or a failed probe leave it as set', () => {
    for (const over of [{ clis: [] }, { clis: [claude('login_required')] }, { online: false }]) {
      const c = agentCase({ n: 61, mark: true, tokens: [agentToken(1, CID, over)] });
      expect(reason(c, 'authorised')).toBe('set');
    }
    const failed = agentCase({ n: 61, mark: true, tokens: [agentToken(1, CID)], probe: { outcome: 'timeout' } });
    expect(reason(failed, 'authorised')).toBe('set');
    expect(reason(failed, 'probe')).toBe('failed');
  });

  it('does not infer a passed probe from a valid login, nor a valid login from a passed probe', () => {
    const loginOnly = agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: null });
    expect(reason(loginOnly, 'login')).toBe('valid');
    expect(reason(loginOnly, 'probe')).toBe('not_requested');
    expect(life(loginOnly).ready).toBe(false);

    const probeOnly = agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('login_required')] })] });
    expect(reason(probeOnly, 'probe')).toBe('passed');
    expect(reason(probeOnly, 'login')).toBe('login_required');
    expect(life(probeOnly).ready).toBe(false);
  });

  it('does not infer a login from an installed client: every auth state the contract has is read as itself', () => {
    expect([...RUNNER_CLI_NAME_VALUES].sort()).toEqual(['claude', 'codex']);
    const expected = { valid: 'valid', login_required: 'login_required', unknown: 'unknown' } as const;
    for (const auth of RUNNER_CLI_AUTH_STATE_VALUES) {
      const c = agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude(auth)] })] });
      expect(reason(c, 'installed')).toBe('found');
      expect(reason(c, 'login')).toBe(expected[auth]);
    }
  });

  it('keeps the seven steps in the order of the lifecycle, each with a Russian label', () => {
    expect(AGENT_STEP_ORDER).toEqual(['registration', 'online', 'installed', 'login', 'authorised', 'probe', 'ready']);
    for (const id of AGENT_STEP_ORDER) expect(STEP_LABELS[id]).toMatch(/[А-Яа-я]{4}/);
    expect(STEP_LABELS.installed).toBe('Клиент командной строки установлен');
    expect(STEP_LABELS.login).toBe('Вход клиента действителен');
    expect(STEP_LABELS.authorised).toBe('Разрешено для интеграции');
    expect(STEP_LABELS.probe).toBe('Проба модели пройдена');
  });

  it('names the first step that is not done as the current one', () => {
    expect(currentStep(life(agentCase({ n: 61 }))).id).toBe('registration');
    expect(currentStep(life(agentCase({ n: 61, tokens: [agentToken(1, CID, { online: false })] }))).id).toBe('online');
    expect(currentStep(life(agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [] })] }))).id).toBe('installed');
    expect(currentStep(life(agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [codex('login_required')] })] }))).id).toBe('login');
    expect(currentStep(life(agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: null }))).id).toBe('probe');
  });
});

describe('the detail is re-read only while something moves', () => {
  it('moves while a fresh grant waits, and stops once it is used or has run out', () => {
    expect(agentIsMoving(agentCase({ n: 61, enrollments: [{ state: 'pending' }] }).detail, NOW)).toBe(true);
    expect(agentIsMoving(agentCase({ n: 61, enrollments: [{ state: 'expired' }] }).detail, NOW)).toBe(false);
    expect(agentIsMoving(agentCase({ n: 61, enrollments: [{ state: 'pending', expires_at: at(1) }] }).detail, NOW)).toBe(false);
  });

  it('moves for a quarter of an hour after an agent registered while it is not ready, and then stops', () => {
    const fresh = (age: number) => agentCase({
      n: 61, tokens: [agentToken(1, CID, { created_at: at(age), clis: [] })],
    }).detail;
    expect(JOIN_WINDOW_MS).toBe(15 * MINUTE);
    expect(agentIsMoving(fresh(5 * MINUTE), NOW)).toBe(true);
    expect(agentIsMoving(fresh(14 * MINUTE), NOW)).toBe(true);
    expect(agentIsMoving(fresh(16 * MINUTE), NOW)).toBe(false);
  });

  it('does not move when the agent is ready, archived, not an agent, or not read yet', () => {
    expect(agentIsMoving(READY().detail, NOW)).toBe(false);
    expect(agentIsMoving(agentCase({ n: 61, archived: true, enrollments: [{ state: 'pending' }] }).detail, NOW)).toBe(false);
    expect(agentIsMoving(agentCase({ n: 61, pullClient: 'claude_code_session', tokens: [agentToken(1, CID)] }).detail, NOW)).toBe(false);
    expect(agentIsMoving(undefined, NOW)).toBe(false);
  });
});

// ------------------------------------------------------------------------- the panel, rendered

function panel(c: AgentCase, canManage = true): string {
  return renderScreen(newClient(), createElement(AgentLifecyclePanel, {
    connection: c.connection, detail: c.detail, canManage, nowMs: NOW,
  }));
}

/** The text a reader sees, with the commands and the identifiers they copy taken out. */
function readable(markup: string): string {
  return markup
    .replace(/<(input|textarea)\b[^>]*>(?:[^<]*<\/textarea>)?/g, ' ')
    .replace(/<code>[^<]*<\/code>/g, ' ')
    .replace(/<time[^>]*>[^<]*<\/time>/g, ' ')
    .replace(/<[^>]+>/g, ' ');
}

const ALLOWED_LATIN = new Set(['SSH', 'Claude', 'Code', 'codex', 'Ubuntu', 'API', 'OpenRouter', 'SHA']);

function foreignLatin(text: string): string[] {
  return [...new Set((text.match(/[A-Za-z]+/g) ?? []).filter((word) => !ALLOWED_LATIN.has(word)))];
}

describe('what the panel shows and offers', () => {
  it('lists the seven steps in order, with the four statuses each under its own name', () => {
    const markup = panel(READY());
    const at_ = AGENT_STEP_ORDER.map((id) => markup.indexOf(`data-agent-step="${id}"`));
    expect(at_.every((position) => position >= 0)).toBe(true);
    expect([...at_].sort((a, b) => a - b)).toEqual(at_);
    for (const label of [STEP_LABELS.installed, STEP_LABELS.login, STEP_LABELS.authorised, STEP_LABELS.probe]) {
      expect(markup.split(label).length - 1, label).toBeGreaterThanOrEqual(1);
    }
    expect(markup).toContain('data-agent-ready="yes"');
    expect(markup).toContain('Четыре состояния клиента независимы');
  });

  it('is drawn only for an agent: a pull connection for a Claude Code session gets the token panel and nothing here', () => {
    const session = agentCase({ n: 61, pullClient: 'claude_code_session', tokens: [agentToken(1, CID)] });
    expect(panel(session)).not.toContain('data-agent-lifecycle');
    expect(renderScreen(newClient(), createElement(AgentLifecyclePanel, {
      connection: READY().connection, detail: undefined, canManage: true, nowMs: NOW,
    }))).not.toContain('data-agent-lifecycle');
  });

  it('offers a new command, never the old one, while the registration waits, has expired or has not begun', () => {
    const start = panel(agentCase({ n: 61 }));
    expect(start).toContain('data-agent-command-start');
    expect(start).toContain('Получить команду');
    const waiting = panel(agentCase({ n: 61, enrollments: [{ state: 'pending' }] }));
    expect(waiting).toContain('Ожидает регистрации');
    expect(waiting).toContain('Новая команда');
    const expired = panel(agentCase({ n: 61, enrollments: [{ state: 'expired' }] }));
    expect(expired).toContain('Команда устарела');
    expect(expired).toContain('Новая команда');
    for (const markup of [start, waiting, expired]) {
      expect(markup).not.toContain('data-agent-command-shown');
      expect(markup).not.toContain('<textarea');
    }
    expect(panel(READY())).not.toContain('data-agent-command-start');
  });

  it('shows the official login commands for a client that is not signed in, and «Проверить снова»', () => {
    const c = agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('login_required'), codex('unknown')] })] });
    const markup = panel(c);
    expect(markup).toContain('data-agent-login-guidance');
    expect(markup).toContain(`value="${LOGIN_COMMANDS.claude}"`);
    expect(markup).toContain(`value="${LOGIN_COMMANDS.codex}"`);
    expect(LOGIN_COMMANDS.claude).toBe('sudo -u pdf-agent -H claude auth login');
    expect(LOGIN_COMMANDS.codex).toBe('sudo -u pdf-agent -H codex login --device-auth');
    expect(markup).toContain('Проверить снова');
    expect(markup).toContain('data-agent-recheck');
    // No password, no key and no code is asked for here.
    expect(markup).not.toContain('type="password"');
  });

  it('shows no login guidance for a client that is signed in, but still names it', () => {
    const markup = panel(READY());
    expect(markup).not.toContain('data-agent-login-guidance');
    expect(markup).toContain('data-agent-cli="claude"');
    expect(markup).toContain('data-agent-cli-auth="valid"');
    expect(markup).toContain('вход действителен');
  });

  it('tells a missing client apart from a client that needs signing in', () => {
    const missing = panel(agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [] })] }));
    expect(missing).toContain('data-agent-missing-cli');
    expect(missing).toContain('Клиент командной строки не найден');
    expect(missing).not.toContain('data-agent-login-guidance');
    const login = panel(agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('login_required')] })] }));
    expect(login).toContain('data-agent-login-guidance');
    expect(login).not.toContain('data-agent-missing-cli');
  });

  it('says an offline agent is offline and when it was last seen', () => {
    const markup = panel(agentCase({ n: 61, tokens: [agentToken(1, CID, { online: false, last_seen_at: at(10 * MINUTE) })] }));
    expect(markup).toContain('data-agent-step-reason="offline"');
    expect(markup).toContain('Агент не в сети');
    expect(markup).toContain('Последнее обращение');
  });

  it('shows the administrator’s mark with the R-149b note, and lets only an administrator change it', () => {
    const unmarked = panel(READY());
    expect(unmarked).toContain('data-agent-mark="not_set"');
    expect(unmarked).toContain(INTEGRATION_NOTE);
    expect(unmarked).toContain('Отметить как разрешённое');
    const marked = panel(agentCase({ n: 61, tokens: [agentToken(1, CID)], mark: true }));
    expect(marked).toContain('data-agent-mark="set"');
    expect(marked).toContain('Снять отметку');
    const expert = panel(agentCase({ n: 61, tokens: [agentToken(1, CID)], mark: true }), false);
    expect(expert).toContain(INTEGRATION_NOTE);
    expect(expert).not.toContain('data-agent-mark-action');
  });

  it('says the mark is not a login, not an install and not a probe, in the note itself', () => {
    expect(INTEGRATION_NOTE).toContain('Отметку ставит администратор');
    expect(INTEGRATION_NOTE).toContain('отметку из входа клиента не выводит');
    expect(INTEGRATION_NOTE).toContain('не копирует учётные данные');
    expect(INTEGRATION_NOTE).toContain('не обходит лимиты провайдера');
    expect(INTEGRATION_NOTE).toContain('не имитирует человека');
  });

  it('offers no action to an expert, who still sees every state', () => {
    for (const c of [
      agentCase({ n: 61 }),
      agentCase({ n: 61, enrollments: [{ state: 'expired' }] }),
      agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('login_required')] })] }),
      agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [] })] }),
      READY(),
    ]) {
      const markup = panel(c, false);
      expect(markup).toContain('data-agent-lifecycle');
      for (const control of ['data-agent-command-start', 'data-agent-recheck', 'data-agent-mark-action', 'data-agent-move-open', 'data-agent-copy-button']) {
        expect(markup, control).not.toContain(control);
      }
    }
  });

  it('draws nothing in English apart from named products, in any state', () => {
    for (const c of [
      agentCase({ n: 61 }),
      agentCase({ n: 61, enrollments: [{ state: 'pending' }] }),
      agentCase({ n: 61, enrollments: [{ state: 'expired' }] }),
      agentCase({ n: 61, tokens: [unseenToken(1, CID)] }),
      agentCase({ n: 61, tokens: [agentToken(1, CID, { online: false })] }),
      agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [] })] }),
      agentCase({ n: 61, tokens: [agentToken(1, CID, { clis: [claude('login_required'), codex('unknown')] })] }),
      agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: { outcome: 'model_mismatch' } }),
      agentCase({ n: 61, tokens: [agentToken(1, CID)], probe: null }),
      agentCase({ n: 61, tokens: [agentToken(1, CID)], mark: true }),
    ]) {
      expect(foreignLatin(readable(panel(c)))).toEqual([]);
    }
  });
});
