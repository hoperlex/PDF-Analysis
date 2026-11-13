/**
 * Fixtures of «Серверы» and «Модели по этапам» (`HOSTS-WEB-01`): a list of four servers (one on line with three models, one
 * off line, one on line with nothing usable, one with every slot used), the details of one, the model catalogue and a layout.
 * Every string is Cyrillic or an identifier, so the language guard can render them.
 */

import type { QueryClient } from '@tanstack/react-query';

import type {
  ExecutorAgentInstall,
  ExecutorHost,
  ExecutorHostDetails,
  ExecutorHostList,
  IssuedExecutorEnrollment,
  ModelCatalogue,
  StageComparisonCell,
  StageLayoutCell,
  StageModelLayout,
} from '@/shared/api';
import { executorHostDetailsKey, executorHostsKey } from '@/entities/executor-host';
import { modelCatalogueKey, stageLayoutKey } from '@/entities/stage-layout';

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8';
export const HOST_A = `exh_${ULID}A`;
export const HOST_B = `exh_${ULID}B`;
export const HOST_C = `exh_${ULID}C`;
export const HOST_D = `exh_${ULID}D`;
export const USER = `usr_${ULID}A`;
export const RUN = `run_${ULID}A`;
export const TASK = `ext_${ULID}A`;
const NOW = '2026-11-09T11:00:00Z';

function host(over: Partial<ExecutorHost> & Pick<ExecutorHost, 'host_id' | 'display_name'>): ExecutorHost {
  return {
    created_at: '2026-11-08T09:00:00Z', created_by: USER, enabled: true, models: [], slots_in_use: 0, slots_total: 0,
    state: 'online', last_seen_at: NOW, agent_version: '0.9.0', ...over,
  };
}

export const SERVER_ONLINE = host({
  host_id: HOST_A, display_name: 'основной', slots_in_use: 2, slots_total: 3,
  models: [
    { provider: 'claude_code', access: 'subscription', model_id: 'claude-opus-5-5', state: 'available' },
    { provider: 'claude_code', access: 'subscription', model_id: 'claude-sonnet-5-5', state: 'available' },
    { provider: 'codex', access: 'api', model_id: 'gpt-6-sol', state: 'available' },
  ],
});
export const SERVER_OFFLINE = host({
  host_id: HOST_B, display_name: 'резерв', state: 'offline', slots_in_use: 0, slots_total: 2, last_seen_at: '2026-11-09T11:02:00Z',
});
export const SERVER_EMPTY = host({ host_id: HOST_C, display_name: 'новый', slots_total: 1 });
export const SERVER_BUSY = host({
  host_id: HOST_D, display_name: 'второй', state: 'busy', slots_in_use: 1, slots_total: 1,
  models: [{ provider: 'codex', access: 'subscription', model_id: 'gpt-6.1-sol', state: 'busy' }],
});

export const HOST_LIST: ExecutorHostList = {
  items: [SERVER_ONLINE, SERVER_OFFLINE, SERVER_EMPTY, SERVER_BUSY], online: 3, slots_free: 3, slots_total: 7, total: 4,
};

export const HOST_DETAILS: ExecutorHostDetails = {
  host: SERVER_ONLINE,
  slots: [
    { provider: 'claude_code', access: 'subscription', in_use: 1, slots: 1 },
    { provider: 'codex', access: 'api', in_use: 1, slots: 2 },
  ],
  providers: [
    {
      provider: 'claude_code', access: 'subscription', auth_state: 'valid', cli_version: '2.4.1',
      models: [
        { model_id: 'claude-opus-5-5', state: 'available', reasons: [] },
        { model_id: 'claude-sonnet-5-5', state: 'unavailable', reasons: ['model_cooling_down'], cooldown_until: '2026-11-09T11:30:00Z' },
      ],
    },
    {
      provider: 'codex', access: 'api', auth_state: 'login_required',
      models: [{ model_id: 'gpt-6-sol', state: 'unavailable', reasons: ['login_required', 'model_not_verified'] }],
    },
    {
      provider: 'openrouter_api', access: 'api', auth_state: 'unknown',
      models: [{ model_id: 'gpt-6-astra', state: 'busy', reasons: [] }],
    },
  ],
  tasks: [{ task_id: TASK, run_id: RUN, stage_key: 'blocks:3', model_id: 'claude-opus-5-5', provider: 'claude_code', since: '2026-11-09T10:45:00Z' }],
};

