/**
 * The agent connections the `connect-remote-agent` tests render (`EXEC2-WEB-WIZARD-01`).
 *
 * Every instant is relative to one fixed `NOW`, which the tests pass to the code under test, so a rule
 * about a minute or a quarter of an hour is judged against a clock nobody moves. Every server value is
 * Cyrillic, an identifier or a contract enum, for the reason `rendered-language.guard.test.ts` gives:
 * a Latin word left in the output is chrome the application wrote.
 */

import type {
  ExecutorAgentInstall,
  ExecutorConnection,
  ExecutorConnectionDetail,
  ExecutorEnrollmentMetadata,
  ExecutorProbe,
  ExecutorRevision,
  IssuedExecutorEnrollment,
  RunnerCliHealth,
  RunnerTokenMetadata,
} from '@/shared/api';

import { ADMIN_UID, PINNED, connectionId, probeId, revisionId, tokenId, ulid } from './executor-fixtures';

export { ADMIN_UID, PINNED };

export const NOW = Date.parse('2026-11-02T12:00:00Z');
export const MINUTE = 60_000;
export const HOUR = 60 * MINUTE;
export const DAY = 24 * HOUR;
export const at = (milliseconds: number): string => new Date(NOW - milliseconds).toISOString();
export const later = (milliseconds: number): string => new Date(NOW + milliseconds).toISOString();

export const enrollmentId = (n: number): `exen_${string}` => `exen_${ulid(n)}`;
export const installId = (n: number): `exai_${string}` => `exai_${ulid(n)}`;

export function enrollment(
  n: number,
  connection: string,
  over: Partial<ExecutorEnrollmentMetadata> = {},
): ExecutorEnrollmentMetadata {
  return {
    enrollment_id: enrollmentId(n),
    connection_id: connection,
    created_at: at(5 * MINUTE),
    created_by: ADMIN_UID,
    expires_at: later(10 * MINUTE),
    secret_prefix: 'секрет-А1',
    state: 'pending',
    ...over,
  };
}

/** A client as the agent reports it: installed, with a version, and the state of its login. */
export const claude = (auth: RunnerCliHealth['auth_state'], installed = true): RunnerCliHealth => ({
  cli: 'claude', installed, auth_state: installed ? auth : 'unknown', ...(installed ? { version: '2.0.1' } : {}),
});
export const codex = (auth: RunnerCliHealth['auth_state'], installed = true): RunnerCliHealth => ({
  cli: 'codex', installed, auth_state: installed ? auth : 'unknown', ...(installed ? { version: '0.9.4' } : {}),
});

/** A token of a registered agent: live, seen ten seconds ago, health reported. */
export function agentToken(
  n: number,
  connection: string,
  over: Partial<RunnerTokenMetadata> = {},
): RunnerTokenMetadata {
  return {
    token_id: tokenId(n),
    connection_id: connection,
    token_prefix: `токен-А${n}`,
    created_at: at(HOUR),
    created_by: ADMIN_UID,
    expires_at: later(28 * DAY),
    last_seen_at: at(10_000),
    last_seen_address: '203.0.113.9',
    online: true,
    agent_version: '1.0.0',
    concurrency: 1,
    execution_profile: 'command',
    features: [],
    health_reported_at: at(20_000),
    clis: [claude('valid')],
    ...over,
  };
}

/** A token that was just redeemed: no call yet, so no `online`, no `last_seen_at`, no health. */
export function unseenToken(n: number, connection: string, over: Partial<RunnerTokenMetadata> = {}): RunnerTokenMetadata {
  const token: RunnerTokenMetadata = { ...agentToken(n, connection), ...over };
  delete token.online;
  delete token.last_seen_at;
  delete token.last_seen_address;
  delete token.clis;
  delete token.agent_version;
  delete token.concurrency;
  delete token.execution_profile;
  delete token.features;
  delete token.health_reported_at;
  return token;
}

/** The same token as an old stand would send it: health reported, but no server-side `online`. */
export function withoutOnline(token: RunnerTokenMetadata): RunnerTokenMetadata {
  const copy: RunnerTokenMetadata = { ...token };
  delete copy.online;
  return copy;
}

