/**
 * The connections the «Подключения» and «Назначения» tests, the language guard and the
 * contrast census render (`EXEC-HTTP-01`).
 *
 * Every value is Cyrillic, an identifier or a contract enum, for the reason
 * `rendered-language.guard.test.ts` gives: a Latin word left in the output is chrome the
 * application wrote. The cases are written out, not derived from the contract, so a member the
 * contract gains is a member nobody has looked at and the guard's coverage assertion says so.
 *
 * Times are relative to the moment the fixture is built, so the seven-day notice has changes to
 * name and the older rows fall outside it.
 */

import type {
  ExecutorConnection,
  ExecutorConnectionDetail,
  ExecutorConnectionList,
  ExecutorPinnedModel,
  ExecutorProbe,
  ExecutorProbeOutcome,
  ExecutorRevision,
  ExecutorRoute,
  ExecutorSecretMetadata,
} from '@/shared/api';
import { queryKeys } from '@/shared/api';

import type { newClient } from '../screens/harness';

type Client = ReturnType<typeof newClient>;

const CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const BASE = '01J9ZQ8K7NHVXW3T2R5M6P4Q';

/** A well-formed ULID suffix, distinct per `n` (0 to 1023). */
export function ulid(n: number): string {
  return `${BASE}${CROCKFORD[(n >> 5) & 31]}${CROCKFORD[n & 31]}`;
}

export const connectionId = (n: number): `exc_${string}` => `exc_${ulid(n)}`;
export const revisionId = (n: number): `excr_${string}` => `excr_${ulid(n)}`;
export const probeId = (n: number): `epb_${string}` => `epb_${ulid(n)}`;
export const secretId = (n: number): `exs_${string}` => `exs_${ulid(n)}`;
export const ADMIN_UID = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
export const ago = (milliseconds: number): string => new Date(Date.now() - milliseconds).toISOString();

export const PINNED: readonly ExecutorPinnedModel[] = [
  { pin_id: 'модель-основная', input_per_mtok_usd: 3, output_per_mtok_usd: 15 },
  { pin_id: 'модель-быстрая', input_per_mtok_usd: 1, output_per_mtok_usd: 5 },
];

export function revision(over: Partial<ExecutorRevision> & Pick<ExecutorRevision, 'connection_id' | 'revision_id'>): ExecutorRevision {
  return {
    revision_no: 1,
    created_at: ago(2 * HOUR),
    created_by: ADMIN_UID,
    pin_id: 'модель-основная',
    gateway_model: 'шлюзовая-основная',
    billing: 'metered',
    allow_client_documents: false,
    timeout_seconds: 120,
    ...over,
  };
}

export function probe(over: Partial<ExecutorProbe> & Pick<ExecutorProbe, 'probe_id' | 'connection_id' | 'revision_id'>): ExecutorProbe {
  const state = over.state ?? 'finished';
  return {
    state,
    requested_at: ago(90 * 60_000),
    requested_by: ADMIN_UID,
    // A probe that is still open has not finished, and one that was only requested has not started.
    ...(state === 'requested' ? {} : { started_at: ago(89 * 60_000) }),
    ...(state === 'finished' ? { finished_at: ago(88 * 60_000) } : {}),
    ...over,
  };
}

export function secret(over: Partial<ExecutorSecretMetadata> & Pick<ExecutorSecretMetadata, 'secret_id' | 'connection_id'>): ExecutorSecretMetadata {
  return {
    purpose: 'api_key',
    last4: '4417',
    kid: 'кольцо-1',
    bound_to_current_revision: true,
    set_at: ago(3 * HOUR),
    set_by: ADMIN_UID,
    ...over,
  };
}

export interface ExecutorCase {
  readonly connection: ExecutorConnection;
  readonly detail: ExecutorConnectionDetail;
}

interface CaseOptions {
  readonly n: number;
  readonly kind?: ExecutorConnection['kind'];
  readonly name: string;
  readonly revision?: Partial<ExecutorRevision> | null;
  readonly probe?: Partial<ExecutorProbe> | null;
  readonly secrets?: readonly Partial<ExecutorSecretMetadata>[];
  readonly archived?: boolean;
  readonly routed?: boolean;
  readonly createdAt?: string;
}

