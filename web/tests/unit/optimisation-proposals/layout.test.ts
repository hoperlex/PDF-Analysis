/**
 * `UI-B-06`: the proposals of a pass in two layouts -- the cards (the default) and the original's table -- and the choice in the address.
 *
 * Each half has a case that shows it can fail:
 *
 *   - the address is read and written as a pure pair: «Карточки» is the absent parameter, a value outside the closed set reads as the
 *     default and is never echoed, a parameter that is not this one is carried through;
 *   - the table is one header over a row per proposal, and the row carries the markers the card carries (`data-proposal`,
 *     `data-decision`, «Открыть лист»), the decision line, the controls and the history of the same proposal, and a block row only
 *     where the container gave it a strip;
 *   - the switch is drawn only where the container can write the address, and says which layout is pressed;
 *   - the container (the live `OptimisationProposals`) reads `?layout=` from the router: under `table` it asks the server for the
 *     original's fifty and draws the table, under no parameter it asks for its own twenty and draws cards.
 */

import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const router = vi.hoisted(() => ({ params: null as URLSearchParams | null }));

vi.mock('next/navigation', () => ({ useSearchParams: () => router.params }));

import { queryKeys } from '@/shared/api';
import { PROPOSAL_PAGE_LIMIT } from '@/entities/optimisation-proposal';
import {
  OptimisationProposals,
  ProposalListView,
  TABLE_PAGE_LIMIT,
  pageLimitOf,
  readProposalLayout,
  writeProposalLayout,
} from '@/widgets/optimisation-proposals';

import { newClient, renderScreen } from '../screens/harness';
import {
  AR_DOCUMENT_UID,
  PASS_ID,
  PROPOSALS_PROJECT_UID,
  SHEET_URL,
  arVersion,
  decision,
  pass,
  proposal,
  proposalPage,
  tapeProposal,
} from './fixtures';

const noop = (): void => {};

const read = (query: string) => readProposalLayout(new URLSearchParams(query));

beforeEach(() => {
  router.params = null;
});

afterEach(() => {
  router.params = null;
});

describe('the layout address', () => {
  it('reads table, and anything else as cards', () => {
    expect(read('layout=table')).toBe('table');
    expect(read('layout=cards')).toBe('cards');
    expect(read('')).toBe('cards');
    expect(read('layout=')).toBe('cards');
    expect(read('layout=grid')).toBe('cards');
    expect(read('layout=TABLE')).toBe('cards');
  });

  it('writes the table, and cards as the absent parameter', () => {
    expect(writeProposalLayout(new URLSearchParams(''), 'table').toString()).toBe('layout=table');
    expect(writeProposalLayout(new URLSearchParams('layout=table'), 'cards').toString()).toBe('');
  });

  it('carries the parameters of the tab and the pass through a write', () => {
    expect(writeProposalLayout(new URLSearchParams('tab=optimisation&pass=opp_1&project=prj_1'), 'table').toString()).toBe(
      'tab=optimisation&pass=opp_1&project=prj_1&layout=table',
    );
    expect(writeProposalLayout(new URLSearchParams('tab=optimisation&layout=table&pass=opp_1'), 'cards').toString()).toBe(
      'tab=optimisation&pass=opp_1',
    );
  });

  it('asks for the original’s fifty in the table and for the cards’ own page otherwise', () => {
    expect(TABLE_PAGE_LIMIT).toBe(50);
    expect(pageLimitOf('table', PROPOSAL_PAGE_LIMIT)).toBe(50);
    expect(pageLimitOf('cards', PROPOSAL_PAGE_LIMIT)).toBe(PROPOSAL_PAGE_LIMIT);
  });
});

