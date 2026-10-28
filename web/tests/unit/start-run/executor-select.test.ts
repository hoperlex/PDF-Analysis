/**
 * `EXEC-PAR-WEB-01`: the start control's «Исполнитель» select.
 *
 * Rendered, not read from source (`D-53`): the control over a seeded cache, in the three states
 * the connection list can be in (loading, failed, read), and the select view in the shapes a
 * `useState` and a settled mutation produce. The options are checked against `routeBlocker`, the
 * repository's one definition of «can serve now», so a second definition in the select would be red.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ApiError, queryKeys } from '@/shared/api';
import type { ErrorEnvelope } from '@/shared/api';
import { DEFAULT_EXECUTOR_LABEL, ExecutorSelectView, StartRunControl } from '@/features/start-run';
import {
  CHOICE_BLOCKER_SENTENCES, KIND_LABELS, choiceCanServe, currentRevision, executorChoiceLabel, executorChoices,
  routeBlocker,
} from '@/entities/executor-connection';

import { PROJECT_UID, VERSION_UID } from '../review/fixtures';
import { newClient, renderWith, seedError } from '../screens/harness';
import { ALL_CASES, OUTCOME_CASES, READY, SPARE, executorCase, seedExecutors } from '../workers/executor-fixtures';

type Client = ReturnType<typeof newClient>;

function control(client: Client): string {
  return renderWith(client, createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
}

function seeded(cases = ALL_CASES): Client {
  const client = newClient();
  seedExecutors(client, cases);
  return client;
}

/**
 * The `<option>` elements of the **executor's** select, as `[attributes, text]`. `ANALYSIS-PRESETS-01`
 * put the preset's select before it on the control; these tests are about the executor's, so the
 * slice starts at its marker and ends at its `</select>`.
 */
function options(markup: string): Array<readonly [string, string]> {
  const start = markup.indexOf('data-executor-select');
  const slice = start < 0 ? '' : markup.slice(start, markup.indexOf('</select>', start));
  return [...slice.matchAll(/<option\b([^>]*)>([^<]*)<\/option>/g)].map((m) => [m[1] ?? '', m[2] ?? ''] as const);
}

const optionFor = (markup: string, id: string) => options(markup).find(([attrs]) => attrs.includes(`value="${id}"`));

describe('the selector is on the control', () => {
  it('draws the executor’s labelled select, with the preset’s before it, and its first option is the default', () => {
    const markup = control(seeded());
    expect(markup.match(/<select\b/g)).toHaveLength(2);
    expect(markup.indexOf('data-preset-select')).toBeLessThan(markup.indexOf('data-executor-select'));
    expect(markup).toMatch(/<label for="([^"]+)">Исполнитель<\/label><select id="\1"/);
    const first = options(markup)[0];
    expect(first?.[1]).toBe(DEFAULT_EXECUTOR_LABEL);
    expect(DEFAULT_EXECUTOR_LABEL).toBe('По умолчанию (маршрут)');
    expect(first?.[0]).toContain('value=""');
    expect(first?.[0]).toContain('selected');
  });

  it('keeps the start button beside it, enabled', () => {
    const markup = control(seeded());
    expect(markup).toMatch(/<button type="button" class="am-button">Запустить прогон<\/button>/);
  });
});

