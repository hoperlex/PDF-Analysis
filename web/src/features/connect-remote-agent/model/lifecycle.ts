/**
 * The lifecycle of an agent connection, read from the connection's detail
 * (`EXEC2-WEB-WIZARD-01`, ADR-0026 decisions 4, 5, 8 and 9).
 *
 *     ожидает регистрации → агент в сети → клиент найден → вход действителен / нужен вход
 *       → проба пройдена → готово
 *
 * Both install paths end in the same enrollment, so one function reads both: it looks at the
 * connection's enrollments, its runner tokens with the health the agent reported on them (`online`,
 * `clis`), the administrator's mark and the latest probe of the current revision. Nothing here
 * calls the stand; the panel re-reads the detail and this function says what it now means.
 *
 * **Four statuses stay distinct** (decision 8, `R-149b`): the client is installed, its login is
 * valid, the administrator marked it authorised for this integration, and the model probe passed.
 * Each is its own step with its own reason, and no step is derived from another one: a valid login
 * does not set the mark, the mark does not make a client installed, and a passed probe does not
 * stand in for a login. The mark is **not** a gate of «готово» — the stand records it and does not
 * enforce it — so a ready agent without the mark says so beside the step and stays ready.
 *
 * Pure: the clock is a parameter, and every function takes data and returns data, so each rule is
 * a function a test calls.
 */

import type {
  ExecutorConnection,
  ExecutorConnectionDetail,
  ExecutorEnrollmentMetadata,
  ExecutorProbe,
  ExecutorRevision,
  RunnerCliAuthState,
  RunnerCliName,
  RunnerTokenMetadata,
} from '@/shared/api';
import {
  currentRevision,
  runnerTokenIsLive,
  runnerTokenIsOnline,
} from '@/entities/executor-connection';

/** How long after an agent registered the panel keeps re-reading while it is not yet ready. */
export const JOIN_WINDOW_MS = 15 * 60_000;

export type AgentStepId =
  | 'registration' | 'online' | 'installed' | 'login' | 'authorised' | 'probe' | 'ready';

export const AGENT_STEP_ORDER: readonly AgentStepId[] = [
  'registration', 'online', 'installed', 'login', 'authorised', 'probe', 'ready',
];

/**
 * `done`: satisfied. `waiting`: nothing is wrong, the step has not happened yet. `attention`:
 * somebody has to act. `inert`: a mark nobody has set (it is not a failure).
 */
export type AgentStepState = 'done' | 'waiting' | 'attention' | 'inert';

/** The closed set of reasons per step; each has a sentence in `step-sentences.ts`. */
export interface AgentStepReasons {
  readonly registration: 'not_started' | 'waiting' | 'expired' | 'replaced' | 'token_gone' | 'registered';
  readonly online: 'waiting_registration' | 'never_seen' | 'offline' | 'online';
  readonly installed: 'no_report' | 'missing' | 'found';
  readonly login: 'no_client' | 'unknown' | 'login_required' | 'valid';
  readonly authorised: 'not_set' | 'set';
  readonly probe: 'not_requested' | 'open' | 'failed' | 'stale' | 'passed';
  readonly ready: 'not_ready' | 'ready';
}

export interface AgentStep<K extends AgentStepId = AgentStepId> {
  readonly id: K;
  readonly state: AgentStepState;
  readonly reason: AgentStepReasons[K];
}

export type AgentSteps = { readonly [K in AgentStepId]: AgentStep<K> };

/** One official client as the agent last reported it. */
export interface CliReading {
  readonly cli: RunnerCliName;
  readonly installed: boolean;
  readonly version: string | null;
  readonly auth: RunnerCliAuthState;
}

export interface AgentLifecycle {
  readonly steps: AgentSteps;
  /** The newest live runner token: the agent the connection is served by. */
  readonly token: RunnerTokenMetadata | null;
  /** The newest enrollment, whatever its state. */
  readonly enrollment: ExecutorEnrollmentMetadata | null;
  /** The newest enrollment that is still waiting to be used. */
  readonly pendingEnrollment: ExecutorEnrollmentMetadata | null;
  readonly clis: readonly CliReading[];
  readonly revision: ExecutorRevision | undefined;
  readonly probe: ExecutorProbe | undefined;
  /** When the agent last reported its health, if it did. */
  readonly healthReportedAt: string | null;
  /**
   * Live tokens older than the token of the newest redeemed enrollment, once that new agent is in
   * the network: the prior agent's tokens an administrator may now revoke (decision 9).
   */
  readonly supersededTokens: readonly RunnerTokenMetadata[];
  readonly ready: boolean;
}