describe('the table layout of a page', () => {
  const view = (props: Record<string, unknown> = {}) =>
    renderScreen(
      newClient(),
      createElement(ProposalListView, {
        page: proposalPage({ items: [proposal({ current_verdict: 'accept', current_decision: decision({ verdict: 'accept' }), saving_percent: '16' }), tapeProposal()] }),
        canDecide: true,
        onDecision: noop,
        onPage: noop,
        layout: 'table',
        onLayout: noop,
        ...props,
      }),
    );

  it('is one header over a row per proposal, and no card', () => {
    const markup = view();
    expect(markup).toContain('data-proposal-table');
    expect(markup).not.toContain('<article');
    const header = /<thead>([\s\S]*?)<\/thead>/.exec(markup)?.[1] ?? '';
    expect([...header.matchAll(/<th[^>]*>([^<]*)<\/th>/g)].map((cell) => cell[1])).toEqual([
      '№',
      'Строка спецификации',
      'Сейчас в прайс-листе',
      'Дешёвый аналог',
      'Экономия',
      'Основание',
      'Решение',
    ]);
    expect(markup.match(/<tr data-proposal="/g)).toHaveLength(2);
    expect(markup).toContain('data-decision="accept"');
  });

  it('keeps what a card says of a proposal: the row text, both positions, the saving with its percent and the decision', () => {
    const markup = view();
    expect(markup).toContain('Дверь противопожарная ДПМ-01/60 ООО «Промет»');
    expect(markup).toContain('Поставщик: Кнауф Гипс');
    expect(markup).toContain('data-saving-percent');
    expect(markup).toContain('Решение: <strong>принято</strong>');
  });

  it('puts the controls and the history of each proposal in its own decision cell', () => {
    const markup = view({
      controlsFor: (item: { ordinal: number }) => createElement('div', { 'data-test-controls': item.ordinal }),
      historyFor: (item: { ordinal: number }) => createElement('div', { 'data-test-history': item.ordinal }),
    });
    const cells = [...markup.matchAll(/<td class="[^"]*judgement[^"]*">([\s\S]*?)<\/td>/g)].map((cell) => cell[1] ?? '');
    expect(cells).toHaveLength(2);
    expect(cells[0]).toContain('data-test-controls="1"');
    expect(cells[0]).toContain('data-test-history="1"');
    expect(cells[0]).not.toContain('data-test-controls="2"');
    expect(cells[1]).toContain('data-test-controls="2"');
  });

  it('draws no controls for a reader who cannot decide', () => {
    const markup = view({
      canDecide: false,
      controlsFor: () => createElement('div', { 'data-test-controls': '' }),
    });
    expect(markup).not.toContain('data-test-controls');
  });

  it('offers «Открыть лист» as the card does, and a block row only where there is a strip', () => {
    const none = view({ sheet: { url: SHEET_URL, isLoading: false, failure: null, onRetry: noop } });
    expect(none).toContain('data-open-sheet="2"');
    expect(none).not.toContain('data-proposal-blocks-row');
    const strips = view({ blocksFor: (item: { ordinal: number }) => (item.ordinal === 1 ? createElement('div', { 'data-test-strip': '' }) : null) });
    expect(strips.match(/data-proposal-blocks-row=/g)).toHaveLength(1);
    expect(strips).toMatch(/<td colSpan="7"><div data-test-strip="">|<td colspan="7"><div data-test-strip="">/);
  });

  it('says that nothing matches, in either layout, when the page is empty', () => {
    const empty = view({ page: proposalPage({ items: [], total: 0, decision: 'accept' }) });
    expect(empty).toContain('Нет предложений в выбранном состоянии');
    expect(empty).not.toContain('data-proposal-table');
  });
});

describe('the switch', () => {
  const list = (props: Record<string, unknown>) =>
    renderScreen(newClient(), createElement(ProposalListView, { page: proposalPage(), canDecide: false, onDecision: noop, onPage: noop, ...props }));

  it('is drawn where the container can write the address, with the pressed layout marked', () => {
    const cards = list({ onLayout: noop });
    expect(cards).toContain('aria-label="Раскладка предложений"');
    expect(cards).toContain('data-proposal-layout="cards"');
    expect(cards).toMatch(/aria-pressed="true"[^>]*>Карточки</);
    expect(cards).toMatch(/aria-pressed="false"[^>]*>Таблица</);
    expect(cards).toContain('<article');
    const table = list({ onLayout: noop, layout: 'table' });
    expect(table).toContain('data-proposal-layout="table"');
    expect(table).toMatch(/aria-pressed="true"[^>]*>Таблица</);
  });

  it('is not drawn where nothing can write the address', () => {
    expect(list({})).not.toContain('Раскладка предложений');
  });
});

describe('the container follows the address', () => {
  const documents = queryKeys.projects.documents(PROPOSALS_PROJECT_UID, undefined, 50);
  const passes = queryKeys.optimisation.passes(PROPOSALS_PROJECT_UID, AR_DOCUMENT_UID);

  function seeded(limit: number) {
    const client = newClient();
    client.setQueryData(documents, { items: [arVersion()], page: { next_cursor: null } as never });
    client.setQueryData(passes, { items: [pass()] });
    client.setQueryData(queryKeys.optimisation.proposals(PASS_ID, null, 0, limit), proposalPage({ limit }));
    return client;
  }

  const section = () => createElement(OptimisationProposals, { projectUid: PROPOSALS_PROJECT_UID, roles: ['expert'] });

  it('draws cards, from the cards’ own page, with no parameter', () => {
    router.params = new URLSearchParams('');
    const markup = renderScreen(seeded(PROPOSAL_PAGE_LIMIT), section());
    expect(markup).toContain('<article');
    expect(markup).not.toContain('data-proposal-table');
    expect(markup).toContain('data-proposal-layout="cards"');
  });

  it('draws the table, from the page of fifty, under ?layout=table', () => {
    router.params = new URLSearchParams('layout=table');
    const markup = renderScreen(seeded(TABLE_PAGE_LIMIT), section());
    expect(markup).toContain('data-proposal-table');
    expect(markup).not.toContain('<article');
    expect(markup).toContain('data-proposal-layout="table"');
  });

  it('does not draw the table from a cache entry of the cards’ size', () => {
    // Under `table` the page asked for is the fifty; the twenty seeded for the cards is another entry, so nothing is drawn from it.
    router.params = new URLSearchParams('layout=table');
    const markup = renderScreen(seeded(PROPOSAL_PAGE_LIMIT), section());
    expect(markup).not.toContain('data-proposal-table');
  });
});
