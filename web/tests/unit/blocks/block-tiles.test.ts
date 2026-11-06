/**
 * «Блоки» as the original shows it (`UI-PARITY`): a page selector with counts, a grid of tiles, the
 * number of findings on a tile's page, and the block view.
 *
 * Two halves. The pure model (image zoom and pan, the page selection, the excerpt, the findings by
 * page) is asserted as functions, because this suite has no DOM and cannot fire a wheel or a key.
 * The markup is asserted through the real views, rendered once: a closed list, a list with a page
 * chosen, a list with the block view drawn open (`staticOpen`), and the widget over a seeded cache
 * for the run's findings. Where a property is about what the markup does NOT carry (a number on a
 * tile with no run), the positive half is asserted beside it.
 */

import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Finding, PortalBlock, RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { AR_V3_BETA_PROFILE_ID, runListQueryOptions } from '@/entities/audit-run';
import {
  MAX_ZOOM,
  MIN_ZOOM,
  WHEEL_IN,
  WHEEL_OUT,
  WHOLE_IMAGE,
  blocksOfSelection,
  clampView,
  effectiveSelection,
  isZoomed,
  pageChips,
  pageSelectionOf,
  pageSelectionParam,
  panBy,
  portalBlocksQueryOptions,
  sectionsByPage,
  stepIndex,
  textExcerpt,
  viewTransform,
  wheelZoom,
  zoomAround,
  zoomLabel,
} from '@/entities/block';
import type { View } from '@/entities/block';
import {
  PortalBlockListView,
  PortalBlocks,
  completeFindingsOf,
  findingsByPage,
  latestPublishedRunId,
  pageReading,
  runSourcePhrase,
  scopeRunId,
  severityTone,
  worstDecided,
} from '@/widgets/portal-blocks';
import type { PageFindingsReading } from '@/widgets/portal-blocks';

import { runStatus } from '../review/fixtures';
import { newClient, renderScreen } from '../screens/harness';
import {
  BLOCKS_PROJECT_UID,
  BLOCKS_RUN_ID,
  BLOCKS_VERSION_UID,
  TEST_CROP_SRC,
  blockId,
  blocksOnFivePages,
  blocksVersion,
  everyKindOfBlock,
  portalPage,
  runFindings,
  textBlock,
} from './fixtures';

beforeEach(() => {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
});
afterEach(() => {
  vi.unstubAllEnvs();
});

// ======================================================================= the image's zoom and pan

const STAGE = { width: 800, height: 600 };

describe('the block image zooms from the whole image to twelve times, around the pointer', () => {
  it('states the original’s limits and notches', () => {
    expect(MIN_ZOOM).toBe(1);
    expect(MAX_ZOOM).toBe(12);
    expect(WHEEL_IN).toBe(1.15);
    expect(WHEEL_OUT).toBe(0.87);
  });

  it('keeps the point under the pointer under the pointer', () => {
    const anchor = { x: 600, y: 150 };
    const zoomed = zoomAround(WHOLE_IMAGE, 3, anchor, STAGE);
    // The image point that lay under the anchor before is the one under it after.
    expect((anchor.x - zoomed.x) / zoomed.zoom).toBeCloseTo(anchor.x, 6);
    expect((anchor.y - zoomed.y) / zoomed.zoom).toBeCloseTo(anchor.y, 6);
  });

  it('zooms in by 1.15 and out by 0.87 per notch, away from the reader meaning in', () => {
    const anchor = { x: 400, y: 300 };
    const once = wheelZoom(WHOLE_IMAGE, -100, anchor, STAGE);
    expect(once.zoom).toBeCloseTo(1.15, 9);
    const back = wheelZoom({ ...once, zoom: 2 }, 100, anchor, STAGE);
    expect(back.zoom).toBeCloseTo(2 * 0.87, 9);
    // A wheel that does not move changes nothing.
    expect(wheelZoom(once, 0, anchor, STAGE)).toBe(once);
  });

  it('never goes below the whole image or past twelve times', () => {
    const anchor = { x: 10, y: 10 };
    expect(wheelZoom(WHOLE_IMAGE, 100, anchor, STAGE)).toEqual(WHOLE_IMAGE);
    let view: View = WHOLE_IMAGE;
    for (let i = 0; i < 80; i += 1) view = wheelZoom(view, -100, anchor, STAGE);
    expect(view.zoom).toBe(12);
    expect(clampView({ zoom: Number.NaN, x: 0, y: 0 }, STAGE).zoom).toBe(1);
    expect(clampView({ zoom: 99, x: 0, y: 0 }, STAGE).zoom).toBe(12);
  });

  it('cannot be dragged out of reach, and a whole image does not move at all', () => {
    expect(panBy(WHOLE_IMAGE, 300, -200, STAGE)).toEqual(WHOLE_IMAGE);
    const zoomed: View = { zoom: 2, x: -100, y: -100 };
    // Dragging right and down as far as the hand goes stops at the image's top-left corner...
    expect(panBy(zoomed, 9999, 9999, STAGE)).toEqual({ zoom: 2, x: 0, y: 0 });
    // ...and left and up at its bottom-right corner: the stage shows the image's last 1/zoom.
    expect(panBy(zoomed, -9999, -9999, STAGE)).toEqual({ zoom: 2, x: -800, y: -600 });
    expect(isZoomed(zoomed)).toBe(true);
    expect(isZoomed(WHOLE_IMAGE)).toBe(false);
  });

  it('holds a zoomed view inside a stage that shrank, and leaves a stage with no size whole', () => {
    expect(clampView({ zoom: 4, x: -2000, y: -1500 }, { width: 400, height: 300 })).toEqual({ zoom: 4, x: -1200, y: -900 });
    expect(clampView({ zoom: 4, x: -50, y: -50 }, { width: 0, height: 0 })).toEqual(WHOLE_IMAGE);
  });

  it('draws a view as a CSS transform and names the zoom with a decimal comma', () => {
    expect(viewTransform({ zoom: 2.5, x: -10, y: -20 })).toBe('translate(-10px, -20px) scale(2.5)');
    expect(zoomLabel({ zoom: 2.5, x: 0, y: 0 })).toBe('×2,5');
    expect(zoomLabel(WHOLE_IMAGE)).toBe('×1,0');
  });
});

