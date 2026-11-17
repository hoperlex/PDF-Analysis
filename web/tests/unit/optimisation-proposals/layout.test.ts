/**
 * `UI-B-06`, `UIP-S09-01`: the proposals of a pass in two layouts -- the original's table (the default) and the cards -- and the choice in
 * the address.
 *
 * Each half has a case that shows it can fail:
 *
 *   - the address is read and written as a pure pair: «Таблица» is the absent parameter, `?layout=cards` opens the cards and the earlier
 *     `?layout=table` still opens the table, a value outside the closed set reads as the default and is never echoed, a parameter that
 *     is not this one is carried through;
 *   - the table is one header over a row per proposal, and the row carries the markers the card carries (`data-proposal`,
 *     `data-decision`, «Открыть лист»), the decision line, the controls and the history of the same proposal, and a block row only
 *     where the container gave it a strip;
 *   - the link to the other layout is drawn only where the container can write the address, and says which layout it opens;
 *   - the container (the live `OptimisationProposals`) reads `?layout=` from the router: under no parameter and under `table` it asks the
 *     server for the original's fifty and draws the table, under `cards` it asks for its own twenty and draws cards.
 */

import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const router = vi.hoisted(() => ({ params: null as URLSearchParams | null }));

vi.mock('next/navigation', () => ({ useSearchParams: () => router.params }));

