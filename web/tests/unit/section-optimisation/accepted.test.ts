/**
 * `UI-B-27`: «Принято» — the proposals whose decision in force is an acceptance, across a section's projects.
 *
 * Rendered, not read from source (`D-53`): the rows a reviewer would see, the saving that is not computed and is never a
 * zero, the link into the pass the proposal belongs to, the empty answer said in words, the pager, the filters, and the
 * project the address names offered even when the projects the installation lists do not include it.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ApiError, queryKeys } from '@/shared/api';
import type { ProjectUid } from '@/shared/api';
import { ACCEPTED_PAGE_LIMIT, acceptedProposalsQueryOptions } from '@/entities/optimisation-proposal';
import {
  SectionAcceptedList,
  SectionAcceptedOptimisations,
  acceptedQuantity,
  acceptedSaving,
  acceptedSectionTitle,
} from '@/widgets/section-accepted-optimisations';

import { newClient, renderScreen, seedError } from '../screens/harness';
import {
  ACCEPTED_DOCUMENT,
  ACCEPTED_PASS,
  ACCEPTED_PROJECT_A,
  ACCEPTED_PROJECT_B,
  acceptedKey,
  acceptedPage,
  acceptedRow,
  acceptedTape,
} from './fixtures';

const noop = (): void => undefined;

function list(over: { hasPrevious?: boolean; page?: ReturnType<typeof acceptedPage> } = {}): string {
  return renderToStaticMarkup(
    createElement(SectionAcceptedList, {
      page: over.page ?? acceptedPage(),
      hasPrevious: over.hasPrevious ?? false,
      onPrevious: noop,
      onNext: noop,
    }),
  );
}

/** The visible text, the figures' narrow no-break spaces read as spaces. */
function text(markup: string): string {
  return markup.replace(/<[^>]+>/g, ' ').replace(/[\u202f\u00a0]/g, ' ').replace(/\s+/g, ' ');
}

const plain = (value: string): string => value.replace(/[\u202f\u00a0]/g, ' ');

describe('the rows', () => {
  it('state the count and one row per accepted proposal, newest first as the API sent them', () => {
    const markup = list();
    expect(markup).toContain('data-accepted-count="2"');
    expect(text(markup)).toContain('Принято предложений: 2');
    const tape = markup.indexOf('Монтажная лента армированная');
    const door = markup.indexOf('Дверь противопожарная ДПМ-02/60');
    expect(tape).toBeGreaterThan(-1);
    expect(door).toBeGreaterThan(tape);
  });

  it('lead to the document’s «Оптимизация» tab on the pass the proposal belongs to', () => {
    const markup = list();
    expect(markup).toContain(
      `href="/projects/${ACCEPTED_PROJECT_A}/documents/${ACCEPTED_DOCUMENT}?tab=optimisation&amp;pass=${ACCEPTED_PASS}"`,
    );
  });

  it('say where the proposal is, who accepted it, when, and why', () => {
    const said = text(list());
    expect(said).toContain('Школа на пятьсот мест');
    expect(said).toContain('Комплект АР');
    expect(said).toContain('страница 2, позиция 1');
    expect(said).toContain('Петрова А.');
    expect(said).toContain('Подходит по огнестойкости.');
    expect(said).toContain('25 000 руб. → 21 000 руб. за шт');
  });

  it('show the saving where the API states one and say an absent one is not computed, never as zero', () => {
    expect(plain(acceptedSaving(acceptedRow()))).toBe('16 000 руб.');
    expect(acceptedSaving(acceptedTape())).toBe('не рассчитана');
    expect(acceptedSaving(acceptedTape())).not.toMatch(/\b0\b/);
    expect(plain(acceptedQuantity(acceptedRow()))).toBe('4 шт');
    expect(acceptedQuantity(acceptedTape())).toBe('не число (компл)');
    const tape = list({ page: acceptedPage({ items: [acceptedTape()], total: 1 }) });
    expect(text(tape)).toContain('не рассчитана');
  });

  it('D-346: state the server\'s percent of the price under the amount, as the proposal card does, also where the amount is not computed', () => {
    const MINUS = '\u2212';
    const markup = list();
    expect(text(markup)).toContain(`${MINUS}16 % к цене в прайс-листе`);
    expect(markup).toContain('data-saving-percent="16"');
    // The tape has no amount and has its percent: a price difference, worded as one.
    const tape = list({ page: acceptedPage({ items: [acceptedTape()], total: 1 }) });
    expect(text(tape)).toContain('не рассчитана');
    expect(text(tape)).toContain(`${MINUS}33,33 % к цене в прайс-листе`);
    expect(tape).toContain('data-saving-percent="33.33"');
    // A row that carries none (a zero current price, or a server that predates it) draws no percent and no empty wrapper.
    const { saving_percent: _omitted, ...bare } = acceptedRow();
    void _omitted;
    const none = list({ page: acceptedPage({ items: [bare], total: 1 }) });
    expect(none).not.toContain('data-saving-percent');
    expect(text(none)).not.toContain('к цене в прайс-листе');
  });

  it('name the section by its title, and leave a code this build does not know as it was sent', () => {
    expect(acceptedSectionTitle('AR')).toBe('Архитектурные решения (АР)');
    expect(acceptedSectionTitle('XX')).toBe('XX');
    expect(acceptedSectionTitle(undefined)).toBeNull();
    expect(text(list({ page: acceptedPage({ items: [acceptedRow({ section: 'KJ' })], total: 1 }) }))).toContain(
      'Конструкции железобетонные (КЖ)',
    );
  });
});

