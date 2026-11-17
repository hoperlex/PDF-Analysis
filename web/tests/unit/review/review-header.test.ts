/**
 * `UIP-S06-04`: the header of «Разбор» is one small line, and what used to stand over the table stands under it.
 *
 * The title, the state of the run with its mode («из записи» or «живой вызов»), the two codes and the way back to the run are
 * ONE line; the links to the object and to all objects are gone. The summary of the extended review, the line of the
 * precedents and the machine candidates are three closed blocks under the table, in that order, and the link to the
 * candidates names the block that holds them.
 *
 * The line is drawn without the shell's header (`PageShell`, `UIP-G-04`'s), so the page's own claim is what is asserted here:
 * `provider_mode` is on the header, because a run read from a record must never look like a live call.
 */

import { createElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => null,
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

import type { RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { ReviewPage } from '@/_pages/review';
import { precedentKeys } from '@/entities/decision-memory';

import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, RUN_ID, findingDetail, runStatus } from './fixtures';
import { navigation, runPrecedents, textFinding, vectorControl } from './precedents-fixtures';

afterEach(() => {
  navigation.search = '';
});

const A = textFinding('H1', 'Не указан предел огнестойкости перекрытия.');
const B = textFinding('H2', 'Ширина помещения на плане не совпадает с экспликацией.');

interface Seed {
  readonly run?: Partial<RunStatus> | null;
  readonly candidates?: boolean;
  readonly precedentsAbsent?: boolean;
  readonly search?: string;
}

/** The review screen over a seeded cache: an expert, two findings, and — as asked — the saved extended review and the night line. */
function page(seed: Seed = {}): string {
  navigation.search = seed.search ?? '';
  const client = newClient();
  const envelope = { next_cursor: null } as { next_cursor: null };
  client.setQueryData(queryKeys.account.me(), { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', roles: ['expert'], login: 'эксперт' });
  if (seed.run !== null) client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus({ run_id: RUN_ID, ...seed.run }));
  client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: [A, B], page: envelope } });
  for (const one of [A, B]) {
    client.setQueryData(queryKeys.findings.detail(one.finding_uid), { data: findingDetail({ ...one }) });
    client.setQueryData(queryKeys.findings.decisions(one.finding_uid), { data: { items: [], page: envelope } });
  }
  if (seed.candidates === true) {
    client.setQueryData(['extended-run-review', RUN_ID], {
      run_id: RUN_ID,
      status: 'completed',
      result: {
        version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
        sources: [{ source_id: 'drawing', kind: 'image', page_number: 2 }],
        observations: [{ observation_id: 'xobs_h1', title: 'Несовпадение размеров', description: 'На плане 3000 мм, в спецификации 2800 мм.', source_ids: ['drawing'] }],
      },
    });
  }
  if (seed.precedentsAbsent === true) {
    client.setQueryData(precedentKeys.run(RUN_ID), runPrecedents([], { available: false }));
    client.setQueryData(precedentKeys.vectorControl(), vectorControl({ start: '01:00', end: '06:00', tz: 'Asia/Yekaterinburg' }));
  }
  return renderWith(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
}

/** The header's markup: from its opening tag to its closing one. */
function headerOf(markup: string): string {
  const from = markup.indexOf('data-review-header');
  expect(from).toBeGreaterThan(-1);
  return markup.slice(from, markup.indexOf('</header>', from));
}

/** The opening tag of the `<details>` that carries the marker, whatever the order of its attributes. */
function detailsTag(markup: string, marker: string): string {
  const at = markup.indexOf(marker);
  expect(at, marker).toBeGreaterThan(-1);
  const from = markup.lastIndexOf('<', at);
  expect(markup.slice(from, from + 8), marker).toBe('<details');
  return markup.slice(from, markup.indexOf('>', at) + 1);
}

const isOpen = (tag: string) => /\sopen(=|\s|>)/.test(tag);

