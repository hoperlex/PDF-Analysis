/**
 * The card of a block finding on «Разбор» (`F8-WEB`, `D-683`, contract 1.52.0).
 *
 * A finding of a `one_list` run that comes from a drawing or a cross-check stands on portal blocks. It has no text span, so no `char_start`
 * and no quotation; the places it points at are `block_evidence`. The card must still open, on the page of its blocks, with a frame at
 * each one, and a text finding's card must stay what it was. These cases render the screen itself over a seeded cache, so what they read is
 * the markup the expert gets.
 */

import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { Finding, FindingDetail } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { BLOCK_FRAME_SENTENCES, BlockEvidenceView, ReviewPage, ReviewViewerAside, blockCardsOnPage, blockFrameOf, blockPages } from '@/_pages/review';

import { newClient, renderScreen } from '../screens/harness';
import { PROJECT_UID, RUN_ID, blockEvidence, blockFinding, decisionEvent, finding, runStatus } from './fixtures';

const BLOCK_UID = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8D';
const PAGE = { next_cursor: null } as { next_cursor: null };

function detailOf(candidate: Finding): FindingDetail {
  return { ...candidate, decision_event_count: 0, latest_comment: null };
}

/** The review screen over a run holding `findings`, the first of which is the open one, as an expert sees it. */
function review(findings: readonly Finding[], extended?: unknown, view?: 'table'): string {
  const client = newClient();
  const open = findings[0] as Finding;
  client.setQueryData(queryKeys.account.me(), { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', roles: ['expert'], login: 'эксперт' });
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus());
  client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: findings, page: PAGE } });
  client.setQueryData(queryKeys.findings.detail(open.finding_uid), { data: detailOf(open) });
  client.setQueryData(queryKeys.findings.decisions(open.finding_uid), { data: { items: [decisionEvent()], page: PAGE } });
  if (extended !== undefined) client.setQueryData(['extended-run-review', RUN_ID], { run_id: RUN_ID, status: 'completed', result: extended });
  const page = createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID });
  if (view === undefined) return renderScreen(client, page);
  // The address carries the way the findings are read (`?view=table`), as the browser's does.
  const query = new URLSearchParams({ view, finding: open.finding_uid });
  return renderScreen(
    client,
    createElement(PathnameContext.Provider, { value: '/review' }, createElement(SearchParamsContext.Provider, { value: query as never }, page)),
  );
}

describe('a block finding opens its card', () => {
  const block = blockFinding({ finding_uid: BLOCK_UID });

  it('has no text span at all, and the card draws without one', () => {
    expect(block.observation.evidence).toEqual([]);
    expect(JSON.stringify(block)).not.toContain('char_start');

    const markup = review([block]);

    expect(markup).toContain('data-block-evidence=""');
    expect(markup).toContain('data-block-card="1"');
    expect(markup).toContain('Блоки на странице 3');
    expect(markup).toContain(block.observation.finding_text);
    // The quotation viewer refuses an observation with no evidence; it must not be what drew this card.
    expect(markup).not.toContain('Нарушение целостности данных');
    expect(markup).not.toContain('data-evidence-quote');
  });

  it('is listed with its page and its «Чертёж» chip, and carries its ✓/✕', () => {
    const markup = review([block]);

    expect(markup).toContain(`data-finding-uid="${BLOCK_UID}"`);
    expect(markup).toContain('data-pages="3"');
    expect(markup).toContain('data-finding-origin="drawing"');
    expect(markup).toContain('Чертёж');
    expect(markup).toContain('data-row-actions');
  });

  it('leaves a text finding\'s card as it was: the quotation viewer, no block card', () => {
    const markup = review([finding()]);

    expect(markup).toContain('data-evidence-quote="Срок поставки составляет 30 дней."');
    expect(markup).not.toContain('data-block-evidence');
    expect(markup).not.toContain('data-finding-origin');
  });

  it('keeps a block finding with a text span on the quotation viewer: it is a text finding\'s card', () => {
    const mixed = finding({ origin: 'cross_check', block_evidence: [blockEvidence()], observation: { ...finding().observation, grounding_kind: 'portal_block' } });

    const markup = review([mixed]);

    expect(markup).toContain('data-evidence-quote=');
    expect(markup).not.toContain('data-block-evidence');
  });
});

