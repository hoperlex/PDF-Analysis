/**
 * `EXEC2-WEB-CAP-01` — capacity on the connection form and card (B1 §6, test 13; ADR-0026
 * decisions 1, 2 and 19).
 *
 * What an administrator sees of «Одновременных прогонов»:
 *
 * - the field, in every kind, starting at one or at the current revision's value, with the coupled
 *   limit of the kind beside it and the `R-149a` notice;
 * - what the form sends (the member, or nothing when the form does not carry the field) and what
 *   it refuses before sending;
 * - the three refusals the server makes for the field, said in Russian and not in the English
 *   message of the envelope;
 * - on the card, «Занято N из M» for runs and comparison calls together, the calls named only when
 *   there is one, nothing when the connection has no reading — and never «свободно»;
 * - on the connection list, the notice that client documents are not checked.
 *
 * Rendered, not read from source: the static render keeps every `useState` at its start. None of
 * this needs PostgreSQL. Written under `R-149d` and not run in EXEC-2.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type {
  ExecutorConnection, ExecutorKind, ExecutorOccupancy, ExecutorRevision, Role,
} from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import {
  CAPACITY_COUPLING_HINTS, CAPACITY_FIELD_LABEL, CAPACITY_HINT, CLIENT_DOCUMENTS_NOTICE,
  SSH_PROFILE_LABELS, connectionFailure, connectionRefusalSentence, occupancyReading, occupancySentence,
} from '@/entities/executor-connection';
import {
  CommandFailure, CreateConnectionForm, FIELD_NAMES, ReviseConnectionForm, SettingsFields, initialSettings,
  readRevision, requestFromRevision,
} from '@/features/manage-executor-connection';
import { ExecutorConnections } from '@/widgets/executor-connections';

import { render } from '../review/fixtures';
import { newClient, renderScreen } from '../screens/harness';
import type { ExecutorCase } from './executor-fixtures';
import { PINNED, PULL_ONLINE, READY, SPARE, revision, seedExecutors } from './executor-fixtures';

// ------------------------------------------------------------------------------ helpers

function form(fields: Record<string, string | boolean>): FormData {
  const data = new FormData();
  for (const [name, value] of Object.entries(fields)) {
    if (value === true) data.set(name, 'on');
    else if (value !== false) data.set(name, value);
  }
  return data;
}

const COMMON = {
  pin_id: 'модель-основная', gateway_model: 'шлюзовая-основная', billing: 'metered', timeout_seconds: '120',
};
const HTTP = {
  ...COMMON, api_flavour: 'openai_chat', base_url: 'https://шлюз.example/api/v1', transport: 'direct', max_parallel_calls: '4',
};
const SSH = {
  ...COMMON, ssh_profile: 'claude_code_headless', ssh_host: 'node.example', ssh_port: '22', ssh_user: 'runner',
};
const PULL = { ...COMMON, pull_client: 'agent', answer_deadline_seconds: '600', max_claimed_tasks: '4' };
const BY_KIND: Readonly<Record<ExecutorKind, Record<string, string>>> = { http_api: HTTP, ssh_command: SSH, pull: PULL };
const KINDS: readonly ExecutorKind[] = ['http_api', 'ssh_command', 'pull'];

const RANGE_PROBLEM = 'Одновременных прогонов: целое число от 1 до 16.';

function fields(kind: ExecutorKind, initial?: ExecutorRevision): string {
  return render(createElement('form', null, createElement(SettingsFields, {
    kind, pinnedModels: PINNED, idPrefix: `cap-${kind}`, ...(initial === undefined ? {} : { initial }),
  })));
}

/** The one `<input>` of the capacity field. */
function capacityInput(markup: string): string {
  const tags = markup.match(/<input[^>]*name="max_active_runs"[^>]*>/g) ?? [];
  expect(tags, 'exactly one capacity field').toHaveLength(1);
  return tags[0] as string;
}

/** The same case with the occupancy the server reads, or with none (a connection without a current revision). */
function withOccupancy(one: ExecutorCase, occupancy: ExecutorOccupancy | undefined, over: Partial<ExecutorConnection> = {}): ExecutorCase {
  const connection: ExecutorConnection = { ...one.connection, ...over };
  delete connection.occupancy;
  if (occupancy !== undefined) connection.occupancy = occupancy;
  return { connection, detail: { ...one.detail, connection } };
}