import { queryKeys } from '@/shared/api';
import { PROPOSAL_PAGE_LIMIT } from '@/entities/optimisation-proposal';
import {
  DEFAULT_PROPOSAL_LAYOUT,
  LayoutSwitch,
  OptimisationProposals,
  PROPOSAL_LAYOUT_PARAM,
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
  it('reads cards, and anything else as the table', () => {
    expect(read('layout=cards')).toBe('cards');
    expect(read('layout=table')).toBe('table');
    expect(read('')).toBe('table');
    expect(read('layout=')).toBe('table');
    expect(read('layout=grid')).toBe('table');
    expect(read('layout=CARDS')).toBe('table');
  });

  it('has the table as its default and `layout` as its parameter', () => {
    expect(DEFAULT_PROPOSAL_LAYOUT).toBe('table');
    expect(PROPOSAL_LAYOUT_PARAM).toBe('layout');
  });

  it('writes cards, and the table as the absent parameter', () => {
    expect(writeProposalLayout(new URLSearchParams(''), 'cards').toString()).toBe('layout=cards');
    expect(writeProposalLayout(new URLSearchParams('layout=cards'), 'table').toString()).toBe('');
  });

  it('writes an address of the earlier form, `?layout=table`, as the absent parameter', () => {
    expect(writeProposalLayout(new URLSearchParams('layout=table'), 'table').toString()).toBe('');
    expect(writeProposalLayout(new URLSearchParams('layout=table'), 'cards').toString()).toBe('layout=cards');
  });

  it('carries the parameters of the tab and the pass through a write', () => {
    expect(writeProposalLayout(new URLSearchParams('tab=optimisation&pass=opp_1&project=prj_1'), 'cards').toString()).toBe(
      'tab=optimisation&pass=opp_1&project=prj_1&layout=cards',
    );
    expect(writeProposalLayout(new URLSearchParams('tab=optimisation&layout=cards&pass=opp_1'), 'table').toString()).toBe(
      'tab=optimisation&pass=opp_1',
    );
  });

  it('asks for the original’s fifty in the table and for the cards’ own page otherwise', () => {
    expect(TABLE_PAGE_LIMIT).toBe(50);
    expect(pageLimitOf('table', PROPOSAL_PAGE_LIMIT)).toBe(50);
    expect(pageLimitOf('cards', PROPOSAL_PAGE_LIMIT)).toBe(PROPOSAL_PAGE_LIMIT);
    expect(pageLimitOf(DEFAULT_PROPOSAL_LAYOUT, PROPOSAL_PAGE_LIMIT)).toBe(50);
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
    // The rows stand by verdict (`row-order.test.ts`), so the cells are told by the number their own controls carry.
    const own = cells.map((cell) => /data-test-controls="(\d+)"/.exec(cell)?.[1]);
    expect([...own].sort()).toEqual(['1', '2']);
    cells.forEach((cell, index) => {
      expect(cell).toContain(`data-test-history="${own[index]}"`);
      expect(cell.match(/data-test-controls=/g)).toHaveLength(1);
    });
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

describe('the link to the other layout', () => {
  const list = (props: Record<string, unknown>) =>
    renderScreen(newClient(), createElement(ProposalListView, { page: proposalPage(), canDecide: false, onDecision: noop, onPage: noop, ...props }));

  it('draws the table with no layout given, and offers «Показать карточками» as a link, not as a pair of buttons', () => {
    const table = list({ onLayout: noop });
    expect(table).toContain('data-proposal-table');
    expect(table).not.toContain('<article');
    expect(table).toContain('aria-label="Раскладка предложений"');
    expect(table).toContain('data-proposal-layout="table"');
    expect(table).toContain('Показать карточками');
    expect(table).not.toContain('Показать таблицей');
    expect(table).not.toMatch(/aria-pressed="[^"]*"[^>]*>(Таблица|Карточки)</);
    expect(table.match(/data-proposal-layout-link=/g)).toHaveLength(1);
    expect(table).toMatch(/<button[^>]*data-proposal-layout-link="cards"[^>]*>Показать карточками<\/button>/);
  });

  it('draws the cards where they are chosen, with the way back to the table', () => {
    const cards = list({ onLayout: noop, layout: 'cards' });
    expect(cards).toContain('<article');
    expect(cards).not.toContain('data-proposal-table');
    expect(cards).toContain('data-proposal-layout="cards"');
    expect(cards).toContain('Показать таблицей');
    expect(cards).not.toContain('Показать карточками');
    expect(cards).toMatch(/<button[^>]*data-proposal-layout-link="table"[^>]*>Показать таблицей<\/button>/);
  });

  it('asks the container for the other layout when it is pressed', () => {
    const asked: string[] = [];
    const press = (selected: 'table' | 'cards') => {
      const nav = LayoutSwitch({ selected, onSelect: (layout) => asked.push(layout) });
      (nav.props as { children: { props: { onClick: () => void } } }).children.props.onClick();
    };
    press('table');
    press('cards');
    expect(asked).toEqual(['cards', 'table']);
  });

  it('is not drawn where nothing can write the address', () => {
    expect(list({})).not.toContain('Раскладка предложений');
    expect(list({ layout: 'cards' })).not.toContain('Показать таблицей');
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

  it('draws the table, from the page of fifty, with no parameter', () => {
    router.params = new URLSearchParams('');
    const markup = renderScreen(seeded(TABLE_PAGE_LIMIT), section());
    expect(markup).toContain('data-proposal-table');
    expect(markup).not.toContain('<article');
    expect(markup).toContain('data-proposal-layout="table"');
    expect(markup).toContain('Показать карточками');
  });

  it('draws the table, from the page of fifty, under the earlier ?layout=table', () => {
    router.params = new URLSearchParams('layout=table');
    const markup = renderScreen(seeded(TABLE_PAGE_LIMIT), section());
    expect(markup).toContain('data-proposal-table');
    expect(markup).not.toContain('<article');
    expect(markup).toContain('data-proposal-layout="table"');
  });

  it('draws cards, from the cards’ own page, under ?layout=cards', () => {
    router.params = new URLSearchParams('layout=cards');
    const markup = renderScreen(seeded(PROPOSAL_PAGE_LIMIT), section());
    expect(markup).toContain('<article');
    expect(markup).not.toContain('data-proposal-table');
    expect(markup).toContain('data-proposal-layout="cards"');
    expect(markup).toContain('Показать таблицей');
  });

  it('does not draw the cards from a cache entry of the table’s size', () => {
    // Under `cards` the page asked for is the cards' own twenty; the fifty seeded for the table is another entry, so nothing is drawn from it.
    router.params = new URLSearchParams('layout=cards');
    const markup = renderScreen(seeded(TABLE_PAGE_LIMIT), section());
    expect(markup).not.toContain('<article');
  });

  it('does not draw the table from a cache entry of the cards’ size', () => {
    // The default is the table: the twenty seeded for the cards is not the page it asks for.
    router.params = new URLSearchParams('');
    const markup = renderScreen(seeded(PROPOSAL_PAGE_LIMIT), section());
    expect(markup).not.toContain('data-proposal-table');
  });
});