describe('the page of a block finding', () => {
  const blocks = [
    blockEvidence({ ordinal: 1, page_number: 5, portal_block_id: `blk_${'b'.repeat(32)}`, bbox_norm: { x0: 0.1, y0: 0.1, x1: 0.3, y1: 0.2 } }),
    blockEvidence({ ordinal: 0, page_number: 3, portal_block_id: `blk_${'a'.repeat(32)}`, bbox_norm: { x0: 0.18, y0: 0.32, x1: 0.62, y1: 0.58 } }),
    blockEvidence({ ordinal: 2, page_number: 3, portal_block_id: `blk_${'c'.repeat(32)}`, bbox_norm: { x0: 0.7, y0: 0.7, x1: 0.9, y1: 0.8 }, recognised_quote: 'Размер 3000 мм' }),
  ];

  it('is offered only for the pages the blocks are on, ascending', () => {
    expect(blockPages(blocks)).toEqual([3, 5]);
  });

  it('numbers the frames of a page in the finding\'s own order, and gives each a region from its box', () => {
    const cards = blockCardsOnPage(blocks, 3);

    expect(cards.map((card) => [card.badge, card.portalBlockId.slice(4, 5), card.frame])).toEqual([['1', 'a', 'framed'], ['2', 'c', 'framed']]);
    expect(cards[0]?.target.region).toEqual([0.18, 0.32, 0.62, 0.58]);
    expect(cards[1]?.target.region).toEqual([0.7, 0.7, 0.9, 0.8]);
    // A frame is placed by its region alone: a quotation to search for would frame text nobody pointed at.
    expect(cards.every((card) => card.target.quote === undefined && card.target.rects === undefined)).toBe(true);
    expect(blockCardsOnPage(blocks, 5).map((card) => card.badge)).toEqual(['1']);
  });

  it('says in words a box it cannot frame, and never guesses a frame', () => {
    expect(blockFrameOf({ x0: 0, y0: 0, x1: 1, y1: 1 })).toBe('whole_page');
    expect(blockFrameOf({ x0: 0.5, y0: 0.2, x1: 0.4, y1: 0.9 })).toBe('unplaceable');
    expect(blockFrameOf({ x0: -0.1, y0: 0.2, x1: 0.4, y1: 0.9 })).toBe('unplaceable');
    expect(blockFrameOf({ x0: Number.NaN, y0: 0.2, x1: 0.4, y1: 0.9 })).toBe('unplaceable');

    const [whole, broken] = blockCardsOnPage(
      [blockEvidence({ ordinal: 0, bbox_norm: { x0: 0, y0: 0, x1: 1, y1: 1 } }), blockEvidence({ ordinal: 1, bbox_norm: { x0: 0.5, y0: 0.5, x1: 0.2, y1: 0.2 } })],
      3,
    );
    expect(whole?.target.region).toBeUndefined();
    expect(broken?.target.region).toBeUndefined();
    expect(BLOCK_FRAME_SENTENCES.whole_page).toContain('всю страницу');
    expect(BLOCK_FRAME_SENTENCES.unplaceable).toContain('не нарисована');
  });

  it('draws the pages bar, a card for each block with its frame sentence, and the recognised text marked as recognised', () => {
    const cards = blockCardsOnPage(blocks, 3);
    const markup = renderScreen(
      newClient(),
      createElement(BlockEvidenceView, {
        cards, pages: blockPages(blocks), page: 3, onPageChange: () => {}, activeId: cards[0]?.id ?? null, onChoose: () => {},
        viewer: createElement('div', { 'data-viewer-stub': '' }), providerMode: 'recorded',
      }),
    );

    expect(markup).toContain('data-viewer-stub');
    expect(markup).toMatch(/data-page="3" data-active="true"/);
    expect(markup).toMatch(/data-page="5" data-active="false"/);
    expect(markup.match(/data-block-card=/g)).toHaveLength(2);
    expect(markup).toContain(BLOCK_FRAME_SENTENCES.framed);
    expect(markup).toContain('data-block-recognised-quote="Размер 3000 мм"');
    expect(markup).toContain('распознано: Размер 3000 мм');
    // A block with no proved reading says nothing more than its place.
    expect(markup.match(/data-block-recognised-quote=/g)).toHaveLength(1);
    expect(markup).toContain('data-provider-mode="recorded"');
  });

  it('says a page the portal cannot place is not placed: the frame may lie elsewhere than the block', () => {
    const cards = blockCardsOnPage(blocks, 3);
    const view = (unlinkedPages?: ReadonlySet<number>) =>
      renderScreen(
        newClient(),
        createElement(BlockEvidenceView, { cards, pages: [3, 5], page: 3, onPageChange: () => {}, activeId: null, onChoose: () => {}, viewer: null, unlinkedPages }),
      );

    expect(view(new Set([3]))).toContain('data-block-page-unlinked="3"');
    expect(view(new Set([3]))).toContain('рамка может лежать не там');
    expect(view(new Set([5]))).not.toContain('data-block-page-unlinked');
    expect(view()).not.toContain('data-block-page-unlinked');
  });

  it('offers «Во весь экран» inline and not in the full-screen view', () => {
    const cards = blockCardsOnPage(blocks, 3);
    const common = { cards, pages: [3], page: 3, onPageChange: () => {}, activeId: null, onChoose: () => {}, viewer: null } as const;
    const inline = renderScreen(newClient(), createElement(BlockEvidenceView, { ...common, onExpand: () => {} }));
    const full = renderScreen(newClient(), createElement(BlockEvidenceView, { ...common, presentation: 'full', onExpand: () => {}, aside: createElement('p', null, 'Находка') }));

    expect(inline).toContain('data-expand-evidence');
    expect(full).not.toContain('data-expand-evidence');
    expect(full).toContain('data-presentation="full"');
    expect(full).toContain('Находка');
  });
});