function connections(roles: Role[], cases: readonly ExecutorCase[]): string {
  const client = newClient();
  seedExecutors(client, cases, []);
  client.setQueryData(queryKeys.account.me(), { roles });
  return renderScreen(client, createElement(ExecutorConnections, { roles }));
}

/** Every occupancy line of a page: its state and its sentence. */
function occupancyLines(markup: string): { state: string; text: string; attributes: string }[] {
  return [...markup.matchAll(/<p data-executor-occupancy="([a-z_]+)"([^>]*)>([^<]*)<\/p>/g)]
    .map((match) => ({ state: match[1] as string, attributes: match[2] as string, text: match[3] as string }));
}

// -------------------------------------------------------------------- the field, in the form

describe('«Одновременных прогонов» is drawn in every kind, starting at one', () => {
  for (const kind of KINDS) {
    it(`${kind}: a required whole number from 1 to 16 under its label, starting at 1`, () => {
      const markup = fields(kind);
      const input = capacityInput(markup);
      expect(input).toContain('type="number"');
      expect(input).toContain('min="1"');
      expect(input).toContain('max="16"');
      expect(input).toContain('required');
      expect(input).toContain('value="1"');
      expect(markup).toContain(`<label for="cap-${kind}-active-runs">Одновременных прогонов</label>`);
      expect(input).toContain(`id="cap-${kind}-active-runs"`);
      expect(CAPACITY_FIELD_LABEL).toBe('Одновременных прогонов');
    });
  }

  it('is drawn for a tunnelled HTTP API connection too', () => {
    const current = READY.detail.revisions[0] as ExecutorRevision;
    const markup = fields('http_api', { ...current, transport: 'ssh_tunnel', ssh_host: 'туннель.пример', ssh_port: 22, ssh_user: 'исполнитель' });
    expect(markup).toContain('name="ssh_host"');
    expect(capacityInput(markup)).toContain('value="1"');
  });

  it('starts from the current revision’s value, and from one when the revision has none', () => {
    const current = READY.detail.revisions[0] as ExecutorRevision;
    expect(capacityInput(fields('http_api', { ...current, max_active_runs: 3 }))).toContain('value="3"');
    expect(capacityInput(fields('http_api', current))).toContain('value="1"');
  });

  it('is on the revise form and the create form', () => {
    const current = { ...(READY.detail.revisions[0] as ExecutorRevision), max_active_runs: 4 };
    const client = newClient();
    const revise = renderScreen(client, createElement(ReviseConnectionForm, {
      connection: READY.connection, revision: current, pinnedModels: PINNED, holdsKey: true, onClose: () => undefined,
    }));
    expect(capacityInput(revise)).toContain('value="4"');
    const create = renderScreen(client, createElement(CreateConnectionForm, { pinnedModels: PINNED }));
    expect(capacityInput(create)).toContain('value="1"');
  });
});

describe('the coupled limit of the kind stands beside the field (ADR-0026 decision 2)', () => {
  it('says, for an HTTP API connection, that «Параллельных вызовов» may not be fewer, and that field is drawn', () => {
    const markup = fields('http_api');
    expect(markup).toContain(`data-executor-capacity-coupling="http_api">${CAPACITY_COUPLING_HINTS.http_api}</p>`);
    expect(CAPACITY_COUPLING_HINTS.http_api).toContain('«Параллельных вызовов»');
    expect(markup).toContain('>Параллельных вызовов</label>');
  });

  it('says, for a client that pulls tasks, that «Заданий в работе одновременно» may not be fewer, and that field is drawn', () => {
    const markup = fields('pull');
    expect(markup).toContain(`data-executor-capacity-coupling="pull">${CAPACITY_COUPLING_HINTS.pull}</p>`);
    expect(CAPACITY_COUPLING_HINTS.pull).toContain('«Заданий в работе одновременно»');
    expect(markup).toContain('>Заданий в работе одновременно</label>');
  });

  it('says, for a command over SSH, that a custom command takes one, naming the profile the select offers', () => {
    const markup = fields('ssh_command');
    expect(markup).toContain(`data-executor-capacity-coupling="ssh_command">${CAPACITY_COUPLING_HINTS.ssh_command}</p>`);
    expect(CAPACITY_COUPLING_HINTS.ssh_command).toContain(`«${SSH_PROFILE_LABELS.custom_command}»`);
    expect(markup).toContain(`>${SSH_PROFILE_LABELS.custom_command}</option>`);
    expect(CAPACITY_COUPLING_HINTS.ssh_command).toContain('только значение 1');
  });

  it('draws the hint of its own kind and no other', () => {
    for (const kind of KINDS) {
      const markup = fields(kind);
      for (const other of KINDS) {
        const present = markup.includes(CAPACITY_COUPLING_HINTS[other]);
        expect(present, `${kind} form, ${other} hint`).toBe(other === kind);
      }
      expect(markup).toContain(CAPACITY_HINT);
    }
  });

  it('carries the R-149a notice at the field, because capacity above one is for test data', () => {
    for (const kind of KINDS) {
      expect(fields(kind)).toContain(`data-executor-capacity-notice="true">${CLIENT_DOCUMENTS_NOTICE}</p>`);
    }
  });
});

