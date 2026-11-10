/**
 * The run table of a version (`RunTable`): the dense replacement of the run-row list.
 *
 * Rendered to static markup, so the words and attributes judged are the ones a reader and the browser
 * journey meet. The four tests that used to render one `RunRow` (executor, queue capacity, executor
 * groups, presets) render a one-row table and keep their assertions; this file holds what only the
 * table has: its columns, the starter, the duration, the findings count gate, and the two ways into a run.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunState, RunStatus } from '@/shared/api';
import { RUN_STATE_VALUES, queryKeys } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { RUN_PAGE_LIMIT, RunTable, STARTED_BY_UNKNOWN } from '@/entities/audit-run';
import { RunList } from '@/widgets/run-list';

import { PROJECT_UID, RUN_ID, VERSION_UID, render, runStatus } from '../review/fixtures';
import { newClient, renderScreen } from '../screens/harness';

const RUN_HREF = (run: RunStatus): string => `/runs/${run.run_id}`;
const REVIEW_HREF = (run: RunStatus): string => `/reviews/${run.run_id}`;

function table(...runs: RunStatus[]): string {
  return render(createElement(RunTable, { runs, runHref: RUN_HREF, reviewHref: REVIEW_HREF }));
}

const text = (html: string): string => html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

/** The cells of the first body row, as visible text, in column order. */
function cellsOf(markup: string): string[] {
  const body = markup.slice(markup.indexOf('<tbody>'));
  const row = body.slice(0, body.indexOf('</tr>'));
  return [...row.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((cell) => text(cell[1] as string));
}

/** A reading that omits one optional field, as the server does (`exactOptionalPropertyTypes` forbids setting it to `undefined`). */
function without(run: RunStatus, key: 'terminal_at' | 'published_finding_count'): RunStatus {
  const copy: Record<string, unknown> = { ...run };
  delete copy[key];
  return copy as unknown as RunStatus;
}

const runIdAt = (digit: string): string => `${RUN_ID.slice(0, -1)}${digit}`;

describe('the columns', () => {
  it('are the six the owner named, in order, each a column header', () => {
    const markup = table(runStatus());
    const heads = [...markup.matchAll(/<th[^>]*scope="col"[^>]*>([\s\S]*?)<\/th>/g)].map((head) => text(head[1] as string));
    expect(heads).toEqual(['Состояние', 'Начат', 'Запустил', 'Длительность', 'Находок', 'Действия']);
  });

  it('are a table and not a list of blocks', () => {
    const markup = table(runStatus());
    expect(markup).toContain('<table');
    expect(markup).not.toContain('am-rows');
    expect(markup).not.toContain('<ul');
    expect(markup).not.toContain('<li');
  });

  it('give one body row to each run, keyed by its identity', () => {
    const markup = table(runStatus(), runStatus({ run_id: runIdAt('9') }), runStatus({ run_id: runIdAt('8') }));
    expect(markup.match(/<tr[^>]*data-row-key=/g)).toHaveLength(3);
    for (const id of [RUN_ID, runIdAt('9'), runIdAt('8')]) {
      expect(markup).toContain(`data-row-key="${id}"`);
      expect(markup.match(new RegExp(`data-run-id="${id}"`, 'g'))).toHaveLength(1);
    }
  });
});

describe('the cells of one run', () => {
  const run = runStatus({ started_by_label: 'Проверкина А. С.' });

  it('say the state with its provider mode, when it began, who started it, how long it took, how many findings', () => {
    const cells = cellsOf(table(run));
    expect(cells).toHaveLength(6);
    expect(cells[0]).toBe('опубликован из записи');
    expect(cells[1]).toBe(formatInstant('2026-09-10T08:00:00.000Z'));
    expect(cells[2]).toBe('Проверкина А. С.');
    expect(cells[3]).toBe('4 мин 0 с');
    expect(cells[4]).toBe('1');
    expect(cells[5]).toBe('Прогон Разобрать');
  });

  it('carry the state badge, with the provider mode, in the first cell', () => {
    const markup = table(run);
    const first = markup.slice(markup.indexOf('<td'), markup.indexOf('</td>'));
    expect(first).toContain('data-run-id="' + RUN_ID + '"');
    expect(first).toContain('data-run-state="published"');
    expect(first).toContain('data-provider-mode="recorded"');
  });

  it('say «неизвестно» for a starter the reading does not name, absent or blank, and never an account id', () => {
    for (const over of [{}, { started_by_label: '' }, { started_by_label: '   ' }] as Partial<RunStatus>[]) {
      const markup = table(runStatus({ ...over, started_by_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' }));
      expect(cellsOf(markup)[2], JSON.stringify(over)).toBe(STARTED_BY_UNKNOWN);
      expect(markup).not.toContain('usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B');
    }
    expect(STARTED_BY_UNKNOWN).toBe('неизвестно');
  });

  it('say the duration only when the run has ended, from its two instants', () => {
    expect(cellsOf(table(runStatus({ created_at: '2026-09-10T08:00:00.000Z', terminal_at: '2026-09-10T08:00:00.030Z' })))[3]).toBe('30 мс');
    expect(cellsOf(table(runStatus({ created_at: '2026-09-10T08:00:00.000Z', terminal_at: '2026-09-10T08:00:12.300Z' })))[3]).toBe('12 с');
    expect(cellsOf(table(runStatus({ state: 'running', terminal_at: null })))[3]).toBe('—');
    expect(cellsOf(table(without(runStatus({ state: 'queued' }), 'terminal_at')))[3]).toBe('—');
  });
});

describe('the findings count', () => {
  it('is drawn for the states that can publish, with the count the reading carries', () => {
    expect(cellsOf(table(runStatus({ state: 'published', published_finding_count: 7 })))[4]).toBe('7');
    expect(cellsOf(table(runStatus({ state: 'partial', published_finding_count: 0 })))[4]).toBe('0');
  });

  it('is a dash when a state that can publish carries no count', () => {
    expect(cellsOf(table(without(runStatus({ state: 'published' }), 'published_finding_count')))[4]).toBe('—');
  });

  it('is a dash for every other state, even if the reading carries a number', () => {
    for (const state of RUN_STATE_VALUES as readonly RunState[]) {
      if (state === 'published' || state === 'partial') continue;
      expect(cellsOf(table(runStatus({ state, published_finding_count: 5 })))[4], state).toBe('—');
    }
  });
});

describe('the two ways into a run', () => {
  const links = (markup: string): { readonly href: string; readonly label: string }[] =>
    [...markup.matchAll(/<a [^>]*href="([^"]*)"[^>]*>([\s\S]*?)<\/a>/g)].map((link) => ({ href: link[1] as string, label: text(link[2] as string) }));

  it('always open the run, at the address the screen built, and name the run in the tooltip', () => {
    const markup = table(runStatus({ state: 'failed' }));
    expect(links(markup)).toEqual([{ href: `/runs/${RUN_ID}`, label: 'Прогон' }]);
    expect(markup).toContain(`title="${RUN_ID}"`);
  });

  it('open the findings, at the address the screen built, for a run with a published result', () => {
    for (const state of ['published', 'partial'] as const) {
      expect(links(table(runStatus({ state }))), state).toEqual([
        { href: `/runs/${RUN_ID}`, label: 'Прогон' },
        { href: `/reviews/${RUN_ID}`, label: 'Разобрать' },
      ]);
    }
  });

  it('offer no review for a run that has no published result', () => {
    for (const state of RUN_STATE_VALUES as readonly RunState[]) {
      if (state === 'published' || state === 'partial') continue;
      const markup = table(runStatus({ state }));
      expect(markup, state).not.toContain('Разобрать');
      expect(markup, state).not.toContain('/reviews/');
    }
  });
});

describe('the version’s run list', () => {
  it('draws the table, builds both addresses from the project and the run, and keeps the run count', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items: [runStatus(), runStatus({ run_id: runIdAt('9'), state: 'failed' })],
      page: { next_cursor: null },
    });
    const markup = renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
    expect(markup).toContain('data-run-count="2"');
    expect(markup).toContain('<table');
    expect(markup).not.toContain('am-rows');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${RUN_ID}"`);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${RUN_ID}/review"`);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${runIdAt('9')}"`);
    expect(markup).not.toContain(`href="/projects/${PROJECT_UID}/runs/${runIdAt('9')}/review"`);
  });
});