function instant(text: string | undefined): number | null {
  if (text === undefined) return null;
  const parsed = Date.parse(text);
  return Number.isNaN(parsed) ? null : parsed;
}

function newestFirst<T extends { readonly created_at: string }>(items: readonly T[]): T[] {
  return [...items].sort((left, right) =>
    left.created_at < right.created_at ? 1 : left.created_at > right.created_at ? -1 : 0);
}

/**
 * An enrollment's state at `nowMs`. The server derives `state` at read time; a detail read a while
 * ago can still say `pending` for a grant that has since run out, so the expiry is judged here too.
 */
export function enrollmentIsExpired(enrollment: ExecutorEnrollmentMetadata, nowMs: number): boolean {
  if (enrollment.state === 'expired') return true;
  if (enrollment.state !== 'pending') return false;
  const expires = instant(enrollment.expires_at);
  return expires !== null && expires <= nowMs;
}

export function enrollmentIsPending(enrollment: ExecutorEnrollmentMetadata, nowMs: number): boolean {
  return enrollment.state === 'pending' && !enrollmentIsExpired(enrollment, nowMs);
}

/** Whether the agent behind a token is in the network now: the server's word, else the last call. */
export function tokenIsOnline(token: RunnerTokenMetadata, nowMs: number): boolean {
  if (!runnerTokenIsLive(token, nowMs)) return false;
  return token.online ?? runnerTokenIsOnline(token, nowMs);
}

function readClis(token: RunnerTokenMetadata | null): readonly CliReading[] {
  return (token?.clis ?? []).map((item) => ({
    cli: item.cli,
    installed: item.installed,
    version: item.version ?? null,
    auth: item.auth_state,
  }));
}

/**
 * Whether the connection is an agent connection: a `pull` connection whose current settings name
 * the agent as the client, or one that has ever been given an enrollment. A `pull` connection
 * meant for a Claude Code session has neither, and the token panel is its whole story.
 */
export function isAgentConnection(
  connection: Pick<ExecutorConnection, 'kind' | 'current_revision_id'>,
  detail: ExecutorConnectionDetail | undefined,
): boolean {
  if (connection.kind !== 'pull') return false;
  if ((detail?.enrollments ?? []).length > 0) return true;
  const revision = detail === undefined ? undefined : currentRevision(connection, detail.revisions);
  return revision?.pull_client === 'agent';
}