// ---------------------------------------------------------------- what the form sends

describe('reading the field out of a form', () => {
  for (const kind of KINDS) {
    it(`${kind}: sends the member with the number typed, beside the rest of the settings`, () => {
      const reading = readRevision(kind, form({ ...BY_KIND[kind], max_active_runs: '3' }), PINNED);
      expect(reading.ok && reading.body.max_active_runs).toBe(3);
      expect(reading.ok && reading.body.pin_id).toBe('модель-основная');
    });

    it(`${kind}: sends none when the form does not carry the field, so the server reads one`, () => {
      const reading = readRevision(kind, form(BY_KIND[kind]), PINNED);
      expect(reading.ok).toBe(true);
      expect(reading.ok && 'max_active_runs' in reading.body).toBe(false);
    });
  }

  it('accepts both ends of the range', () => {
    for (const value of ['1', '16']) {
      const reading = readRevision('http_api', form({ ...HTTP, max_active_runs: value }), PINNED);
      expect(reading.ok && reading.body.max_active_runs, value).toBe(Number(value));
    }
  });

  for (const value of ['0', '17', '1.5', '-1', 'много', '', '  ']) {
    it(`refuses ${JSON.stringify(value)} with a sentence next to the field, sending nothing`, () => {
      for (const kind of KINDS) {
        expect(readRevision(kind, form({ ...BY_KIND[kind], max_active_runs: value }), PINNED), kind)
          .toEqual({ ok: false, problem: RANGE_PROBLEM });
      }
    });
  }

  it('leaves the coupled limits to the server: a number below «Параллельных вызовов» is sent, not refused here', () => {
    const http = readRevision('http_api', form({ ...HTTP, max_parallel_calls: '2', max_active_runs: '8' }), PINNED);
    expect(http.ok && http.body).toMatchObject({ max_parallel_calls: 2, max_active_runs: 8 });
    const pull = readRevision('pull', form({ ...PULL, max_claimed_tasks: '1', max_active_runs: '8' }), PINNED);
    expect(pull.ok && pull.body).toMatchObject({ max_claimed_tasks: 1, max_active_runs: 8 });
    const custom = readRevision('ssh_command', form({ ...SSH, ssh_profile: 'custom_command', max_active_runs: '2' }), PINNED);
    expect(custom.ok && custom.body).toMatchObject({ ssh_profile: 'custom_command', max_active_runs: 2 });
  });

  it('keeps the field name the contract’s own', () => {
    expect(FIELD_NAMES.maxActiveRuns).toBe('max_active_runs');
  });
});

describe('starting a form, and changing one field of a revision', () => {
  it('starts a new connection at one and a revision from its own value', () => {
    expect(initialSettings(undefined, PINNED).maxActiveRuns).toBe(1);
    const current = revision({ connection_id: READY.connection.connection_id, revision_id: 'excr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', max_active_runs: 5 });
    expect(initialSettings(current, PINNED).maxActiveRuns).toBe(5);
    expect(initialSettings(READY.detail.revisions[0], PINNED).maxActiveRuns).toBe(1);
  });

  it('keeps the capacity when another field is changed, and invents none for a revision without one', () => {
    const current = READY.detail.revisions[0] as ExecutorRevision;
    expect(requestFromRevision({ ...current, max_active_runs: 6 }, { host_key: 'новый-отпечаток' }))
      .toMatchObject({ host_key: 'новый-отпечаток', max_active_runs: 6 });
    expect('max_active_runs' in requestFromRevision(current)).toBe(false);
  });
});