describe('the critic\'s advice in the card of a block finding', () => {
  const block = blockFinding({ finding_uid: BLOCK_UID });
  const candidate = (over: Record<string, unknown> = {}) => ({
    observation_id: 'xobs_1', title: '', description: block.observation.finding_text, source_ids: [`blk_${'a'.repeat(32)}`],
    review: { llm_decision: 'reject', explanation: 'Размер на чертеже верный.', mode: 'model' }, ...over,
  });

  it('stands under the recommendation, in one line, when the saved review names the candidate', () => {
    const markup = review([block], { observations: [candidate()] });

    expect(markup).toContain('data-critic-advice="reject"');
    expect(markup).toContain('Совет критика: рекомендует снять наблюдение — Размер на чертеже верный.');
    expect(markup.indexOf('data-critic-advice')).toBeGreaterThan(markup.indexOf(block.observation.recommendation_text));
  });

  it('stands in the table\'s opened row too, which says the finding and its recommendation itself', () => {
    const markup = review([block], { observations: [candidate()] }, 'table');

    expect(markup).toContain('data-finding-table');
    expect(markup).toContain('data-critic-advice="reject"');
  });

  it('is not drawn when no candidate, or more than one, fits, and never for a text finding', () => {
    expect(review([block])).not.toContain('data-critic-advice');
    expect(review([block], { observations: [candidate({ description: 'Другое.' })] })).not.toContain('data-critic-advice');
    expect(review([block], { observations: [candidate(), candidate({ observation_id: 'xobs_2' })] })).not.toContain('data-critic-advice');
    expect(review([finding()], { observations: [candidate({ description: finding().observation.finding_text })] })).not.toContain('data-critic-advice');
  });

  it('stands in the full-screen view\'s side column, under the recommendation', () => {
    const markup = renderScreen(
      newClient(),
      createElement(ReviewViewerAside, {
        findingUid: BLOCK_UID, meta: 'стр. 3', text: block.observation.finding_text, recommendation: block.observation.recommendation_text,
        advice: createElement('p', { 'data-critic-advice': 'reject' }, 'Совет критика'),
      }),
    );

    expect(markup.indexOf('data-critic-advice')).toBeGreaterThan(markup.indexOf(block.observation.recommendation_text));
  });
});

describe('a run of one list', () => {
  it('drops the caption that the candidates are separate machine observations, and a text-only run keeps it', () => {
    const extended = { observations: [{ observation_id: 'xobs_9', title: 'Кандидат', description: 'Описание.', source_ids: [] }] };

    expect(review([finding(), blockFinding({ finding_uid: BLOCK_UID })], extended)).not.toContain('Это отдельные машинные наблюдения');
    expect(review([finding()], extended)).toContain('Это отдельные машинные наблюдения');
    expect(review([finding(), blockFinding({ finding_uid: BLOCK_UID })], extended)).toContain('предварительных кандидатов: 1');
  });
});