/** A server that is switched off and out of contact: every model is unavailable for the two reasons that name it. */
export const HOST_DETAILS_OFF: ExecutorHostDetails = {
  host: { ...SERVER_OFFLINE, enabled: false },
  slots: [],
  providers: [{
    provider: 'claude_code', access: 'subscription', auth_state: 'valid',
    models: [{ model_id: 'claude-opus-5-5', state: 'unavailable', reasons: ['host_disabled', 'host_offline'] }],
  }],
  tasks: [],
};

export const CATALOGUE: ModelCatalogue = {
  contract_version: '1.55.0',
  items: [
    { provider: 'claude_code', model_id: 'claude-opus-5-5', access: ['subscription', 'api'], efforts: ['medium', 'high'], accepted_reported: ['claude-opus-5-5'] },
    { provider: 'claude_code', model_id: 'claude-sonnet-5-5', access: ['subscription', 'api'], efforts: ['low', 'medium', 'high'], accepted_reported: ['claude-sonnet-5-5'] },
    { provider: 'codex', model_id: 'gpt-6.1-sol', access: ['subscription', 'api'], efforts: ['low', 'medium', 'high'], accepted_reported: ['gpt-6.1-sol'] },
    { provider: 'codex', model_id: 'gpt-6-sol', access: ['subscription', 'api'], efforts: ['low', 'medium', 'high'], accepted_reported: ['gpt-6-sol'] },
    { provider: 'codex', model_id: 'gpt-6-astra', access: ['subscription', 'api'], efforts: ['low', 'medium', 'high'], accepted_reported: ['gpt-6-astra'] },
    { provider: 'codex', model_id: 'gpt-6-luna', access: ['subscription', 'api'], efforts: ['low', 'medium', 'high'], accepted_reported: ['gpt-6-luna'] },
  ],
};

export function cell(row: StageLayoutCell['row'], model: string, effort: StageLayoutCell['effort'] = 'medium', role: StageLayoutCell['role'] = 'main'): StageLayoutCell {
  return { cell_key: `${row}:${role}`, row, role, model_id: model, effort };
}

/** The blocks row is a scheme of the closed list (`HOSTS-ENSEMBLE-01`): one Astra. A single Claude is refused by the server. */
export const LAYOUT_CELLS: StageLayoutCell[] = [
  cell('text', 'claude-sonnet-5-5'),
  cell('blocks', 'gpt-6-astra'),
  cell('cross_check', 'claude-sonnet-5-5'),
  cell('norms', 'claude-sonnet-5-5'),
  cell('review', 'gpt-6-astra'),
  cell('correction', 'claude-sonnet-5-5'),
];

export const LAYOUT: StageModelLayout = {
  enabled: true,
  current: { layout_revision_id: `slr_${ULID}B`, revision_no: 2, kit: 'custom', created_at: NOW, created_by: USER, cells: LAYOUT_CELLS },
  history: [
    { layout_revision_id: `slr_${ULID}A`, revision_no: 1, kit: 'claude_only', created_at: '2026-11-08T10:00:00Z', created_by: USER, cells: LAYOUT_CELLS },
    { layout_revision_id: `slr_${ULID}B`, revision_no: 2, kit: 'custom', created_at: NOW, created_by: USER, cells: LAYOUT_CELLS },
  ],
  switch_journal: [{ enabled: true, set_at: NOW, set_by: USER }],
  // The critic's model is on no server.
  unavailable_cell_keys: ['review:main'],
};

/** The blocks row as an ensemble scheme (two legs and a judge), every effort of the catalogue on some cell. */
export const LAYOUT_ENSEMBLE: StageModelLayout = {
  ...LAYOUT,
  current: {
    ...LAYOUT.current!,
    cells: [
      cell('text', 'claude-sonnet-5-5', 'low'),
      cell('blocks', 'claude-opus-5-5', 'high', 'leg1'),
      cell('blocks', 'gpt-6-astra', 'medium', 'leg2'),
      cell('blocks', 'claude-sonnet-5-5', 'medium', 'judge'),
      cell('cross_check', 'claude-sonnet-5-5'),
      cell('norms', 'claude-sonnet-5-5'),
      cell('review', 'claude-sonnet-5-5'),
      cell('correction', 'claude-sonnet-5-5'),
    ],
  },
  unavailable_cell_keys: [],
};