// --------------------------------------------------------------------- the three refusals

describe('the server’s refusals for the field are said in Russian', () => {
  const refusal = (details: Record<string, string>): ApiError => new ApiError(422, {
    contract_version: '1.43.0', error_code: 'validation_failed', message: 'Safe.',
    correlation_id: 'cid-capacity-1', retryable: false, details,
  }, null);
  const said = (details: Record<string, string>): string => connectionFailure(refusal(details), true).detail;

  it('below_max_active_runs on a client that pulls tasks names «Заданий в работе»', () => {
    expect(said({ field: 'max_claimed_tasks', constraint: 'below_max_active_runs' })).toBe(
      'Заданий в работе: значение меньше числа одновременных прогонов; увеличьте его или уменьшите число прогонов.');
  });

  it('below_max_active_runs on an HTTP API connection names «Параллельных вызовов»', () => {
    expect(said({ field: 'max_parallel_calls', constraint: 'below_max_active_runs' })).toBe(
      'Параллельных вызовов: значение меньше числа одновременных прогонов; увеличьте его или уменьшите число прогонов.');
  });

  it('capacity_not_supported_for_kind names the custom command and the value that is allowed', () => {
    expect(said({ field: 'max_active_runs', constraint: 'capacity_not_supported_for_kind' })).toBe(
      'Одновременных прогонов: для профиля «Своя команда на удалённой машине» допустимо только значение 1; параллельные запуски своей команды стенд пока не изолирует.');
  });

  it('range on the field says 1 to 16, not the bound of a token’s lifetime', () => {
    const sentence = said({ field: 'max_active_runs', constraint: 'range' });
    expect(sentence).toBe(RANGE_PROBLEM);
    expect(sentence).not.toContain('365');
    // The same constraint on the token field keeps its own bound.
    expect(said({ field: 'expires_in_days', constraint: 'range' })).toContain('от 1 до 365 дней');
  });

  it('is a definite refusal, never an unknown outcome, so the person fixes the number and repeats', () => {
    for (const constraint of ['below_max_active_runs', 'capacity_not_supported_for_kind', 'range']) {
      const failure = connectionFailure(refusal({ field: 'max_active_runs', constraint }), true);
      expect(failure.kind, constraint).toBe('refusal');
    }
  });

  it('puts the sentence on the form’s failure box, in Russian only', () => {
    for (const details of [
      { field: 'max_claimed_tasks', constraint: 'below_max_active_runs' },
      { field: 'max_parallel_calls', constraint: 'below_max_active_runs' },
      { field: 'max_active_runs', constraint: 'capacity_not_supported_for_kind' },
      { field: 'max_active_runs', constraint: 'range' },
    ]) {
      const failure = connectionFailure(refusal(details), true);
      const markup = render(createElement(CommandFailure, { failure }));
      expect(markup).toContain('Команда подключению не выполнена');
      expect(markup).toContain(failure.detail);
      expect(failure.detail).not.toContain('Safe.');
      expect(failure.detail, details.constraint).not.toMatch(/[A-Za-z]/);
    }
  });

  it('answers null for a constraint it does not know, so the catalogue sentence is used', () => {
    expect(connectionRefusalSentence(refusal({ field: 'max_active_runs', constraint: 'something_new' }))).toBeNull();
    expect(connectionFailure(refusal({ field: 'max_active_runs', constraint: 'something_new' }), true).detail)
      .not.toContain('Safe.');
  });
});

// -------------------------------------------------------------- occupancy on the card