const HTTP = {
  api_flavour: 'openai_chat', base_url: 'https://шлюз.example/api/v1', transport: 'direct', max_parallel_calls: 2,
} as const;
const SSH = {
  ssh_host: 'узел.example', ssh_port: 22, ssh_user: 'исполнитель', ssh_profile: 'claude_code_headless',
} as const;
const PULL = { pull_client: 'claude_code_session', answer_deadline_seconds: 600, max_claimed_tasks: 1 } as const;

/** One connection with its current revision, latest probe and secrets, assembled consistently. */
export function executorCase(options: CaseOptions): ExecutorCase {
  const kind = options.kind ?? 'http_api';
  const cid = connectionId(options.n);
  const rid = revisionId(options.n);
  const settings = kind === 'http_api' ? HTTP : kind === 'ssh_command' ? SSH : PULL;
  const secrets = (options.secrets ?? []).map((item, index) =>
    secret({ secret_id: secretId(options.n * 4 + index), connection_id: cid, ...item }));
  const latest = options.probe === null || options.probe === undefined
    ? undefined
    : probe({
      probe_id: probeId(options.n), connection_id: cid, revision_id: rid,
      ...(secrets[0] === undefined ? {} : { secret_id: secrets[0].secret_id }),
      ...options.probe,
    });
  const current = options.revision === null
    ? undefined
    : revision({
      connection_id: cid, revision_id: rid, ...settings, ...options.revision,
      ...(latest === undefined ? {} : { latest_probe: latest }),
    });
  const connection: ExecutorConnection = {
    connection_id: cid,
    kind,
    display_name: options.name,
    created_at: options.createdAt ?? ago(4 * HOUR),
    created_by: ADMIN_UID,
    secrets,
    routed_work_kinds: options.routed === true ? ['text_analysis'] : [],
    ...(options.archived === true ? { archived_at: ago(HOUR) } : {}),
    ...(current === undefined ? {} : { current_revision_id: rid, current_revision_no: current.revision_no }),
  };
  return {
    connection,
    detail: {
      connection,
      revisions: current === undefined ? [] : [current],
      probes: latest === undefined ? [] : [latest],
    },
  };
}

const OK = { outcome: 'ok', reported_model: 'шлюзовая-основная', identity_basis: 'reported', latency_ms: 840, rate_check: 'checked' } as const;

/** The connection that can be routed: a finished `ok` probe on its current, readable key. */
export const READY = executorCase({
  n: 1, name: 'Основной шлюз', secrets: [{}], probe: OK, routed: true,
});

/** A second routable connection, for the standby. */
export const SPARE = executorCase({
  n: 2, name: 'Запасной шлюз', secrets: [{}], probe: { ...OK, rate_check: 'not_reported' },
  revision: { api_flavour: 'anthropic_messages', billing: 'not_metered', allow_client_documents: true },
});

