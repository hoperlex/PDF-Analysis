/**
 * `executorChoices`, the repository's one reading of «can this connection serve now» for a list of connections.
 *
 * The start control's «Исполнитель» select was the only test instrument of these functions beside the preset form,
 * and `RUN-START-ONE-01a` removed the select. The two claims that were about the entity and not about the select are
 * kept here, so that the preset form (`features/manage-analysis-preset`, `widgets/analysis-presets`), which still reads
 * the same choices, keeps a test of its own source:
 *
 * - a choice can serve exactly when `routeBlocker` finds nothing against its connection (no second definition);
 * - the label is words only, and a connection with no settings and no probe is named without inventing either.
 */

import { describe, expect, it } from 'vitest';

import {
  CHOICE_BLOCKER_SENTENCES, KIND_LABELS, choiceCanServe, currentRevision, executorChoiceLabel, executorChoices,
  routeBlocker,
} from '@/entities/executor-connection';

import { ALL_CASES, READY, executorCase } from '../workers/executor-fixtures';

const choices = executorChoices(
  ALL_CASES.map((one) => one.connection),
  new Map(ALL_CASES.map((one) => [one.connection.connection_id as string, one.detail])),
);

describe('what can serve is decided by the repository’s readiness rule', () => {
  it('lets a connection serve exactly when routeBlocker finds nothing against it', () => {
    let serving = 0;
    let blocked = 0;
    for (const { connection, detail } of ALL_CASES) {
      if (connection.archived_at !== undefined) continue;
      const blocker = routeBlocker(connection, currentRevision(connection, detail.revisions));
      const choice = choices.find((one) => one.connectionId === connection.connection_id);
      expect(choice, connection.display_name).toBeDefined();
      expect(choiceCanServe(choice!), connection.display_name).toBe(blocker === null);
      if (blocker === null) serving += 1; else blocked += 1;
    }
    // Both sides of the rule are exercised, or the loop above proves nothing.
    expect(serving).toBeGreaterThan(2);
    expect(blocked).toBeGreaterThan(8);
  });

  it('says why a connection cannot serve, in the sentence «Назначения» uses', () => {
    for (const { connection, detail } of ALL_CASES) {
      if (connection.archived_at !== undefined) continue;
      const blocker = routeBlocker(connection, currentRevision(connection, detail.revisions));
      if (blocker === null) continue;
      const choice = choices.find((one) => one.connectionId === connection.connection_id)!;
      expect(executorChoiceLabel(choice), connection.display_name).toContain(`недоступно: ${CHOICE_BLOCKER_SENTENCES[blocker]}`);
    }
  });

  it('shows the kind, the pinned model and the last probe beside the name', () => {
    const ready = executorChoiceLabel(choices.find((one) => one.connectionId === READY.connection.connection_id)!);
    expect(ready).toContain('Основной шлюз');
    expect(ready).toContain(`(${KIND_LABELS.http_api})`);
    expect(ready).toContain('модель «модель-основная»');
    expect(ready).toContain('проверка: готово');
    expect(ready).not.toContain('недоступно');
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

  it('prints no key, no address, no token and no identifier', () => {
    for (const choice of choices) {
      const label = executorChoiceLabel(choice);
      expect(label).not.toContain('шлюз.example');
      expect(label).not.toContain('base_url');
      expect(label).not.toMatch(/exc_|excr_|epb_|exs_/);
    }
  });
});