describe('«Занято N из M» on the card', () => {
  const lines = (occupancy: ExecutorOccupancy | undefined, over: Partial<ExecutorConnection> = {}, roles: Role[] = ['admin']) =>
    occupancyLines(connections(roles, [withOccupancy(READY, occupancy, over)]));

  it('counts runs only, and does not mention calls when there are none', () => {
    const [line, ...rest] = lines({ capacity: 4, active_runs: 2, active_calls: 0 });
    expect(rest).toEqual([]);
    expect(line?.text).toBe('Занято 2 из 4.');
    expect(line?.state).toBe('in_use');
    expect(line?.text).not.toContain('вызов');
    expect(line?.attributes).toContain('data-executor-occupancy-used="2"');
    expect(line?.attributes).toContain('data-executor-occupancy-capacity="4"');
  });

  it('counts runs and calls together and names the calls only when there is one', () => {
    const [line] = lines({ capacity: 4, active_runs: 2, active_calls: 1 });
    expect(line?.text).toBe('Занято 3 из 4 (прогонов: 2, вызовов модели сравнения: 1).');
    expect(line?.attributes).toContain('data-executor-occupancy-runs="2"');
    expect(line?.attributes).toContain('data-executor-occupancy-calls="1"');
  });

  it('is not idle while only a call holds a unit', () => {
    const [line] = lines({ capacity: 2, active_runs: 0, active_calls: 1 });
    expect(line?.state).toBe('in_use');
    expect(line?.text).toBe('Занято 1 из 2 (прогонов: 0, вызовов модели сравнения: 1).');
  });

  it('says a connection with nothing in use has nothing in use, in the same form', () => {
    const [line] = lines({ capacity: 3, active_runs: 0, active_calls: 0 });
    expect(line?.state).toBe('idle');
    expect(line?.text).toBe('Занято 0 из 3.');
  });

  it('says a full connection makes new runs wait', () => {
    const [line] = lines({ capacity: 2, active_runs: 1, active_calls: 1 });
    expect(line?.state).toBe('full');
    expect(line?.text).toBe('Занято 2 из 2 (прогонов: 1, вызовов модели сравнения: 1): новые прогоны ждут в очереди.');
  });

  it('says, when the capacity was lowered below the work in flight, that the work is not stopped', () => {
    const [line] = lines({ capacity: 2, active_runs: 3, active_calls: 0 });
    expect(line?.state).toBe('over');
    expect(line?.text).toBe('Занято 3 из 2: число одновременных прогонов уменьшили, идущая работа не прерывается, а новая ждёт в очереди.');
  });

  it('draws nothing when the connection has no reading, and no «Занято» anywhere', () => {
    for (const one of [READY, SPARE, PULL_ONLINE, withOccupancy(READY, undefined)]) {
      const markup = connections(['admin'], [one]);
      expect(markup).not.toContain('data-executor-occupancy');
      expect(markup).not.toContain('Занято');
    }
  });

  it('draws nothing for a reading that is not whole non-negative numbers, rather than a guess', () => {
    const malformed: ExecutorOccupancy[] = [
      { capacity: 0, active_runs: 0, active_calls: 0 },
      { capacity: 2, active_runs: -1, active_calls: 0 },
      { capacity: 2, active_runs: 0.5, active_calls: 0 },
      { capacity: 2, active_runs: 0, active_calls: Number.NaN },
      { capacity: Number.POSITIVE_INFINITY, active_runs: 0, active_calls: 0 },
    ];
    for (const occupancy of malformed) {
      expect(occupancyReading({ occupancy }), JSON.stringify(occupancy)).toBeNull();
      expect(lines(occupancy)).toEqual([]);
    }
  });

  it('is shown to an expert and before the roles are read, because any role reads the list', () => {
    for (const roles of [['expert'], []] as Role[][]) {
      expect(lines({ capacity: 2, active_runs: 1, active_calls: 0 }, {}, roles)[0]?.text).toBe('Занято 1 из 2.');
    }
  });

  it('is shown on an archived connection, whose work in flight still holds its units', () => {
    const archived = lines({ capacity: 2, active_runs: 1, active_calls: 0 }, { archived_at: '2026-11-01T09:00:00.000Z' });
    expect(archived[0]?.text).toBe('Занято 1 из 2.');
  });

  it('is shown on a client that pulls tasks as on any other kind', () => {
    const markup = connections(['admin'], [withOccupancy(PULL_ONLINE, { capacity: 3, active_runs: 3, active_calls: 0 })]);
    expect(occupancyLines(markup)[0]?.state).toBe('full');
  });

  it('never says «свободно», in any state, anywhere on the page or in the words behind it', () => {
    const states: ExecutorOccupancy[] = [
      { capacity: 3, active_runs: 0, active_calls: 0 },
      { capacity: 3, active_runs: 1, active_calls: 0 },
      { capacity: 3, active_runs: 0, active_calls: 2 },
      { capacity: 3, active_runs: 2, active_calls: 1 },
      { capacity: 2, active_runs: 3, active_calls: 0 },
    ];
    for (const occupancy of states) {
      expect(connections(['admin'], [withOccupancy(READY, occupancy)]), JSON.stringify(occupancy)).not.toMatch(/свободн/i);
    }
    for (const words of [CAPACITY_HINT, CLIENT_DOCUMENTS_NOTICE, ...Object.values(CAPACITY_COUPLING_HINTS)]) {
      expect(words).not.toMatch(/свободн/i);
    }
  });

  it('is Cyrillic throughout: no Latin word is chrome the application wrote', () => {
    for (const occupancy of [
      { capacity: 4, active_runs: 2, active_calls: 1 }, { capacity: 2, active_runs: 2, active_calls: 0 },
      { capacity: 2, active_runs: 3, active_calls: 0 }, { capacity: 3, active_runs: 0, active_calls: 0 },
    ]) {
      const reading = occupancyReading({ occupancy });
      expect(reading).not.toBeNull();
      expect(occupancySentence(reading!)).not.toMatch(/[A-Za-z]/);
    }
  });
});