describe('the empty answer and the pager', () => {
  it('says nothing is accepted, and why unverified proposals are not here', () => {
    const markup = list({ page: acceptedPage({ items: [], total: 0 }) });
    expect(text(markup)).toContain('Нет принятых экспертом оптимизаций.');
    expect(text(markup)).toContain('Непроверенные, отклонённые и возвращённые на доработку предложения сюда намеренно не включаются');
    expect(markup).not.toContain('<table');
  });

  it('offers «Далее» only with a cursor and «Назад» only after one page', () => {
    const first = list();
    expect(first).toMatch(/<button[^>]*disabled=""[^>]*>Назад<\/button>/);
    expect(first).toMatch(/<button[^>]*disabled=""[^>]*>Далее<\/button>/);
    const middle = list({ hasPrevious: true, page: acceptedPage({ page: { next_cursor: 'abc' } }) });
    expect(middle).not.toMatch(/<button[^>]*disabled=""[^>]*>Назад<\/button>/);
    expect(middle).not.toMatch(/<button[^>]*disabled=""[^>]*>Далее<\/button>/);
    // A page past the end is a page, not "nothing accepted": the table stays so «Назад» is reachable.
    const past = list({ hasPrevious: true, page: acceptedPage({ items: [], total: 2 }) });
    expect(past).toContain('<table');
  });
});

describe('the tab as a screen', () => {
  it('reads one page under its section and project, and waits on the read', () => {
    const client = newClient();
    const markup = renderScreen(
      client,
      createElement(SectionAcceptedOptimisations, {
        sectionCode: 'KJ', projectUid: ACCEPTED_PROJECT_B as ProjectUid,
      }),
    );
    expect(markup).toContain('data-section-accepted');
    expect(client.getQueryCache().getAll().map((query) => query.queryKey)).toContainEqual(
      acceptedKey({ sectionCode: 'KJ', projectUid: ACCEPTED_PROJECT_B }),
    );
  });

  it('draws the seeded page', () => {
    const client = newClient();
    client.setQueryData(acceptedKey({ sectionCode: 'AR' }), acceptedPage());
    const markup = renderScreen(
      client,
      createElement(SectionAcceptedOptimisations, { sectionCode: 'AR', projectUid: null }),
    );
    expect(markup).toContain('data-accepted-count="2"');
  });

  it('reads nothing of the projects: the section and project choice is the page’s (`UI-B-24`)', () => {
    const client = newClient();
    renderScreen(
      client,
      createElement(SectionAcceptedOptimisations, { sectionCode: 'AR', projectUid: ACCEPTED_PROJECT_B as ProjectUid }),
    );
    const heads = client.getQueryCache().getAll().map((query) => (query.queryKey as string[])[0]);
    expect(heads).toEqual(['optimisation']);
  });

  it('says a refused read is refused and offers to try again', () => {
    const client = newClient();
    const correlation = '0f0e9d8c-7b6a-4948-b726-150413021100';
    seedError(client, acceptedKey({ sectionCode: 'AR' }), new ApiError(503, {
      contract_version: '1.51.0', error_code: 'dependency_unavailable',
      message: 'Сообщение об отказе.', correlation_id: correlation, retryable: false,
    }, correlation));
    const markup = renderScreen(
      client,
      createElement(SectionAcceptedOptimisations, { sectionCode: 'AR', projectUid: null }),
    );
    expect(markup).toContain('data-accepted-failure=');
    expect(text(markup)).toContain('Принятые оптимизации не прочитаны');
  });
});

describe('the read', () => {
  it('keys one page under its filters, with the page size', () => {
    expect(acceptedProposalsQueryOptions({ sectionCode: 'AR' }).queryKey).toEqual([
      'optimisation', 'accepted', { section_code: 'AR', limit: ACCEPTED_PAGE_LIMIT },
    ]);
    expect(
      acceptedProposalsQueryOptions({ sectionCode: 'KJ', projectUid: ACCEPTED_PROJECT_B as ProjectUid, cursor: 'c1' }).queryKey,
    ).toEqual(['optimisation', 'accepted', { project_uid: ACCEPTED_PROJECT_B, section_code: 'KJ', cursor: 'c1', limit: ACCEPTED_PAGE_LIMIT }]);
    expect(queryKeys.optimisation.allAccepted()).toEqual(['optimisation', 'accepted']);
  });
});