/**
 * The four comparison cells of a «Свой набор» revision (`CMP-WEB-01`): every kind has its model and effort and nothing else (`LIMITS-01`).
 * Spec is served by no server (see `LAYOUT_COMPARISON`).
 */
export const COMPARISON_CELLS: StageComparisonCell[] = [
  { work_kind: 'comparison_pair_check', model_id: 'gpt-6-astra', effort: 'high' },
  { work_kind: 'comparison_sheet_changes', model_id: 'gpt-6.1-sol', effort: 'high' },
  { work_kind: 'comparison_spec', model_id: 'claude-sonnet-5-5', effort: 'medium' },
  { work_kind: 'comparison_report', model_id: 'claude-opus-5-5', effort: 'high' },
];

/** «Свой набор» with the four comparison cells stored; the cell of the specification names a model no server serves. */
export const LAYOUT_COMPARISON: StageModelLayout = {
  ...LAYOUT,
  current: { ...LAYOUT.current!, comparison_cells: COMPARISON_CELLS },
  unavailable_cell_keys: ['review:main', 'comparison_spec:main'],
};

/** A named set: the server serves its table (`comparison_cells` are present for a named set whatever the revision stored). */
export const LAYOUT_COMPARISON_KIT: StageModelLayout = {
  ...LAYOUT,
  current: {
    ...LAYOUT.current!, kit: 'codex_only',
    comparison_cells: COMPARISON_CELLS.map((c) => ({ ...c, model_id: 'gpt-6.1-sol', effort: 'high' as const })),
  },
  unavailable_cell_keys: [],
};

export const LAYOUT_OFF: StageModelLayout = { ...LAYOUT, enabled: false, switch_journal: [], unavailable_cell_keys: [] };
export const LAYOUT_EMPTY: StageModelLayout = { enabled: false, history: [], switch_journal: [], unavailable_cell_keys: [] };

export const ISSUED: IssuedExecutorEnrollment = {
  command: 'curl -fsSL https://stand.example/install.sh | AM_ENROLL_SECRET=ex-secret-1 sh',
  secret: 'ex-secret-1',
  package_sha256: 'a'.repeat(64),
  package_version: '0.9.0',
  enrollment: {
    enrollment_id: `exe_${ULID}A`, host_id: HOST_C, created_at: NOW, created_by: USER, expires_at: '2026-11-09T11:15:00Z',
    secret_prefix: 'ex-sec', state: 'pending',
  },
};

export function install(over: Partial<ExecutorAgentInstall> = {}): ExecutorAgentInstall {
  const made: ExecutorAgentInstall = {
    install_id: `exai_${ULID}A`, host_id: HOST_C, access: 'generated_key', state: 'awaiting_host_key', ssh_host: 'узел.пример', ssh_port: 22,
    ssh_user: 'установщик', created_at: NOW, updated_at: NOW, created_by: USER,
    authorized_keys_line: 'строка-ключа-для-файла', public_key: 'открытый-ключ-стенда',
    observed_host_key_fingerprint: 'отпечаток-ключа-сервера', ...over,
  };
  // A finished install has no line to add any more: the stand removed its key from the server.
  if (over.state === 'succeeded' || over.state === 'failed') delete made.authorized_keys_line;
  return made;
}

/** The reads of the two tabs, seeded the way the cache holds them after the first read. */
export function seedHosts(client: QueryClient, list: ExecutorHostList = HOST_LIST): void {
  client.setQueryData(executorHostsKey(), list);
}
export function seedDetails(client: QueryClient, details: ExecutorHostDetails = HOST_DETAILS): void {
  client.setQueryData(executorHostDetailsKey(details.host.host_id), details);
}
export function seedLayout(client: QueryClient, layout: StageModelLayout = LAYOUT, catalogue: ModelCatalogue = CATALOGUE): void {
  client.setQueryData(stageLayoutKey(), layout);
  client.setQueryData(modelCatalogueKey(), catalogue);
}