export function agentLifecycle(
  connection: ExecutorConnection,
  detail: ExecutorConnectionDetail,
  nowMs: number,
): AgentLifecycle {
  const tokens = newestFirst(detail.runner_tokens ?? []);
  const liveTokens = tokens.filter((token) => runnerTokenIsLive(token, nowMs));
  const token = liveTokens[0] ?? null;
  const enrollments = newestFirst(detail.enrollments ?? []);
  const latest = enrollments[0] ?? null;
  const pending = enrollments.find((item) => enrollmentIsPending(item, nowMs)) ?? null;
  const revision = currentRevision(connection, detail.revisions);
  const probe = revision?.latest_probe;
  const clis = readClis(token);
  const archived = connection.archived_at !== undefined;

  // ---- registration
  let registration: AgentStepReasons['registration'];
  if (token !== null) registration = 'registered';
  else if (latest === null) registration = 'not_started';
  else if (enrollmentIsPending(latest, nowMs)) registration = 'waiting';
  else if (enrollmentIsExpired(latest, nowMs)) registration = 'expired';
  else if (latest.state === 'revoked') registration = 'replaced';
  else registration = 'token_gone';

  // ---- online
  let online: AgentStepReasons['online'];
  if (token === null) online = 'waiting_registration';
  else if (tokenIsOnline(token, nowMs)) online = 'online';
  else online = token.last_seen_at === undefined ? 'never_seen' : 'offline';

  // ---- installed
  let installed: AgentStepReasons['installed'];
  if (token === null || token.clis === undefined) installed = 'no_report';
  else installed = clis.some((item) => item.installed) ? 'found' : 'missing';

  // ---- login
  const installedClis = clis.filter((item) => item.installed);
  let login: AgentStepReasons['login'];
  if (installed !== 'found') login = 'no_client';
  else if (installedClis.some((item) => item.auth === 'valid')) login = 'valid';
  else if (installedClis.some((item) => item.auth === 'login_required')) login = 'login_required';
  else login = 'unknown';

  // ---- authorised (the administrator's mark; no other step reads it)
  const authorised: AgentStepReasons['authorised'] =
    connection.integration_authorisation === undefined ? 'not_set' : 'set';

  // ---- probe
  let probeReason: AgentStepReasons['probe'];
  if (probe === undefined) probeReason = 'not_requested';
  else if (probe.state !== 'finished') probeReason = 'open';
  else if (probe.outcome !== 'ok') probeReason = 'failed';
  else {
    // A probe that passed before the current agent registered tested another host.
    const finished = instant(probe.finished_at);
    const registered = token === null ? null : instant(token.created_at);
    probeReason = finished !== null && registered !== null && registered > finished ? 'stale' : 'passed';
  }

  const ready =
    !archived && registration === 'registered' && online === 'online' && installed === 'found' &&
    login === 'valid' && probeReason === 'passed';

  const steps: AgentSteps = {
    registration: {
      id: 'registration', reason: registration,
      state: registration === 'registered' ? 'done'
        : registration === 'waiting' || registration === 'not_started' ? 'waiting' : 'attention',
    },
    online: {
      id: 'online', reason: online,
      state: online === 'online' ? 'done' : online === 'offline' ? 'attention' : 'waiting',
    },
    installed: {
      id: 'installed', reason: installed,
      state: installed === 'found' ? 'done' : installed === 'missing' ? 'attention' : 'waiting',
    },
    login: {
      id: 'login', reason: login,
      state: login === 'valid' ? 'done' : login === 'login_required' ? 'attention' : 'waiting',
    },
    authorised: { id: 'authorised', reason: authorised, state: authorised === 'set' ? 'done' : 'inert' },
    probe: {
      id: 'probe', reason: probeReason,
      state: probeReason === 'passed' ? 'done' : probeReason === 'failed' ? 'attention' : 'waiting',
    },
    ready: { id: 'ready', reason: ready ? 'ready' : 'not_ready', state: ready ? 'done' : 'waiting' },
  };

  return {
    steps,
    token,
    enrollment: latest,
    pendingEnrollment: pending,
    clis,
    revision,
    probe,
    healthReportedAt: token?.health_reported_at ?? null,
    supersededTokens: supersededTokensOf(tokens, liveTokens, enrollments, nowMs),
    ready,
  };
}

/**
 * The prior agent's live tokens, once the newest redeemed enrollment's agent is in the network
 * (decision 9: «the old token is revoked once the new agent is online»). Before that the old agent
 * is the only one serving, and nothing is offered.
 */
function supersededTokensOf(
  tokens: readonly RunnerTokenMetadata[],
  liveTokens: readonly RunnerTokenMetadata[],
  enrollments: readonly ExecutorEnrollmentMetadata[],
  nowMs: number,
): readonly RunnerTokenMetadata[] {
  const redeemed = enrollments.find((item) => item.state === 'redeemed' && item.runner_token_id !== undefined);
  if (redeemed === undefined) return [];
  const fresh = tokens.find((item) => item.token_id === redeemed.runner_token_id);
  if (fresh === undefined || !tokenIsOnline(fresh, nowMs)) return [];
  return liveTokens.filter((item) => item.token_id !== fresh.token_id && item.created_at < fresh.created_at);
}

/**
 * The first step that is not done on the way to «готово», or `ready`. The wizard's progress line and
 * the panel's summary read it; the mark is not on the way and never named here.
 */
export function currentStep(lifecycle: AgentLifecycle): AgentStep {
  for (const id of ['registration', 'online', 'installed', 'login', 'probe'] as const) {
    const step = lifecycle.steps[id];
    if (step.state !== 'done') return step;
  }
  return lifecycle.steps.ready;
}

/**
 * Whether the detail is worth re-reading on a timer: a grant is waiting to be used, or an agent
 * registered a short while ago and is not yet ready. Bounded on both sides — an offline agent that
 * registered yesterday, or a ready one, schedules nothing — so the poll ends by itself.
 */
export function agentIsMoving(detail: ExecutorConnectionDetail | undefined, nowMs: number): boolean {
  if (detail === undefined) return false;
  const connection = detail.connection;
  if (connection.archived_at !== undefined || !isAgentConnection(connection, detail)) return false;
  const lifecycle = agentLifecycle(connection, detail, nowMs);
  if (lifecycle.pendingEnrollment !== null) return true;
  if (lifecycle.ready || lifecycle.token === null) return false;
  const registered = instant(lifecycle.token.created_at);
  return registered !== null && nowMs - registered < JOIN_WINDOW_MS;
}
