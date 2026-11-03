/**
 * The quotation cards beside the page, and how a quotation becomes a target.
 *
 * The quotation is the evidence and the frame is a navigation aid, so every card renders the
 * server's string byte for byte in every state of its frame, says in one line how the frame was
 * found (or that it was not), and carries the number of the frame it belongs to. Cards and
 * targets are numbered the same way, so the number on the page is the number on the card.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { BlockGeometry, VersionBlockIndex } from '@/shared/api';
import type { TargetResolution } from '@/features/open-evidence';
import { EvidenceViewer, QuotationCard } from '@/widgets/evidence-viewer';
import { quotationTargetId, quotationTargets } from '@/widgets/evidence-viewer/model/quotation-targets';

import { AWKWARD_QUOTES, evidence, observation, render } from './fixtures';

const BLOB = 'blob:https://app.test/0f0e9d8c-7b6a-5948-3726-150413021100';

const found = (method: 'lines' | 'text' | 'region', occurrences = 1): TargetResolution => ({ status: 'found', method, occurrences });
const NOT_FOUND: TargetResolution = { status: 'not-found', method: null, occurrences: 0 };
const NO_TEXT: TargetResolution = { status: 'no-text-layer', method: null, occurrences: 0 };

function card(placement: TargetResolution | null, overrides: { quote?: string; active?: boolean; badge?: string } = {}) {
  return render(
    createElement(
      'ul',
      null,
      createElement(QuotationCard, {
        item: evidence({ evidence_ordinal: 2, page_number: 4, quote: overrides.quote ?? 'точная строка' }),
        badge: overrides.badge ?? '2',
        placement,
        active: overrides.active ?? false,
        onSelect: () => {},
      }),
    ),
  );
}

describe('the sentence under a quotation says how its frame was found', () => {
  it('says nothing while the page is still being read', () => {
    const markup = card(null);
    expect(markup).toContain('data-quote-located="pending"');
    expect(markup).not.toContain('Отмечено');
    expect(markup).not.toContain('Найдено');
    expect(markup).not.toContain('не найден');
  });

  it('names the line geometry when that placed it', () => {
    const markup = card(found('lines'));
    expect(markup).toContain('Отмечено по разметке строк.');
    expect(markup).toContain('data-quote-located="true"');
    expect(markup).toContain('data-quote-method="lines"');
    expect(markup).not.toContain('role="status"');
  });

  it('names the text search when that placed it, and says how many times it was found', () => {
    expect(card(found('text'))).toContain('Найдено в тексте страницы.');
    const several = card(found('text', 3));
    expect(several).toContain('Найдено в тексте страницы, совпадений: 3.');
    expect(several).toContain('data-quote-occurrences="3"');
  });

  it('says the fragment is not on the page, in a status the reader is told about', () => {
    const markup = card(NOT_FOUND);
    expect(markup).toContain('На странице фрагмент не найден — сверяйте по цитате.');
    expect(markup).toContain('data-quote-located="false"');
    expect(markup).toContain('role="status"');
  });

  it('says a page without a text layer could not be searched, not that nothing matched', () => {
    const markup = card(NO_TEXT);
    expect(markup).toContain('нет текстового слоя');
    expect(markup).toContain('сверяйте по цитате');
    expect(markup).not.toContain('На странице фрагмент не найден');
  });

  it.each([null, found('lines'), found('text', 2), NOT_FOUND, NO_TEXT])(
    'renders the quotation byte-for-byte whatever the frame says (%j)',
    (placement) => {
      for (const quote of AWKWARD_QUOTES) {
        const markup = card(placement, { quote });
        const attribute = markup.match(/data-evidence-quote="([^"]*)"/)?.[1] ?? '';
        const decoded = attribute
          .replaceAll('&quot;', '"')
          .replaceAll('&#x27;', "'")
          .replaceAll('&lt;', '<')
          .replaceAll('&gt;', '>')
          .replaceAll('&amp;', '&');
        expect(decoded).toBe(quote);
      }
    },
  );
});

describe('a card is tied to its frame', () => {
  it('carries the number of the frame on a button that says what it does', () => {
    const markup = card(found('lines'), { badge: '3' });
    expect(markup).toMatch(/<button[^>]*aria-label="Показать фрагмент 3 на странице"[^>]*>3<\/button>/);
  });

  it('shows which card the viewer is on', () => {
    const on = card(found('lines'), { active: true });
    const off = card(found('lines'), { active: false });
    expect(on).toContain('data-active="true"');
    expect(on).toContain('aria-pressed="true"');
    expect(off).toContain('data-active="false"');
    expect(off).toContain('aria-pressed="false"');
  });

  it('never prints the character range or the block handle', () => {
    const markup = render(
      createElement(
        'ul',
        null,
        createElement(QuotationCard, {
          item: evidence({ evidence_ordinal: 1, page_number: 4, quote: 'точная строка', char_start: 4711, char_end: 4724, block_id: 'b_000042' }),
          badge: '1',
          placement: found('lines'),
          active: true,
        }),
      ),
    );
    expect(markup).not.toContain('4711');
    expect(markup).not.toContain('4724');
    expect(markup).not.toContain('b_000042');
  });
});

describe('quotations become targets, numbered as the cards are', () => {
  const block = (overrides: Partial<BlockGeometry> & Pick<BlockGeometry, 'char_start' | 'char_end'>): BlockGeometry => ({
    bbox: { x0: 50, y0: 100, x1: 300, y1: 112 },
    bbox_origin: 'top_left',
    bbox_unit: 'pt',
    block_id: 'b_000001',
    block_ordinal: 0,
    page_number: 4,
    ...overrides,
  });
  const index: VersionBlockIndex = {
    block_count: 1,
    blocks: [block({ char_start: 100, char_end: 113 })],
    produced_by_run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
    status: 'produced',
    text_layer_sha256: 'a'.repeat(64),
    version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  };
  const quote = 'точная строка';
  const items = [
    evidence({ evidence_ordinal: 5, page_number: 4, quote, char_start: 100, char_end: 100 + [...quote].length }),
    evidence({ evidence_ordinal: 9, page_number: 4, quote: 'другая', char_start: 100, char_end: 106 }),
  ];

  it('numbers the badges 1..n in card order and keys the ids by the contract’s ordinal', () => {
    const targets = quotationTargets(items, null);
    expect(targets.map((t) => [t.id, t.badge, t.quote])).toEqual([
      ['q5', '1', quote],
      ['q9', '2', 'другая'],
    ]);
    expect(quotationTargetId(items[0]!)).toBe('q5');
  });

  it('attaches the server’s lines only to a quotation whose anchor agrees with it', () => {
    const agreeing = quotationTargets(items.slice(0, 1), index)[0];
    expect(agreeing?.rects).toEqual([{ left: 50, top: 100, width: 250, height: 12 }]);
    // Same range, but a quotation of another length: the card reports a discrepancy and the
    // lines picked by that range would frame text nobody quoted.
    const disagreeing = quotationTargets([evidence({ evidence_ordinal: 1, page_number: 4, quote: 'длинная цитата', char_start: 100, char_end: 103 })], index)[0];
    expect(disagreeing?.rects).toBeUndefined();
    expect(disagreeing?.quote).toBe('длинная цитата');
  });

  it('attaches nothing without an index, or with one that was not produced', () => {
    expect(quotationTargets(items.slice(0, 1), null)[0]?.rects).toBeUndefined();
    expect(quotationTargets(items.slice(0, 1), { ...index, status: 'not_produced', blocks: [], block_count: 0 })[0]?.rects).toBeUndefined();
  });
});

describe('the screen around the page', () => {
  const view = (activePage: number) =>
    render(
      createElement(EvidenceViewer, {
        observation: observation({
          evidence: [
            evidence({ evidence_ordinal: 1, page_number: 4, quote: 'первая цитата' }),
            evidence({ evidence_ordinal: 2, page_number: 4, quote: 'вторая цитата' }),
            evidence({ evidence_ordinal: 3, page_number: 9, quote: 'цитата на другой странице' }),
          ],
        }),
        activePage,
        onPageChange: () => {},
        documentUrl: BLOB,
      }),
    );

  it('numbers the cards of the page 1..n and claims nothing before the page is read', () => {
    const markup = view(4);
    expect(markup).toContain('aria-label="Показать фрагмент 1 на странице"');
    expect(markup).toContain('aria-label="Показать фрагмент 2 на странице"');
    expect(markup).not.toContain('Показать фрагмент 3');
    expect(markup.match(/data-quote-located="pending"/g)).toHaveLength(2);
  });

  it('replaces the old statement that there is no highlight with a true one about the frames', () => {
    const markup = view(4);
    expect(markup).not.toContain('Навигация только по страницам');
    expect(markup).not.toContain('без подсветки фрагмента и рамки');
    expect(markup).toContain('Рамки и подсветка на странице помогают найти место');
    expect(markup).toContain('Свидетельство — цитата');
  });

  it('keeps the viewer on the declared page and leaves no browser reader on the screen', () => {
    const markup = view(9);
    expect(markup).toContain('data-viewer-page="9"');
    expect(markup).toContain('цитата на другой странице');
    expect(markup).not.toContain('первая цитата');
    expect(markup).not.toContain('<object');
  });
});