/** The fifteen outcomes, one connection each; written out, not derived from the contract. */
export const OUTCOME_CASES: readonly [ExecutorProbeOutcome, ExecutorCase][] = [
  ['ok', READY],
  ['ip_refused', executorCase({ n: 10, name: 'Шлюз за списком адресов', secrets: [{}], probe: { outcome: 'ip_refused', http_status: 403 } })],
  ['credential_refused', executorCase({ n: 11, name: 'Шлюз с отклонённым ключом', secrets: [{}], probe: { outcome: 'credential_refused', http_status: 401 } })],
  ['model_mismatch', executorCase({ n: 12, name: 'Шлюз с другой моделью', secrets: [{}], probe: { outcome: 'model_mismatch', reported_model: 'другая-модель', identity_basis: 'reported' } })],
  ['rate_mismatch', executorCase({ n: 13, name: 'Шлюз с чужим тарифом', secrets: [{}], probe: { outcome: 'rate_mismatch', rate_check: 'mismatch', reported_model: 'шлюзовая-основная' } })],
  ['timeout', executorCase({ n: 14, name: 'Шлюз без ответа', secrets: [{}], probe: { outcome: 'timeout', detail: 'ответ не пришёл за отведённое время' }, revision: { transport: 'vpn' } })],
  ['unreachable', executorCase({ n: 15, name: 'Недоступный шлюз', secrets: [{}], probe: { outcome: 'unreachable' } })],
  ['protocol_error', executorCase({ n: 16, name: 'Шлюз с чужим ответом', secrets: [{}], probe: { outcome: 'protocol_error', http_status: 200 } })],
  ['secret_unreadable', executorCase({ n: 17, name: 'Шлюз с чужим адресом ключа', secrets: [{ bound_to_current_revision: false }], probe: { outcome: 'secret_unreadable' } })],
  ['host_key_unpinned', executorCase({
    n: 18, kind: 'ssh_command', name: 'Машина с командой',
    secrets: [{ purpose: 'ssh_private_key', last4: '5521', public_key: 'открытый-ключ-для-проверки' }],
    probe: { outcome: 'host_key_unpinned', observed_host_key: 'наблюдаемый-отпечаток-узла' },
  })],
  ['host_key_changed', executorCase({
    n: 19, kind: 'ssh_command', name: 'Машина со сменой отпечатка',
    secrets: [{ purpose: 'ssh_private_key', last4: '7790', public_key: 'открытый-ключ-для-проверки' }],
    revision: { ssh_profile: 'custom_command', host_key: 'закреплённый-отпечаток-узла', host_key_fingerprint: 'отпечаток-узла-закреплённый' },
    probe: { outcome: 'host_key_changed', observed_host_key: 'новый-отпечаток-узла' },
  })],
  ['no_runner_online', executorCase({ n: 20, kind: 'pull', name: 'Клиент без связи', probe: { outcome: 'no_runner_online' } })],
  ['destination_refused', executorCase({ n: 21, name: 'Шлюз с закрытым адресом', secrets: [{}], probe: { outcome: 'destination_refused' } })],
  ['kind_not_served', executorCase({
    n: 22, kind: 'pull', name: 'Агент распознавания', revision: { pull_client: 'agent' },
    probe: { outcome: 'kind_not_served', identity_basis: 'declared', reported_model: 'заявленная-модель' },
  })],
  ['no_worker', executorCase({ n: 23, name: 'Шлюз без процесса', secrets: [{}], probe: { outcome: 'no_worker' } })],
];

/** The other shapes a card takes: probe states, transports, a tunnel, archive, no settings. */
export const SHAPE_CASES: readonly ExecutorCase[] = [
  executorCase({ n: 30, name: 'Шлюз ждёт проверки', secrets: [{}], probe: { state: 'requested' } }),
  executorCase({ n: 31, name: 'Шлюз проверяется', secrets: [{}], probe: { state: 'running' } }),
  executorCase({ n: 32, name: 'Шлюз без проверок', secrets: [{}], probe: null }),
  executorCase({ n: 33, name: 'Шлюз без ключа', probe: null }),
  executorCase({
    n: 34, name: 'Модель за туннелем', secrets: [{}, { purpose: 'ssh_private_key', last4: '', public_key: 'открытый-ключ-туннеля' }],
    revision: { transport: 'ssh_tunnel', ssh_host: 'туннель.example', ssh_port: 22, ssh_user: 'исполнитель' },
    probe: OK,
  }),
  executorCase({ n: 35, name: 'Подключение в архиве', secrets: [{}], probe: OK, archived: true }),
  executorCase({ n: 36, name: 'Подключение без настроек', revision: null }),
  executorCase({ n: 37, name: 'Старое подключение', secrets: [{}], probe: OK, createdAt: ago(40 * DAY) }),
];

export const ALL_CASES: readonly ExecutorCase[] = [
  ...OUTCOME_CASES.map(([, one]) => one),
  SPARE,
  ...SHAPE_CASES,
];

export const ROUTE: ExecutorRoute = {
  work_kind: 'text_analysis',
  primary_connection_id: READY.connection.connection_id,
  standby_connection_id: SPARE.connection.connection_id,
  set_at: ago(HOUR),
  set_by: ADMIN_UID,
};

export function connectionList(cases: readonly ExecutorCase[] = ALL_CASES): ExecutorConnectionList {
  return { items: cases.map((one) => one.connection), pinned_models: [...PINNED] };
}

/** Seed the three reads of «Подключения» and «Назначения» into a client. */
export function seedExecutors(
  client: Client,
  cases: readonly ExecutorCase[] = ALL_CASES,
  routes: readonly ExecutorRoute[] = [ROUTE],
): void {
  client.setQueryData(queryKeys.execution.connections(), connectionList(cases));
  for (const one of cases) {
    client.setQueryData(queryKeys.execution.connection(one.connection.connection_id), one.detail);
  }
  client.setQueryData(queryKeys.execution.routes(), { items: [...routes] });
}