describe('what it offers is decided by the repository’s readiness rule', () => {
  const markup = control(seeded());

  it('enables a connection exactly when routeBlocker finds nothing against it', () => {
    let enabled = 0;
    let disabled = 0;
    for (const { connection, detail } of ALL_CASES) {
      if (connection.archived_at !== undefined) continue;
      const blocker = routeBlocker(connection, currentRevision(connection, detail.revisions));
      const option = optionFor(markup, connection.connection_id);
      expect(option, connection.display_name).toBeDefined();
      expect(option?.[0].includes('disabled'), connection.display_name).toBe(blocker !== null);
      if (blocker === null) enabled += 1; else disabled += 1;
    }
    // Both sides of the rule are exercised, or the loop above proves nothing.
    expect(enabled).toBeGreaterThan(2);
    expect(disabled).toBeGreaterThan(8);
  });

  it('says why a connection that cannot serve is disabled, in the sentence «Назначения» uses', () => {
    for (const { connection, detail } of ALL_CASES) {
      if (connection.archived_at !== undefined) continue;
      const blocker = routeBlocker(connection, currentRevision(connection, detail.revisions));
      if (blocker === null) continue;
      expect(optionFor(markup, connection.connection_id)?.[1], connection.display_name)
        .toContain(`недоступно: ${CHOICE_BLOCKER_SENTENCES[blocker]}`);
    }
  });

  it('shows the kind, the pinned model and the last probe beside the name', () => {
    const ready = optionFor(markup, READY.connection.connection_id)?.[1] ?? '';
    expect(ready).toContain('Основной шлюз');
    expect(ready).toContain(`(${KIND_LABELS.http_api})`);
    expect(ready).toContain('модель «модель-основная»');
    expect(ready).toContain('проверка: готово');
    expect(ready).not.toContain('недоступно');
    // A refused probe is worded by its outcome.
    const refused = OUTCOME_CASES.find(([outcome]) => outcome === 'credential_refused')![1];
    expect(optionFor(markup, refused.connection.connection_id)?.[1]).toContain('проверка: ключ отклонён');
    // A pull client says so in its own words.
    const pull = ALL_CASES.find((one) => one.connection.kind === 'pull')!;
    expect(optionFor(markup, pull.connection.connection_id)?.[1]).toContain(`(${KIND_LABELS.pull})`);
  });

  it('does not list an archived connection', () => {
    const archived = ALL_CASES.filter((one) => one.connection.archived_at !== undefined);
    expect(archived.length).toBeGreaterThan(0);
    for (const one of archived) expect(optionFor(markup, one.connection.connection_id)).toBeUndefined();
  });

  it('renders no key, no address, no token and no identifier', () => {
    expect(markup).not.toContain('шлюз.example');
    expect(markup).not.toContain('4417');
    expect(markup).not.toContain('токен-');
    expect(markup).not.toContain('base_url');
    expect(markup).not.toMatch(/\bexc_[0-9A-Z]{26}\b[^"]*<\/option>/);
    for (const [, text] of options(markup)) expect(text).not.toMatch(/exc_|excr_|epb_|exs_/);
  });
});

describe('a connection whose settings were not read is not offered', () => {
  it('is listed disabled and says so', () => {
    const client = newClient();
    client.setQueryData(queryKeys.execution.connections(), { items: [READY.connection], pinned_models: [] });
    // Its detail read failed: the list is known, the settings are not.
    seedError(client, queryKeys.execution.connection(READY.connection.connection_id),
      new ApiError(503, { contract_version: '1.10.0', error_code: 'dependency_unavailable', message: 'm', correlation_id: 'c', retryable: true } satisfies ErrorEnvelope, 'c'));
    const markup = control(client);
    const option = optionFor(markup, READY.connection.connection_id);
    expect(option?.[0]).toContain('disabled');
    expect(option?.[1]).toContain('недоступно: настройки подключения не прочитаны');
  });
});

describe('while the list loads, and when it cannot be read, the default start still works', () => {
  it('shows the loading state under a select that already holds the default', () => {
    const markup = control(newClient());
    expect(markup).toContain('Загрузка: исполнители…');
    expect(options(markup)).toEqual([[' value="" selected=""', DEFAULT_EXECUTOR_LABEL]]);
    expect(markup).toMatch(/<button type="button" class="am-button">Запустить прогон<\/button>/);
  });

  it('says the list is not read, offers to read it again, and leaves the start enabled', () => {
    const client = newClient();
    seedError(client, queryKeys.execution.connections(), new ApiError(503, {
      contract_version: '1.10.0', error_code: 'dependency_unavailable', message: 'm',
      correlation_id: 'cid-list', retryable: true,
    }, 'cid-list'));
    const markup = control(client);
    expect(markup).toContain('data-executor-list-failure');
    expect(markup).toContain('Список исполнителей не прочитан.');
    expect(markup).toContain('Прогон можно запустить на исполнителе по умолчанию.');
    expect(markup).toContain('cid-list');
    expect(markup).toContain('Прочитать список снова');
    expect(options(markup)).toEqual([[' value="" selected=""', DEFAULT_EXECUTOR_LABEL]]);
    expect(markup).not.toContain('Загрузка: исполнители');
    expect(markup).toMatch(/<button type="button" class="am-button">Запустить прогон<\/button>/);
  });

  it('says there is nothing to choose when no connection exists', () => {
    const markup = control(seeded([]));
    expect(markup).toContain('Подключений для выбора пока нет.');
    expect(options(markup)).toHaveLength(1);
  });
});

describe('the choice stays visible, whatever happened to it', () => {
  const choices = executorChoices(
    ALL_CASES.map((one) => one.connection),
    new Map(ALL_CASES.map((one) => [one.connection.connection_id as string, one.detail])),
  );
  const view = (value: string | null, disabled = false) =>
    renderWith(newClient(), createElement(ExecutorSelectView, {
      id: 'executor-test', reading: { phase: 'ready', choices }, value, disabled, onChange: () => undefined,
    }));

  it('marks the chosen connection selected and the hint says nothing else will be used', () => {
    const markup = view(SPARE.connection.connection_id);
    const chosen = optionFor(markup, SPARE.connection.connection_id);
    expect(chosen?.[0]).toContain('selected');
    expect(options(markup).filter(([attrs]) => attrs.includes('selected'))).toHaveLength(1);
    expect(markup).toContain('data-executor-hint="chosen"');
    expect(markup).toContain('Прогон пойдёт только на выбранном исполнителе.');
    expect(markup).toContain('другой исполнитель не подставляется');
  });

  it('keeps a chosen connection that can no longer serve selected, disabled and explained', () => {
    const blocked = choices.find((choice) => choice.blocker === 'probe_failed')!;
    const markup = view(blocked.connectionId);
    const option = optionFor(markup, blocked.connectionId);
    expect(option?.[0]).toContain('selected');
    expect(option?.[0]).toContain('disabled');
    expect(option?.[1]).toContain('недоступно');
  });

  it('lists a chosen archived connection, and no other archived one', () => {
    const archived = choices.filter((choice) => choice.archived);
    const markup = view(archived[0]!.connectionId);
    expect(optionFor(markup, archived[0]!.connectionId)?.[0]).toContain('selected');
    expect(optionFor(markup, archived[0]!.connectionId)?.[1]).toContain('недоступно: подключение в архиве');
    for (const other of archived.slice(1)) expect(optionFor(markup, other.connectionId)).toBeUndefined();
  });

  it('keeps a choice that has left the list instead of showing the first option in its place', () => {
    const gone = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';
    const markup = view(gone);
    const option = optionFor(markup, gone);
    expect(option?.[1]).toBe('Выбранный исполнитель больше не в списке');
    expect(option?.[0]).toContain('selected');
    expect(option?.[0]).toContain('disabled');
    expect(options(markup)[0]?.[0]).not.toContain('selected');
  });

  it('holds the select while a start is in flight', () => {
    expect(view(null, true)).toMatch(/<select[^>]*disabled/);
    expect(view(null, false)).not.toMatch(/<select[^>]*disabled/);
  });

  it('says what the default means when nothing is chosen', () => {
    const markup = view(null);
    expect(markup).toContain('data-executor-hint="default"');
    expect(markup).toContain('Без выбора прогон идёт на исполнителе по назначению стенда.');
  });
});

describe('the label is words and nothing else', () => {
  it('names a connection with no settings and no probe without inventing either', () => {
    const bare = executorCase({ n: 90, name: 'Подключение без настроек', revision: null });
    const [choice] = executorChoices([bare.connection], new Map([[bare.connection.connection_id, bare.detail]]));
    expect(choice).toBeDefined();
    const label = executorChoiceLabel(choice!);
    expect(label).toContain('Подключение без настроек');
    expect(label).not.toContain('модель');
    expect(label).toContain('проверок не было');
    expect(label).toContain('недоступно: настройки ещё не заданы');
    expect(choiceCanServe(choice!)).toBe(false);
  });
});