describe('the header is one small line', () => {
  it('holds the title, the state with its mode, both codes and the way back to the run', () => {
    const header = headerOf(page());
    expect(header).toContain('Разбор');
    expect(header).toContain('data-run-state="published"');
    expect(header).toContain(`data-project-uid="${PROJECT_UID}"`);
    expect(header).toContain(`data-run-id="${RUN_ID}"`);
    expect(header).toContain('К прогону');
    expect(header).toContain(`href="/projects/${PROJECT_UID}/runs/${RUN_ID}"`);
    // One header, one title: the shell's own header is not drawn as well.
    expect(page().match(/<h1[ >]/g) ?? []).toHaveLength(1);
    expect(page()).not.toContain('am-page__header');
    expect(page()).not.toContain('am-page__subtitle');
  });

  it('has no link to the object or to all objects', () => {
    const header = headerOf(page());
    expect(header).not.toContain('К объекту');
    expect(header).not.toContain('Все объекты');
    expect(header).not.toContain('К проекту');
    expect(header).not.toContain('Все проекты');
    const markup = page();
    expect(markup).not.toContain('>К объекту<');
    expect(markup).not.toContain('>Все объекты<');
  });

  it('says where the findings come from: «из записи» for a recorded run, «живой вызов» for a live one, never the other', () => {
    const recorded = headerOf(page({ run: { provider_mode: 'recorded' } }));
    expect(recorded).toContain('data-provider-mode="recorded"');
    expect(recorded).toContain('из записи');
    expect(recorded).not.toContain('data-provider-mode="live"');
    expect(recorded).not.toContain('живой вызов');

    const live = headerOf(page({ run: { provider_mode: 'live' } }));
    expect(live).toContain('data-provider-mode="live"');
    expect(live).toContain('живой вызов');
    expect(live).not.toContain('data-provider-mode="recorded"');
    expect(live).not.toContain('из записи');
  });

  it('stands over the frame of the document, and over everything else', () => {
    const markup = page();
    expect(markup.indexOf('data-review-header')).toBeLessThan(markup.indexOf('data-context-level="review"'));
    expect(markup.indexOf('data-context-level="review"')).toBeLessThan(markup.indexOf('data-finding-total'));
  });

  it('says it is loading until the run is read, and then draws no state of its own', () => {
    const header = headerOf(page({ run: null }));
    expect(header).toContain('Разбор');
    expect(header).toContain('Загрузка прогона…');
    expect(header).not.toContain('data-run-state');
    expect(header).not.toContain('data-provider-mode');
  });

  it('puts the diagnostics sentence under the line, not in it', () => {
    const quiet = page();
    expect(quiet).not.toContain('data-diagnostic-observation-count');
    const markup = page({ run: { diagnostic_observation_count: 3 } });
    expect(markup).toContain('data-diagnostic-observation-count="3"');
    expect(headerOf(markup)).not.toContain('data-diagnostic-observation-count');
    expect(markup.indexOf('data-diagnostic-observation-count')).toBeGreaterThan(markup.indexOf('</header>'));
    expect(markup.indexOf('data-diagnostic-observation-count')).toBeLessThan(markup.indexOf('data-context-level="review"'));
  });
});

describe('the blocks of the page, in order', () => {
  const full = (search?: string) => page({ candidates: true, precedentsAbsent: true, ...(search === undefined ? {} : { search }) });

  it('runs header, frame, toolbar, table, summary, precedents, candidates', () => {
    for (const markup of [full(), full('view=table')]) {
      const at = (marker: string) => {
        const found = markup.indexOf(marker);
        expect(found, marker).toBeGreaterThan(-1);
        return found;
      };
      const order = [
        at('data-review-header'),
        at('data-context-level="review"'),
        at('data-finding-total'),
        at('am-finding-list'),
        at('data-extended-summary'),
        at('data-precedents-fold'),
        at('data-review-candidates'),
      ];
      expect(order).toEqual([...order].sort((one, other) => one - other));
    }
  });

  it('draws each of the three once, and none of them over the table', () => {
    const markup = full();
    for (const marker of ['data-extended-summary', 'data-precedents-fold', 'data-review-candidates', 'data-precedents-line']) {
      expect(markup.match(new RegExp(marker, 'g')) ?? [], marker).toHaveLength(1);
      expect(markup.indexOf(marker), marker).toBeGreaterThan(markup.indexOf('am-finding-list'));
    }
  });

  it('keeps all three closed until the reader opens them', () => {
    const markup = full();
    for (const marker of ['data-extended-summary', 'data-precedents-fold', 'data-review-candidates']) {
      expect(isOpen(detailsTag(markup, marker)), marker).toBe(false);
    }
    // The line of the precedents is still the one the plan words, once, inside its block.
    expect(markup).toContain('Прецеденты считаются ночью (01:00–06:00, Asia/Yekaterinburg)');
  });

  it('names the block of the candidates in the link of the summary, and that block is a closed «details»', () => {
    const markup = full();
    expect(markup).toContain('href="#review-machine-candidates"');
    expect(isOpen(detailsTag(markup, 'id="review-machine-candidates"'))).toBe(false);
    expect(markup.indexOf('href="#review-machine-candidates"')).toBeLessThan(markup.indexOf('id="review-machine-candidates"'));
  });

  it('draws none of them when the run has nothing to say', () => {
    const markup = page();
    for (const marker of ['data-extended-summary', 'data-precedents-fold', 'data-review-candidates', 'data-precedents-line']) {
      expect(markup).not.toContain(marker);
    }
  });
});