// ================================================================ the page selection and the walk

describe('the page selection and the walk through it', () => {
  const blocks = everyKindOfBlock(); // pages: 1,1,1 | 2,2 | 3,3
  const sections = sectionsByPage(blocks);

  it('counts the loaded blocks per page, in the order the sections are shown', () => {
    expect(pageChips(sections).map((chip) => [chip.pageNumber, chip.count, chip.differingLabel])).toEqual([
      [1, 3, null],
      [2, 2, 5],
      [3, 2, null],
    ]);
  });

  it('walks every block for «Все блоки» and one page’s blocks for a page', () => {
    expect(blocksOfSelection(sections, 'all')).toEqual(blocks);
    expect(blocksOfSelection(sections, 2).map((block) => block.portal_block_id)).toEqual([blockId(4), blockId(5)]);
  });

  it('takes a page that is not loaded for the whole list rather than for an empty one', () => {
    expect(effectiveSelection(sections, 9)).toBe('all');
    expect(blocksOfSelection(sections, 9)).toEqual(blocks);
    expect(effectiveSelection(sections, 3)).toBe(3);
  });

  it('reads the address’s ?page=N and ?page=all, and takes anything else for «Все блоки»', () => {
    expect(pageSelectionOf('3')).toBe(3);
    expect(pageSelectionOf('12')).toBe(12);
    expect(pageSelectionOf('all')).toBe('all');
    for (const other of [null, undefined, '', '0', '-2', '2.5', '1e3', ' 2', '2 ', 'три', 'ALL', '99999999']) {
      expect(pageSelectionOf(other), String(other)).toBe('all');
    }
  });

  it('writes a selection as the value the address reads back', () => {
    for (const selection of ['all', 1, 3, 40] as const) {
      expect(pageSelectionOf(pageSelectionParam(selection))).toBe(selection);
    }
    expect(pageSelectionParam('all')).toBe('all');
    expect(pageSelectionParam(7)).toBe('7');
  });

  it('stops at either end and does not wrap', () => {
    expect(stepIndex(0, 7, -1)).toBeNull();
    expect(stepIndex(0, 7, 1)).toBe(1);
    expect(stepIndex(6, 7, 1)).toBeNull();
    expect(stepIndex(6, 7, -1)).toBe(5);
    expect(stepIndex(0, 1, 1)).toBeNull();
    expect(stepIndex(0, 1, -1)).toBeNull();
  });
});

describe('a tile’s excerpt of the recognised text', () => {
  it('leaves a short text as it is, flattened to one line', () => {
    expect(textExcerpt('Пояснительная\nзаписка.\n\n  Раздел 1.')).toBe('Пояснительная записка. Раздел 1.');
  });

  it('cuts a long text at a word and says so with «…», never past the limit', () => {
    const long = Array.from({ length: 60 }, (_, i) => `слово${i}`).join(' ');
    const excerpt = textExcerpt(long, 40);
    expect(excerpt.endsWith('…')).toBe(true);
    expect(Array.from(excerpt).length).toBeLessThanOrEqual(41);
    expect(long.startsWith(excerpt.slice(0, -1))).toBe(true);
    expect(excerpt.slice(0, -1)).not.toMatch(/\s$/);
  });

  it('counts code points, not UTF-16 units, and cuts one long token where it stands', () => {
    const astral = '𝔸'.repeat(50);
    expect(Array.from(textExcerpt(astral, 10))).toHaveLength(11);
    expect(textExcerpt(astral, 10)).toBe(`${'𝔸'.repeat(10)}…`);
  });
});

// =========================================================== the run's findings, by page and severity

