/**
 * `HOSTS-L1` (`D-660`, contract 1.48.0) — the run page names the model a waiting run waits for, in one line.
 *
 * `RunStatus.wait_cells` lists the cells of a queued run on the stage layout that cannot be bound now (the model of the plan, the access and a
 * cause of the closed set `RunWaitCause`). The page says «Ждём gpt-6-sol: нет сервера с этой моделью», at most two models and then «и ещё N»,
 * once, under the sentence of the reason; it draws nothing for a run that is not queued, for a reading without cells and for a cause it does
 * not know, and it adds no control. Rendered over a seeded cache (`D-53`), so the words a reader sees are the words judged.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunStatus, RunWaitCause, RunWaitCell } from '@/shared/api';
import { RUN_WAIT_CAUSE_VALUES, queryKeys } from '@/shared/api';
import { WAIT_CAUSE_LABELS, WAIT_MODELS_SHOWN, knownWaitCause, runWaitCellsLine, runWaitCellsSentence } from '@/entities/audit-run';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';

function cell(model: string, cause: RunWaitCause, access: RunWaitCell['access'] = 'subscription', key = `text:main`): RunWaitCell {
  return { cell_key: key, model_id: model, access, cause };
}

function waiting(cells: readonly RunWaitCell[] | undefined, over: Partial<RunStatus> = {}): RunStatus {
  return runStatus({
    state: 'queued', terminal_at: null, binding_state: 'pending', wait_reason: 'model_unavailable', waiting_since: '2026-11-10T09:30:00Z',
    ...(cells === undefined ? {} : { wait_cells: [...cells] }), ...over,
  });
}

function page(run: RunStatus): string {
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(run.run_id), run);
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: run.run_id }));
}

/** The text a reader sees: tags and their attributes removed. */
function visibleText(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').replace(/ ([;:,.])/g, '$1').trim();
}

const sentence = (run: RunStatus): string | null => {
  const line = runWaitCellsLine(run);
  return line === null ? null : runWaitCellsSentence(line);
};

describe('the words', () => {
  it('has a label for every cause the contract has, none it lacks, each in Russian and each different', () => {
    expect(Object.keys(WAIT_CAUSE_LABELS).sort()).toEqual([...RUN_WAIT_CAUSE_VALUES].sort());
    expect(new Set(Object.values(WAIT_CAUSE_LABELS)).size).toBe(RUN_WAIT_CAUSE_VALUES.length);
    for (const label of Object.values(WAIT_CAUSE_LABELS)) expect(label).not.toMatch(/[A-Za-z]/);
  });

  it('says the two causes of the owner\'s examples in his words', () => {
    expect(WAIT_CAUSE_LABELS.not_on_any_server).toBe('нет сервера с этой моделью');
    expect(WAIT_CAUSE_LABELS.at_capacity).toBe('все места сервера заняты');
  });

  it('knows the causes of the contract and not another word', () => {
    expect(knownWaitCause('login_required')).toBe('login_required');
    expect(knownWaitCause('runner_offline')).toBeNull();
    expect(knownWaitCause(undefined)).toBeNull();
    expect(knownWaitCause(null)).toBeNull();
  });
});