describe('the occupancy reading', () => {
  const read = (capacity: number, runs: number, calls: number) =>
    occupancyReading({ occupancy: { capacity, active_runs: runs, active_calls: calls } });

  it('adds runs and calls into one count of units', () => {
    expect(read(4, 2, 1)).toEqual({ used: 3, capacity: 4, runs: 2, calls: 1, state: 'in_use' });
  });

  it('draws the boundaries between idle, in use, full and over', () => {
    expect(read(2, 0, 0)?.state).toBe('idle');
    expect(read(2, 1, 0)?.state).toBe('in_use');
    expect(read(2, 1, 1)?.state).toBe('full');
    expect(read(2, 2, 1)?.state).toBe('over');
    expect(read(1, 0, 1)?.state).toBe('full');
  });

  it('is absent for a connection without one', () => {
    expect(occupancyReading({})).toBeNull();
  });
});

describe('the revision summary states the capacity', () => {
  it('says the revision’s value, and one for a revision from before capacity existed', () => {
    const current = READY.detail.revisions[0] as ExecutorRevision;
    const withValue = { ...READY, detail: { ...READY.detail, revisions: [{ ...current, max_active_runs: 3 }] } };
    expect(connections(['expert'], [withValue])).toContain('<dt>Одновременных прогонов</dt><dd data-executor-active-runs="3">3</dd>');
    expect(connections(['expert'], [READY])).toContain('<dt>Одновременных прогонов</dt><dd data-executor-active-runs="1">1</dd>');
  });
});

// ------------------------------------------------------------------- the R-149a notice

describe('the notice that client documents are not checked (R-149a, ADR-0026 decision 19)', () => {
  it('is the owner’s sentence', () => {
    expect(CLIENT_DOCUMENTS_NOTICE).toBe(
      'Допуск клиентских документов не проверяется: одновременные прогоны и группы — только для тестовых данных.');
    expect(CLIENT_DOCUMENTS_NOTICE).not.toMatch(/[A-Za-z]/);
  });

  it('stands once on the connection list for an administrator, an expert and an unread role', () => {
    for (const roles of [['admin'], ['expert'], []] as Role[][]) {
      const markup = connections(roles, [READY, SPARE]);
      expect(markup.match(/data-executor-list-notice="client-documents"/g), roles.join()).toHaveLength(1);
      expect(markup).toContain(`<p class="am-note" data-executor-list-notice="client-documents">${CLIENT_DOCUMENTS_NOTICE}</p>`);
    }
  });

  it('stands on an empty list too, because it qualifies what the list lets an administrator set', () => {
    const markup = connections(['admin'], []);
    expect(markup).toContain('data-executor-list-notice="client-documents"');
    expect(markup).toContain('Подключений нет');
  });

  it('is not drawn while the list is still being read', () => {
    const cold = renderScreen(newClient(), createElement(ExecutorConnections, { roles: ['admin'] }));
    expect(cold).not.toContain('data-executor-list-notice');
  });
});