export interface AgentOptions {
  readonly n: number;
  readonly name?: string;
  readonly pullClient?: 'agent' | 'claude_code_session';
  readonly enrollments?: readonly Partial<ExecutorEnrollmentMetadata>[];
  readonly tokens?: readonly RunnerTokenMetadata[];
  /** `null`: no probe has ever run. */
  readonly probe?: Partial<ExecutorProbe> | null;
  readonly mark?: boolean;
  readonly archived?: boolean;
}

export interface AgentCase {
  readonly connection: ExecutorConnection;
  readonly detail: ExecutorConnectionDetail;
}

/** One agent connection with its current revision, enrollments, tokens and latest probe. */
export function agentCase(options: AgentOptions): AgentCase {
  const cid = connectionId(options.n);
  const rid = revisionId(options.n);
  const probe: ExecutorProbe | undefined = options.probe === null ? undefined : {
    probe_id: probeId(options.n),
    connection_id: cid,
    revision_id: rid,
    state: 'finished',
    requested_at: at(30 * MINUTE),
    requested_by: ADMIN_UID,
    started_at: at(29 * MINUTE),
    finished_at: at(28 * MINUTE),
    outcome: 'ok',
    reported_model: 'шлюзовая-основная',
    identity_basis: 'declared',
    rate_check: 'not_metered',
    ...options.probe,
  };
  const revision: ExecutorRevision = {
    revision_id: rid,
    connection_id: cid,
    revision_no: 1,
    created_at: at(2 * HOUR),
    created_by: ADMIN_UID,
    pin_id: 'модель-основная',
    gateway_model: 'шлюзовая-основная',
    billing: 'not_metered',
    allow_client_documents: false,
    timeout_seconds: 120,
    pull_client: options.pullClient ?? 'agent',
    answer_deadline_seconds: 600,
    max_claimed_tasks: 1,
    ...(probe === undefined ? {} : { latest_probe: probe }),
  };
  const connection: ExecutorConnection = {
    connection_id: cid,
    kind: 'pull',
    display_name: options.name ?? 'Агент на сервере распознавания',
    created_at: at(3 * HOUR),
    created_by: ADMIN_UID,
    secrets: [],
    routed_work_kinds: [],
    current_revision_id: rid,
    current_revision_no: 1,
    ...(options.mark === true ? { integration_authorisation: { authorised_at: at(HOUR), authorised_by: ADMIN_UID } } : {}),
    ...(options.archived === true ? { archived_at: at(MINUTE) } : {}),
  };
  const enrollments = (options.enrollments ?? []).map((item, index) => enrollment(options.n * 4 + index, cid, item));
  return {
    connection,
    detail: {
      connection,
      revisions: [revision],
      probes: probe === undefined ? [] : [probe],
      runner_tokens: [...(options.tokens ?? [])],
      open_task_count: 0,
      ...(enrollments.length === 0 ? {} : { enrollments }),
    },
  };
}

/** The answer of `issueExecutorEnrollment`: the command carries the secret, and nothing else does. */
export const SECRET = 'секрет-одноразовый-9f8e';
export function issued(connection: string, over: Partial<IssuedExecutorEnrollment> = {}): IssuedExecutorEnrollment {
  return {
    command: `команда-установки --секрет ${SECRET}`,
    secret: SECRET,
    package_version: '1.2.3',
    package_sha256: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
    enrollment: enrollment(91, connection, { state: 'pending' }),
    ...over,
  };
}

export const FINGERPRINT = 'отпечаток-узла-семь-в-ряд';

/** One install session over SSH. */
export function install(connection: string, over: Partial<ExecutorAgentInstall> = {}): ExecutorAgentInstall {
  return {
    install_id: installId(1),
    connection_id: connection,
    access: 'generated_key',
    ssh_host: 'узел.пример',
    ssh_port: 22,
    ssh_user: 'установщик',
    state: 'requested',
    created_at: at(MINUTE),
    created_by: ADMIN_UID,
    updated_at: at(MINUTE),
    authorized_keys_line: 'строка-ключа-для-файла',
    public_key: 'открытый-ключ-стенда',
    ...over,
  };
}