describe('the findings a tile counts are those that cite its PAGE', () => {
  const byPage = findingsByPage(runFindings());

  it('counts a finding once per page it cites, however many quotations it has there', () => {
    expect(byPage.get(1)?.count).toBe(2); // A (two quotations) and B
    expect(byPage.get(2)?.count).toBe(2); // B and C
    expect(byPage.get(3)?.count).toBe(1);
    expect(byPage.get(4)?.count).toBe(1);
    expect(byPage.get(5)).toBeUndefined();
  });

  it('colours by the worst DECIDED severity and never by the model’s proposal', () => {
    expect(byPage.get(1)?.worst).toBe('critical');
    // Page 2's finding C carries a model proposal of «critical»; the expert decided only B (economic).
    expect(byPage.get(2)?.worst).toBe('economic');
    expect(byPage.get(3)?.worst).toBe('operational');
    expect(byPage.get(4)?.worst).toBeNull();
    expect(worstDecided([])).toBeNull();
  });

  it('maps the severities to the badge tones the severity badge uses, and a missing one to neutral', () => {
    expect(
      (['critical', 'economic', 'operational', 'recommendation', 'check_adjacent'] as const).map(severityTone),
    ).toEqual(['failed', 'degraded', 'active', 'inert', 'inert']);
    expect(severityTone(null)).toBe('inert');
  });

  it('says nothing about a page unless the findings were read, and zero only when they were', () => {
    const none: PageFindingsReading = { kind: 'none' };
    expect(pageReading(none, 1)).toBeNull();
    expect(pageReading({ kind: 'no-result', runId: BLOCKS_RUN_ID }, 1)).toBeNull();
    expect(pageReading({ kind: 'unreadable', runId: BLOCKS_RUN_ID }, 1)).toBeNull();
    const read: PageFindingsReading = { kind: 'read', runId: BLOCKS_RUN_ID, byPage };
    expect(pageReading(read, 1)?.count).toBe(2);
    expect(pageReading(read, 5)).toEqual({ count: 0, worst: null, findings: [] });
  });

  it('takes the version’s latest run that published a result, in the order the list came', () => {
    const newest = runStatus({ run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q9A', state: 'failed' });
    const published = runStatus({ run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q9B', state: 'published' });
    const older = runStatus({ run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q9C', state: 'published' });
    expect(latestPublishedRunId([newest, published, older])).toBe(published.run_id);
    expect(latestPublishedRunId([older, published])).toBe(older.run_id);
    expect(latestPublishedRunId([newest])).toBeNull();
    expect(latestPublishedRunId([])).toBeNull();
    // A run of the AR v3 beta profile publishes no canonical findings, so it is not the run in scope.
    const beta = runStatus({ run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q9D', state: 'published', analysis_profile_id: AR_V3_BETA_PROFILE_ID });
    expect(latestPublishedRunId([beta, published])).toBe(published.run_id);
  });

  it('prefers that run to the one that read the bundle, and falls back to the latter only when none published', () => {
    const published = runStatus({ run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q9B', state: 'published' });
    const failed = runStatus({ run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q9A', state: 'failed' });
    expect(scopeRunId([failed, published], BLOCKS_RUN_ID)).toBe(published.run_id);
    expect(scopeRunId([failed], BLOCKS_RUN_ID)).toBe(BLOCKS_RUN_ID);
    expect(scopeRunId([], BLOCKS_RUN_ID)).toBe(BLOCKS_RUN_ID);
    expect(scopeRunId([failed], null)).toBeNull();
    // A list that failed does not hide the numbers; the tiles still name the run they are from.
    expect(scopeRunId('unreadable', BLOCKS_RUN_ID)).toBe(BLOCKS_RUN_ID);
    // A list still on its way guesses no run, so the wrong run's findings are not fetched and replaced.
    expect(scopeRunId('pending', BLOCKS_RUN_ID)).toBeNull();
  });

  it('says which run a count is from in the words «по прогону от <time>», or nothing when the start is unknown', () => {
    expect(runSourcePhrase(RUN_AT)).toBe('по прогону от 2026-09-10 08:00:00 UTC');
    expect(runSourcePhrase(undefined)).toBeNull();
  });

  it('reads the findings only from the envelope the key holds, and never turns another shape into an empty list', () => {
    const items = runFindings();
    expect(completeFindingsOf({ data: { items, page: { next_cursor: null } } })).toBe(items);
    // The raw page, nothing, a non-list: not the envelope. An empty list would read as «nothing found».
    for (const other of [{ items, page: {} }, undefined, null, 'x', { data: null }, { data: { items: 'x' } }]) {
      expect(completeFindingsOf(other)).toBeNull();
    }
  });

  it('refuses to count a payload that is not a finding', () => {
    const [first] = runFindings() as [Finding];
    const diagnostic = { ...first, finding_uid: '' } as Finding;
    expect(findingsByPage([diagnostic]).size).toBe(0);
  });
});

// ============================================================================== the markup

const RUN_AT = '2026-09-10T08:00:00.000Z';
const READ: PageFindingsReading = { kind: 'read', runId: BLOCKS_RUN_ID, byPage: findingsByPage(runFindings()), runAt: RUN_AT };

function list(
  blocks: readonly PortalBlock[],
  over: Partial<Parameters<typeof PortalBlockListView>[0]> = {},
): string {
  return renderScreen(
    newClient(),
    createElement(PortalBlockListView, {
      projectUid: BLOCKS_PROJECT_UID,
      blockCount: blocks.length,
      producedByRunId: BLOCKS_RUN_ID,
      blocks,
      versionUid: BLOCKS_VERSION_UID,
      hasMore: false,
      loadingMore: false,
      moreFailure: null,
      onMore: () => {},
      ...over,
    }),
  );
}

function count(markup: string, needle: string | RegExp): number {
  return typeof needle === 'string'
    ? markup.split(needle).length - 1
    : (markup.match(new RegExp(needle.source, needle.flags.includes('g') ? needle.flags : `${needle.flags}g`)) ?? []).length;
}

/** The text nodes of a fragment, decoded; identifiers in `<code>` left out. */
function visibleText(markup: string): string {
  return markup
    .replace(/<code>[\s\S]*?<\/code>/g, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();
}

/** The `<button …>` opening tags carrying `attribute`, in document order. */
function buttons(markup: string, attribute: string): string[] {
  return markup.match(new RegExp(`<button\\b[^>]*\\s${attribute}=[^>]*>`, 'g')) ?? [];
}

describe('the page selector', () => {
  it('offers «Все блоки (N)» and one chip per page with its count, the first pressed', () => {
    const markup = list(everyKindOfBlock());
    expect(visibleText(markup)).toContain('Все блоки (7) Стр. 1 (3) Стр. 2 (2) Стр. 3 (2)');
    const chips = buttons(markup, 'data-page-chip');
    expect(chips).toHaveLength(4);
    expect(chips[0]).toContain('data-page-chip="all"');
    expect(chips[0]).toContain('aria-pressed="true"');
    for (const chip of chips.slice(1)) expect(chip).toContain('aria-pressed="false"');
  });

  it('shows one page’s tiles when that page is chosen, and presses its chip', () => {
    const markup = list(everyKindOfBlock(), { initialPage: 2 });
    expect(count(markup, 'data-portal-page=')).toBe(1);
    expect(markup).toContain('data-portal-page="2"');
    expect(count(markup, 'data-portal-block-type=')).toBe(2);
    expect(buttons(markup, 'data-page-chip').find((chip) => chip.includes('data-page-chip="2"'))).toContain('aria-pressed="true"');
    expect(buttons(markup, 'data-page-chip')[0]).toContain('aria-pressed="false"');
  });

  it('takes a page that is not loaded for «Все блоки»', () => {
    const markup = list(everyKindOfBlock(), { initialPage: 9 });
    expect(count(markup, 'data-portal-page=')).toBe(3);
  });

  it('opens on the page the address names when the widget is given it (?page=N), and on «Все блоки» otherwise', () => {
    const client = newClient();
    client.setQueryData(portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey, {
      pages: [portalPage(everyKindOfBlock())],
      pageParams: [undefined],
    });
    const open = (page?: Parameters<typeof PortalBlocks>[0]['page']) =>
      renderScreen(client, createElement(PortalBlocks, { version: blocksVersion(true), ...(page === undefined ? {} : { page }) }));
    const third = open(pageSelectionOf('3'));
    expect(count(third, 'data-portal-page=')).toBe(1);
    expect(buttons(third, 'data-page-chip').find((chip) => chip.includes('data-page-chip="3"'))).toContain('aria-pressed="true"');
    expect(count(open(pageSelectionOf('all')), 'data-portal-page=')).toBe(3);
    expect(count(open(), 'data-portal-page=')).toBe(3);
  });

  it('says the count is of what has arrived while another page of blocks is waiting', () => {
    const partial = list(everyKindOfBlock(), { blockCount: 129, hasMore: true });
    expect(buttons(partial, 'data-page-chip')[0]).toContain('title="Загружены не все блоки комплекта: число — по загруженным."');
    expect(buttons(list(everyKindOfBlock()), 'data-page-chip')[0]).not.toContain('title=');
  });

  it('names the portal’s own label of a page that differs, in the chip’s title', () => {
    const chips = buttons(list(everyKindOfBlock()), 'data-page-chip');
    expect(chips.find((chip) => chip.includes('data-page-chip="2"'))).toContain('title="У портала страница названа 5."');
    expect(chips.find((chip) => chip.includes('data-page-chip="1"'))).not.toContain('title=');
  });
});

describe('the tiles', () => {
  const blocks = everyKindOfBlock();
  // Rendered per test, after the top-level `beforeEach` has set the API base the crop address needs.
  let markup = '';
  beforeEach(() => {
    markup = list(blocks);
  });

  it('is one button tile per block, in the order of the pages, each opening a dialog', () => {
    const tiles = buttons(markup, 'data-portal-block-type');
    expect(tiles).toHaveLength(blocks.length);
    expect(tiles.map((tile) => /data-portal-block-type="([a-z]+)"/.exec(tile)?.[1])).toEqual(
      blocks.map((block) => block.block_type),
    );
    for (const tile of tiles) expect(tile).toContain('aria-haspopup="dialog"');
  });

  it('shows an image block’s crop from the seam’s address, at a fixed height, lazily', () => {
    const image = blocks.find((block) => block.crop !== undefined) as PortalBlock;
    const img = /<img\b[^>]*>/.exec(markup)?.[0] ?? '';
    expect(img).toContain(`src="${TEST_CROP_SRC(image)}"`);
    expect(img).toContain('loading="lazy"');
    expect(img).toContain('data-portal-crop="shown"');
    expect(count(markup, /<img\b/)).toBe(blocks.filter((block) => block.crop !== undefined).length);
  });

  it('shows the beginning of a text block, marked «распознано», and never the whole text', () => {
    const long = textBlock({
      portal_block_id: blockId(20),
      recognised_text: { quote_source: 'recognised', text: `Начало текста. ${'Продолжение. '.repeat(60)}Конец.`, flags: [] },
    });
    const tile = list([long]);
    expect(tile).toContain('>распознано<');
    expect(tile).toContain('data-quote-source="recognised"');
    expect(tile).toContain('Начало текста.');
    expect(tile).toContain('…');
    expect(tile).not.toContain('Конец.');
    expect(tile).not.toContain('<pre');
  });

  it('says in words what a block without a picture or a text has instead', () => {
    const text = visibleText(markup);
    expect(text).toContain('Фрагмент не вырезан: страница портала не совпала со страницей PDF.');
    expect(text).toContain('Текст не распознан.');
    expect(text).toContain('У штампа нет ни изображения, ни текста.');
    expect(markup).toContain('data-portal-crop="absent"');
    expect(markup).toContain('data-recognised-absent');
  });

  it('names the type and the place under the picture, and the portal’s status only when it is not the usual', () => {
    const text = visibleText(markup);
    expect(text).toContain('Изображение стр. 1 · порядок 2');
    expect(text).toContain('Штамп стр. 1');
    expect(count(markup, 'am-badge--failed')).toBe(1); // the one block the portal marked as failed
    expect(text).toContain('сбой распознавания портала');
    expect(text).toContain('состояние у портала неизвестно этому экрану');
    expect(text).not.toContain('распознан порталом');
  });

  it('keeps the machine values on data attributes and prints none of them', () => {
    expect(markup).toContain('data-portal-status="failed"');
    expect(markup).toContain('data-portal-geometry="geometry_mismatch"');
    const latin = (visibleText(markup).match(/[A-Za-z_]{2,}/g) ?? []).filter((word) => word !== 'PDF');
    expect(latin).toEqual([]);
  });
});

describe('the number on a tile is the run’s findings on its page, and only when they were read', () => {
  const blocks = blocksOnFivePages();

  it('carries no number, no outline and no note when no run is in scope', () => {
    const markup = list(blocks);
    expect(markup).not.toContain('data-tile-badge');
    expect(count(markup, 'data-has-findings="true"')).toBe(0);
    expect(markup).not.toContain('data-page-findings=');
  });

  it('numbers every tile of a page with that page’s count, in the tone of its worst decided severity', () => {
    const markup = list(blocks, { pageFindings: READ });
    const badge = (page: number) =>
      [...markup.matchAll(/<button\b[^>]*data-portal-block-type[^>]*>[\s\S]*?<\/button>/g)]
        .map((m) => m[0])
        .filter((tile) => tile.includes(`стр. ${page}`));
    // Page 1: three tiles, each 2, failed (critical).
    expect(badge(1)).toHaveLength(3);
    for (const tile of badge(1)) {
      expect(tile).toContain('data-tile-badge="2"');
      expect(tile).toContain('am-badge--failed');
      expect(tile).toContain('title="Замечаний на странице 1: 2 (по прогону от 2026-09-10 08:00:00 UTC)"');
      expect(tile).toContain('data-has-findings="true"');
    }
    for (const tile of badge(2)) expect(tile).toContain('am-badge--degraded');
    for (const tile of badge(3)) expect(tile).toContain('am-badge--active');
    for (const tile of badge(4)) {
      expect(tile).toContain('data-tile-badge="1"');
      expect(tile).toContain('am-badge--inert');
    }
    // Page 5 was read and has none: no badge, no outline. Zero is not drawn as a number.
    for (const tile of badge(5)) {
      expect(tile).not.toContain('data-tile-badge');
      expect(tile).toContain('data-has-findings="false"');
    }
  });

  it('says that the number is of the PAGE, and names the run, when the findings were read', () => {
    const markup = list(blocks, { pageFindings: READ });
    expect(markup).toContain('data-page-findings="read"');
    expect(visibleText(markup)).toContain('Замечание указывает страницу, а не блок');
    expect(markup).toContain(`<code>${BLOCKS_RUN_ID}</code>`);
    // And when that run started: the note and every badge's title say «по прогону от <time>».
    expect(visibleText(markup)).toContain('(по прогону от 2026-09-10 08:00:00 UTC)');
    expect(markup).toContain(`data-page-findings-run-at="${RUN_AT}"`);
  });

  it('folds the reading notes under «Как читать плитки» and opens with the summary, the selector and the tiles', () => {
    const markup = list(blocks, { pageFindings: READ });
    const howTo = markup.indexOf('data-portal-how-to');
    expect(howTo).toBeGreaterThan(-1);
    // `UI-A-81` (density): the notes sit in a closed `<details>`, after the summary and before the selector, and the
    // selector and the tiles are not inside it.
    expect(markup.indexOf('data-portal-block-count')).toBeLessThan(howTo);
    const closing = markup.indexOf('</details>', howTo);
    expect(markup.slice(howTo, closing)).toContain('Замечание указывает страницу, а не блок');
    expect(markup.slice(howTo, closing)).not.toContain('data-page-selector');
    expect(markup.indexOf('data-page-selector')).toBeGreaterThan(closing);
    expect(markup.slice(howTo - 40, howTo)).not.toContain('open');
  });

  it('draws the title without the run’s time when the reading does not carry it', () => {
    const markup = list(blocks, { pageFindings: { ...READ, runAt: undefined } as PageFindingsReading });
    expect(markup).toContain('title="Замечаний на странице 1: 2"');
    expect(markup).not.toContain('по прогону от');
  });

  it('draws no number, and says why, for a run with no findings or findings that could not be read', () => {
    for (const [kind, sentence] of [
      ['no-result', 'не опубликовал замечаний, поэтому чисел замечаний на плитках нет.'],
      ['unreadable', 'не удалось прочитать, поэтому чисел замечаний на плитках нет.'],
    ] as const) {
      const markup = list(blocks, { pageFindings: { kind, runId: BLOCKS_RUN_ID } });
      expect(markup).not.toContain('data-tile-badge');
      expect(markup).toContain(`data-page-findings="${kind}"`);
      expect(visibleText(markup)).toContain(sentence);
    }
  });
});

describe('the block view', () => {
  const blocks = blocksOnFivePages();
  const open = (at: number, over: Partial<Parameters<typeof PortalBlockListView>[0]> = {}) =>
    list(blocks, { initialOpen: at, staticOpen: true, pageFindings: READ, ...over });

  it('is closed until a tile is pressed', () => {
    expect(list(blocks)).not.toContain('<dialog');
    expect(open(0)).toContain('<dialog');
  });

  it('is a modal dialog drawn open here, with the ‹ i / n › bar and a close button', () => {
    const markup = open(0);
    const dialog = /<dialog\b[^>]*>/.exec(markup)?.[0] ?? '';
    expect(dialog).toContain('data-block-viewer');
    expect(dialog).toContain('aria-label="Блок страницы документа"');
    expect(dialog).toMatch(/\sopen(=|\s|>)/);
    expect(markup).toContain('data-viewer-position="1"');
    expect(visibleText(markup)).toContain('1 / 9');
    expect(markup).toContain('aria-label="Предыдущий блок"');
    expect(markup).toContain('aria-label="Следующий блок"');
    expect(markup).toContain('aria-label="Закрыть"');
  });

  it('disables ‹ at the first block and › at the last, and does not wrap', () => {
    const first = open(0);
    expect(/<button\b[^>]*aria-label="Предыдущий блок"[^>]*>/.exec(first)?.[0]).toContain('disabled');
    expect(/<button\b[^>]*aria-label="Следующий блок"[^>]*>/.exec(first)?.[0]).not.toContain('disabled');
    const last = open(8);
    expect(visibleText(last)).toContain('9 / 9');
    expect(/<button\b[^>]*aria-label="Следующий блок"[^>]*>/.exec(last)?.[0]).toContain('disabled');
    expect(/<button\b[^>]*aria-label="Предыдущий блок"[^>]*>/.exec(last)?.[0]).not.toContain('disabled');
  });

  it('counts «i / n» within the page chosen above the tiles', () => {
    const markup = open(1, { initialPage: 2 });
    expect(visibleText(markup)).toContain('2 / 2');
    expect(markup).toContain('data-viewer-position="2"');
    // The block opened is the second block of page 2, and the bar says which page it is on.
    expect(visibleText(markup)).toContain('Текст · стр. 2');
  });

  it('shows an image block’s crop in a zoomable stage with the gestures in words', () => {
    const markup = open(1); // the second block of page 1 is the image
    expect(markup).toContain('data-block-image="shown"');
    expect(markup).toContain('data-zoomed="false"');
    expect(markup).toContain('data-zoom="1"');
    expect(markup).toContain(`src="${TEST_CROP_SRC(blocks[1] as PortalBlock)}"`);
    expect(visibleText(markup)).toContain('Колесо мыши — масштаб, перетаскивание — сдвиг, двойной щелчок — сброс.');
    expect(visibleText(markup)).toContain('Изображение · стр. 1.');
    expect(visibleText(markup)).toContain('Открыть фрагмент целиком');
    expect(markup).toContain('data-block-picture="present"');
  });

  it('shows the crop once in the view, not again in the card beside it', () => {
    const view = /<dialog[\s\S]*<\/dialog>/.exec(open(1))?.[0] ?? '';
    expect(count(view, /<img\b/)).toBe(1);
    expect(view).not.toContain('data-portal-crop');
    // The pixel size is said once, under the stage, where the card would have said it.
    expect(count(view, 'Размер, пикс.: 1177 × 593.')).toBe(1);
  });

  it('puts the block’s card in the side panel: status, recognised text marked, flags, description', () => {
    const text = open(0);
    const panel = /<aside\b[\s\S]*?<\/aside>/.exec(text)?.[0] ?? '';
    expect(panel).toContain('data-block-panel');
    expect(panel).toContain('data-portal-block-type="text"');
    expect(panel).toContain('>распознано<');
    expect(panel).toMatch(/<pre[^>]*>Уровень пола/);
    expect(panel).toContain('data-recognised-flag="mixed_script"');
    const image = /<aside\b[\s\S]*?<\/aside>/.exec(open(1))?.[0] ?? '';
    expect(image).toContain('data-portal-description');
    expect(image).toContain('>описание портала — в анализе не используется<');
  });

  it('says a block with no picture has none, and where its content is', () => {
    const stamp = open(2);
    expect(stamp).toContain('data-block-picture="absent"');
    expect(visibleText(stamp)).toContain('У блока этого типа нет изображения: его содержимое — в панели справа.');
    // Page 3 opens on the mismatch image, which has no crop to draw.
    const mismatch = list(blocks, { initialOpen: 0, initialPage: 3, staticOpen: true });
    expect(visibleText(mismatch)).toContain('Изображения у этого блока нет: фрагмент не вырезан.');
  });

  it('lists the findings that cite the block’s page, honestly not the block’s, with a link to each in «Разбор»', () => {
    const markup = open(0); // a block of page 1
    const panel = /<section\b[^>]*data-page-findings-panel[\s\S]*?<\/section>/.exec(markup)?.[0] ?? '';
    expect(panel).toContain('data-page-findings-panel="2"');
    expect(visibleText(panel)).toContain('Замечания на странице 1 (2)');
    expect(visibleText(panel)).toContain('Замечание указывает страницу PDF, а не блок');
    expect(visibleText(panel)).toContain('(по прогону от 2026-09-10 08:00:00 UTC)');
    expect(visibleText(panel)).toContain('Не указан класс огнестойкости перекрытия.');
    expect(visibleText(panel)).toContain('Объём бетона в ведомости и на плане различается.');
    expect(count(panel, 'data-finding-uid=')).toBe(2);
    expect(panel).toContain(`href="/projects/${BLOCKS_PROJECT_UID}/runs/${BLOCKS_RUN_ID}/review?finding=fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8A"`);
    // The expert's severity is shown where there is one, as the severity badge says it.
    expect(panel).toContain('data-severity="critical"');
    expect(panel).toContain('data-severity="economic"');
  });

  it('does not show the model’s proposal as a severity', () => {
    const second = /<section\b[^>]*data-page-findings-panel[\s\S]*?<\/section>/.exec(open(3))?.[0] ?? ''; // page 2
    expect(second).toContain('data-page-findings-panel="2"');
    // Page 2's finding C is undecided and carries a proposal of «critical»: only B's economic severity is drawn.
    expect(count(second, 'data-severity=')).toBe(1);
    expect(second).toContain('data-severity="economic"');
  });

  it('says a page with no cited findings has none, when the findings were read', () => {
    const panel = /<section\b[^>]*data-page-findings-panel[\s\S]*?<\/section>/.exec(open(8))?.[0] ?? ''; // page 5
    expect(panel).toContain('data-page-findings-panel="0"');
    expect(visibleText(panel)).toContain('Ни в одном замечании прогона нет цитаты с этой страницы.');
    expect(panel).not.toContain('data-finding-uid');
  });

  it('shows no findings panel when no number may be said', () => {
    for (const reading of [{ kind: 'none' }, { kind: 'no-result', runId: BLOCKS_RUN_ID }, { kind: 'unreadable', runId: BLOCKS_RUN_ID }] as const) {
      expect(open(0, { pageFindings: reading })).not.toContain('data-page-findings-panel');
    }
  });

  it('opens nothing for a place that is not in the selection', () => {
    expect(list(blocks, { initialOpen: 99, staticOpen: true })).not.toContain('<dialog');
  });
});

describe('the widget reads the run in scope and numbers the tiles from its findings', () => {
  const run = BLOCKS_RUN_ID;

  function widget(client: ReturnType<typeof newClient>): string {
    return renderScreen(client, createElement(PortalBlocks, { version: blocksVersion(true) }));
  }

  /**
   * The cache the widget reads: the blocks, the version's first page of runs (by default one run, the one
   * that read the bundle, newest first; `runs: null` leaves the list unread, still on its way), and the
   * status and findings of `run`.
   */
  function seeded(
    options: { status?: RunStatus | 'error'; findings?: readonly Finding[]; runs?: readonly RunStatus[] | null } = {},
  ) {
    const client = newClient();
    client.setQueryData(portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey, {
      pages: [portalPage(blocksOnFivePages())],
      pageParams: [undefined],
    });
    if (options.runs !== null) {
      client.setQueryData(runListQueryOptions(BLOCKS_VERSION_UID).queryKey, {
        items: [...(options.runs ?? [runStatus({ run_id: run, version_uid: BLOCKS_VERSION_UID })])],
        page: { next_cursor: null },
      });
    }
    if (options.status !== undefined && options.status !== 'error') {
      client.setQueryData(queryKeys.runs.detail(run), options.status);
    }
    if (options.findings !== undefined) {
      client.setQueryData(queryKeys.runs.findings(run), { data: { items: [...options.findings], page: { next_cursor: null } } });
    }
    return client;
  }

  it('numbers the tiles of a published run whose findings are in the cache', () => {
    const markup = widget(seeded({ status: runStatus({ run_id: run }), findings: runFindings() }));
    expect(markup).toContain('data-page-findings="read"');
    expect(markup).toContain('data-tile-badge="2"');
    expect(markup).toContain('data-has-findings="true"');
  });

  it('shows no number while the run’s status has not arrived, and no sentence either', () => {
    const markup = widget(seeded());
    expect(markup).not.toContain('data-tile-badge');
    expect(markup).not.toContain('data-page-findings=');
    expect(markup).toContain('data-portal-block-type');
  });

  it('says the findings could not be read when the cache holds another shape than the key’s envelope', () => {
    const client = seeded({ status: runStatus({ run_id: run }) });
    client.setQueryData(queryKeys.runs.findings(run), { items: runFindings(), page: { next_cursor: null } });
    const markup = widget(client);
    expect(markup).not.toContain('data-tile-badge');
    expect(markup).toContain('data-page-findings="unreadable"');
  });

  it('does not take a run that published nothing for a run with no findings', () => {
    const markup = widget(seeded({ status: runStatus({ run_id: run, state: 'failed' }), findings: runFindings() }));
    expect(markup).not.toContain('data-tile-badge');
    expect(markup).toContain('data-page-findings="no-result"');
  });

  it('shows no number and no sentence when the geometry run is not named and no run of the version published', () => {
    const client = newClient();
    client.setQueryData(portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey, {
      pages: [portalPage(blocksOnFivePages(), { produced_by_run_id: null })],
      pageParams: [undefined],
    });
    client.setQueryData(runListQueryOptions(BLOCKS_VERSION_UID).queryKey, {
      items: [runStatus({ run_id: run, state: 'failed' })],
      page: { next_cursor: null },
    });
    const markup = widget(client);
    expect(markup).not.toContain('data-tile-badge');
    expect(markup).not.toContain('data-page-findings=');
  });

  it('numbers the tiles from the version’s latest published run, not from the run that read the bundle', () => {
    const latest = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q9B';
    const client = seeded({
      // Newest first: a failed run, then the latest published one, then the run that read the bundle.
      runs: [
        runStatus({ run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q9A', state: 'failed', created_at: '2026-09-12T08:00:00.000Z' }),
        runStatus({ run_id: latest, created_at: '2026-09-11T08:00:00.000Z' }),
        runStatus({ run_id: run, created_at: '2026-09-10T08:00:00.000Z' }),
      ],
      // The geometry run's own cache says «failed»: were it the run in scope, the sentence would be «no-result».
      status: runStatus({ run_id: run, state: 'failed' }),
    });
    client.setQueryData(queryKeys.runs.detail(latest as typeof run), runStatus({ run_id: latest, created_at: '2026-09-11T08:00:00.000Z' }));
    client.setQueryData(queryKeys.runs.findings(latest as typeof run), {
      data: { items: [...runFindings()], page: { next_cursor: null } },
    });
    const markup = widget(client);
    expect(markup).toContain('data-page-findings="read"');
    expect(markup).toContain(`<code>${latest}</code>`);
    expect(markup).toContain('data-tile-badge="2"');
    // The tile’s title and the note say which run, and when it started.
    expect(markup).toContain('title="Замечаний на странице 1: 2 (по прогону от 2026-09-11 08:00:00 UTC)"');
    expect(visibleText(markup)).toContain('(по прогону от 2026-09-11 08:00:00 UTC)');
    expect(markup).not.toContain('data-page-findings="no-result"');
  });

  it('falls back to the run that read the bundle when no run of the version published, and says what that run did', () => {
    const markup = widget(
      seeded({
        runs: [runStatus({ run_id: run, state: 'failed' })],
        status: runStatus({ run_id: run, state: 'failed' }),
      }),
    );
    expect(markup).toContain('data-page-findings="no-result"');
    expect(markup).toContain(`<code>${run}</code>`);
    expect(markup).not.toContain('data-tile-badge');
  });

  it('guesses no run while the version’s runs are still on their way', () => {
    const markup = widget(seeded({ runs: null, status: runStatus({ run_id: run }), findings: runFindings() }));
    expect(markup).not.toContain('data-tile-badge');
    expect(markup).not.toContain('data-page-findings=');
    expect(markup).toContain('data-portal-block-type');
  });
});