describe('the line', () => {
  it('names one model and its cause', () => {
    expect(sentence(waiting([cell('gpt-6-sol', 'not_on_any_server')]))).toBe('Ждём gpt-6-sol: нет сервера с этой моделью');
    expect(sentence(waiting([cell('gpt-6-sol', 'at_capacity')]))).toBe('Ждём gpt-6-sol: все места сервера заняты');
  });

  it('names two models in the order of the plan and counts the rest', () => {
    const two = [cell('gpt-6-sol', 'not_on_any_server'), cell('gpt-6-astra', 'at_capacity', 'subscription', 'blocks:leg1')];
    expect(sentence(waiting(two))).toBe('Ждём gpt-6-sol: нет сервера с этой моделью; gpt-6-astra: все места сервера заняты');
    expect(runWaitCellsLine(waiting(two))).toMatchObject({ more: 0 });
    const more = [...two, cell('gpt-6.1-sol', 'host_offline', 'api', 'correction:main'), cell('claude-opus-5-5', 'login_required', 'subscription', 'review:main')];
    expect(WAIT_MODELS_SHOWN).toBe(2);
    expect(sentence(waiting(more))).toBe('Ждём gpt-6-sol: нет сервера с этой моделью; gpt-6-astra: все места сервера заняты; и ещё 2');
    expect(sentence(waiting([...two, cell('gpt-6.1-sol', 'host_offline')]))).toContain('; и ещё 1');
  });

  it('names a model once, for its most actionable cause, however many cells and accesses wait', () => {
    const cells = [
      cell('gpt-6-sol', 'at_capacity', 'api', 'text:main'),
      cell('gpt-6-sol', 'not_on_any_server', 'subscription', 'review:main'),
      cell('gpt-6-sol', 'at_capacity', 'subscription', 'norms:main'),
    ];
    const line = runWaitCellsLine(waiting(cells));
    expect(line?.models).toEqual([{ model: 'gpt-6-sol', cause: 'not_on_any_server', text: 'нет сервера с этой моделью' }]);
    expect(line?.more).toBe(0);
  });

  it('says every cause of the contract in its own words', () => {
    for (const cause of RUN_WAIT_CAUSE_VALUES) {
      expect(sentence(waiting([cell('gpt-6-sol', cause)]))).toBe(`Ждём gpt-6-sol: ${WAIT_CAUSE_LABELS[cause]}`);
    }
  });

  it('draws nothing for a run that is not queued, without cells, with none, or with a cause it does not know', () => {
    const one = [cell('gpt-6-sol', 'not_on_any_server')];
    expect(runWaitCellsLine(waiting(one, { state: 'running' }))).toBeNull();
    expect(runWaitCellsLine(waiting(one, { state: 'published' }))).toBeNull();
    expect(runWaitCellsLine(waiting(undefined))).toBeNull();
    expect(runWaitCellsLine(waiting([]))).toBeNull();
    const strange = { cell_key: 'text:main', model_id: 'gpt-6-sol', access: 'api', cause: 'a_word_from_the_future' } as unknown as RunWaitCell;
    expect(runWaitCellsLine(waiting([strange]))).toBeNull();
    expect(sentence(waiting([strange, cell('gpt-6-astra', 'at_capacity')]))).toBe('Ждём gpt-6-astra: все места сервера заняты');
  });
});

describe('the run page', () => {
  it('says the model it waits for under the sentence of the reason, once, with the contract value in a data attribute', () => {
    const markup = page(waiting([cell('gpt-6-sol', 'not_on_any_server')]));
    expect(markup.match(/data-run-wait-cells=/g)).toHaveLength(1);
    expect(markup).toContain('data-run-wait-cause="not_on_any_server"');
    expect(markup).toContain('data-run-wait-model="gpt-6-sol"');
    const text = visibleText(markup);
    expect(text).toContain('Ждём gpt-6-sol: нет сервера с этой моделью');
    expect(text).toContain('В очереди: нужной модели сейчас нет на серверах');
    expect(text.indexOf('В очереди: нужной модели')).toBeLessThan(text.indexOf('Ждём gpt-6-sol'));
    expect(text).not.toContain('not_on_any_server');
  });

  it('adds no control: the line has no button, link, select or input', () => {
    const markup = page(waiting([cell('gpt-6-sol', 'at_capacity'), cell('gpt-6-astra', 'host_offline', 'api', 'blocks:leg1')]));
    const line = /<p[^>]*data-run-wait-cells=""[^>]*>[\s\S]*?<\/p>/.exec(markup)?.[0] ?? '';
    expect(line).not.toBe('');
    expect(line).not.toMatch(/<(button|a|select|input|textarea)\b/);
    expect(visibleText(line)).toBe('Ждём gpt-6-sol: все места сервера заняты; gpt-6-astra: сервер не на связи');
  });

  it('says nothing of it for a run that is not queued, for a queued run on the legacy route and for one whose cells the server did not name', () => {
    const one = [cell('gpt-6-sol', 'not_on_any_server')];
    expect(page(waiting(one, { state: 'running' }))).not.toContain('data-run-wait-cells');
    expect(page(waiting(undefined))).not.toContain('data-run-wait-cells');
    expect(page(runStatus({ state: 'queued', terminal_at: null, queue_reason: 'executor_at_capacity' }))).not.toContain('data-run-wait-cells');
  });
});
