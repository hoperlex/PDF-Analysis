/**
 * «Блоки страницы N» under the page on «Разбор» (`UI-A-74`): a strip of the portal blocks of the cited page,
 * inline and in the full-screen view's side column.
 *
 * A finding names pages, never a portal block, so the strip is headed by the page and says it holds all of
 * the page's blocks. It reads the version's blocks from the cache entry the «Блоки» tab fills (no request per
 * finding), draws nothing for a page with no blocks, and one quiet sentence for blocks it could not read.
 * The cases are aimed at these mutations (not run as mutations in this lane): the page filter dropped,
 * `complete` always true, the not-loaded branch folded into `none`, the walk widened to the version, a second
 * key for the read.
 */

import { createElement, isValidElement } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ErrorEnvelope, PortalBlock } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { portalBlocksQueryOptions } from '@/entities/block';
import {
  PageBlocksStrip,
  ReviewPage,
  ReviewPageBlocks,
  ReviewViewerAside,
  readPageBlocks,
  stripPageOf,
} from '@/_pages/review';
import type { PageBlocksShown, PageBlocksStripProps } from '@/_pages/review';

import { newClient, renderScreen, seedError } from '../screens/harness';
import {
  BLOCKS_PROJECT_UID,
  BLOCKS_VERSION_UID,
  TEST_CROP_SRC,
  blockId,
  imageBlock,
  notProducedPage,
  omit,
  portalPage,
  stampBlock,
  textBlock,
} from '../blocks/fixtures';
import {
  PROJECT_UID,
  RUN_ID,
  VERSION_UID,
  evidence,
  findingDetail,
  observation,
  runStatus,
} from './fixtures';

const KEY = portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey;

beforeEach(() => {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
});
afterEach(() => {
  vi.unstubAllEnvs();
});

// ----------------------------------------------------------------------------------------- the blocks

/** Two blocks on page 3 (an image with a crop, a stamp without one) and one text block on page 7. */
function blocksOfThePages(): PortalBlock[] {
  return [
    imageBlock({ portal_block_id: blockId(21), page_number: 3, page_label: 3, ordinal: 1 }),
    stampBlock({ portal_block_id: blockId(22), page_number: 3, page_label: 3 }),
    textBlock({ portal_block_id: blockId(23), page_number: 7, page_label: 7, ordinal: 1 }),
  ];
}

/** A cursor page of `block_count` blocks of which these are the loaded ones, with or without a next cursor. */
function loadedUpTo(blocks: readonly PortalBlock[], more: boolean) {
  return portalPage(blocks, { block_count: more ? 300 : blocks.length, page: { next_cursor: more ? 'c1' : null } });
}

// ----------------------------------------------------------------------------------- what the page has

describe('which blocks the strip may show for a cited page', () => {
  it('shows the blocks of the page, and only that page’s, in the API order', () => {
    const reading = readPageBlocks({ pages: [loadedUpTo(blocksOfThePages(), false)], hasMore: false }, 3);
    expect(reading.kind).toBe('blocks');
    if (reading.kind !== 'blocks') return;
    expect(reading.page).toBe(3);
    expect(reading.blocks.map((block) => block.portal_block_id)).toEqual([blockId(21), blockId(22)]);
    expect(reading.complete).toBe(true);
  });

  it('joins the two halves of a page the cursor cut', () => {
    const first = loadedUpTo([imageBlock({ portal_block_id: blockId(31), page_number: 5 })], true);
    const second = loadedUpTo([textBlock({ portal_block_id: blockId(32), page_number: 5 })], false);
    const reading = readPageBlocks({ pages: [first, second], hasMore: false }, 5);
    expect(reading.kind === 'blocks' && reading.blocks.map((block) => block.portal_block_id)).toEqual([
      blockId(31),
      blockId(32),
    ]);
  });

  it('says the last loaded page may continue, and a page before it may not', () => {
    const pages = [loadedUpTo(blocksOfThePages(), true)];
    const last = readPageBlocks({ pages, hasMore: true }, 7);
    const before = readPageBlocks({ pages, hasMore: true }, 3);
    expect(last.kind === 'blocks' && last.complete).toBe(false);
    expect(before.kind === 'blocks' && before.complete).toBe(true);
  });

  it('draws nothing for a page with no blocks, whether the list is complete or not', () => {
    // Page 5 lies between two loaded pages: a complete page holding none. Page 9 lies past the end of a list with no next cursor.
    expect(readPageBlocks({ pages: [loadedUpTo(blocksOfThePages(), true)], hasMore: true }, 5)).toEqual({ kind: 'none' });
    expect(readPageBlocks({ pages: [loadedUpTo(blocksOfThePages(), false)], hasMore: false }, 9)).toEqual({ kind: 'none' });
  });

  it('says a page past the loaded blocks is not loaded, rather than that it has none', () => {
    const reading = readPageBlocks({ pages: [loadedUpTo(blocksOfThePages(), true)], hasMore: true }, 9);
    expect(reading).toEqual({ kind: 'not-loaded', page: 9 });
  });

  it('treats a version no run has read as having no blocks, whatever the page carries', () => {
    expect(readPageBlocks({ pages: [notProducedPage()], hasMore: false }, 3)).toEqual({ kind: 'none' });
    // `status`, not the length of `items`, is the answer (the contract’s own instruction).
    const odd = { ...notProducedPage(), items: blocksOfThePages() };
    expect(readPageBlocks({ pages: [odd], hasMore: false }, 3)).toEqual({ kind: 'none' });
  });

  it('says a read that failed is unreadable', () => {
    expect(readPageBlocks({ pages: undefined, hasMore: false }, 3)).toEqual({ kind: 'unreadable', page: 3 });
  });

  it('follows the page the viewer is on while it is a cited one, and the first cited page otherwise', () => {
    expect(stripPageOf([3, 7], 7)).toBe(7);
    expect(stripPageOf([3, 7], 5)).toBe(3);
    expect(stripPageOf([3, 7], null)).toBe(3);
    expect(stripPageOf([], 3)).toBeNull();
  });
});

// ------------------------------------------------------------------------------------- the view itself

function shown(over: Partial<Extract<PageBlocksShown, { kind: 'blocks' }>> = {}): PageBlocksShown {
  return { kind: 'blocks', page: 3, blocks: blocksOfThePages().slice(0, 2), complete: true, ...over };
}

function stripProps(over: Partial<PageBlocksStripProps> = {}): PageBlocksStripProps {
  return {
    reading: shown(),
    versionUid: BLOCKS_VERSION_UID,
    onOpen: () => {},
    onMore: () => {},
    loadingMore: false,
    moreFailed: false,
    ...over,
  };
}

function find(
  node: ReactNode,
  matches: (element: ReactElement<Record<string, unknown>>) => boolean,
  found: ReactElement<Record<string, unknown>>[] = [],
): ReactElement<Record<string, unknown>>[] {
  if (Array.isArray(node)) node.forEach((child) => find(child, matches, found));
  else if (isValidElement<Record<string, unknown>>(node)) {
    if (matches(node)) found.push(node);
    find(node.props.children as ReactNode, matches, found);
  }
  return found;
}

function html(props: PageBlocksStripProps): string {
  return renderScreen(newClient(), createElement(PageBlocksStrip, props));
}

describe('the strip as a view', () => {
  it('is headed by the page and its count, and says the blocks are the page’s, not the finding’s', () => {
    const markup = html(stripProps());
    expect(markup).toContain('data-page-blocks="blocks"');
    expect(markup).toContain('data-page-blocks-page="3"');
    expect(markup).toContain('Блоки страницы 3 (2)');
    expect(markup).toContain('Замечание указывает страницу PDF, а не блок портала, поэтому здесь все блоки этой страницы.');
  });

  it('leads to the version’s whole «Блоки» tab when it is given the address, as the original’s thumbnails lead to its blocks', () => {
    expect(html(stripProps())).not.toContain('data-page-blocks-all');
    const markup = html(stripProps({ blocksHref: '/projects/prj_x/versions/ver_x/blocks' }));
    expect(markup).toContain('data-page-blocks-all=""');
    expect(markup).toContain('href="/projects/prj_x/versions/ver_x/blocks"');
    expect(markup).toContain('Все блоки версии →');
  });

  it('draws one thumbnail per block, the crop from the seam’s address and a quiet note where there is none', () => {
    const blocks = blocksOfThePages().slice(0, 2);
    const markup = html(stripProps({ reading: shown({ blocks }) }));
    expect(markup.split('data-page-block-type=').length - 1).toBe(2);
    expect(markup).toContain(`src="${TEST_CROP_SRC(blocks[0] as PortalBlock)}"`);
    expect(markup).toContain('data-page-block-picture="shown"');
    expect(markup).toContain('data-page-block-picture="absent"');
    expect(markup).toContain('Без изображения');
    // The stamp has no crop: no address is built for it.
    expect(markup).not.toContain(TEST_CROP_SRC(blocks[1] as PortalBlock));
  });

  it('opens the block pressed, by its place among the page’s blocks', () => {
    const opened: number[] = [];
    const tree = PageBlocksStrip(stripProps({ onOpen: (index) => opened.push(index) }));
    const thumbs = find(tree, (element) => typeof element.props.onOpen === 'function');
    expect(thumbs).toHaveLength(2);
    (thumbs[1]?.props.onOpen as () => void)();
    (thumbs[0]?.props.onOpen as () => void)();
    expect(opened).toEqual([1, 0]);
  });

  it('draws no “more” footer for a complete page', () => {
    const markup = html(stripProps());
    expect(markup).not.toContain('data-page-blocks-more');
    expect(markup).not.toContain('Загрузить следующие блоки');
  });

  it('offers the next portion for a page that may continue, as a press and with its sentence', () => {
    const pressed: string[] = [];
    const props = stripProps({ reading: shown({ complete: false }), onMore: () => pressed.push('more') });
    const markup = html(props);
    expect(markup).toContain('Загружены не все блоки комплекта: страница может продолжаться в следующей порции.');
    expect(markup).toContain('data-page-blocks-more="idle"');
    const buttons = find(PageBlocksStrip(props), (element) => element.type === 'button' && element.props.onClick !== undefined);
    expect(buttons.map((button) => button.props.disabled)).toEqual([false]);
    (buttons[0]?.props.onClick as () => void)();
    expect(pressed).toEqual(['more']);
  });

  it('says a page beyond the loaded blocks is not loaded: no thumbnails, no “no blocks”', () => {
    const markup = html(stripProps({ reading: { kind: 'not-loaded', page: 9 } }));
    expect(markup).toContain('data-page-blocks="not-loaded"');
    expect(markup).toContain('Блоки страницы 9');
    expect(markup).toContain('Эта страница лежит за блоками, которые уже загружены: следующая порция ещё не прочитана.');
    expect(markup).toContain('Загрузить следующие блоки');
    expect(markup).not.toContain('data-page-block-type');
    expect(markup).not.toContain('Замечание указывает страницу PDF');
  });

  it('holds the press while a portion is on its way and says when one failed', () => {
    const loading = html(stripProps({ reading: { kind: 'not-loaded', page: 9 }, loadingMore: true }));
    expect(loading).toContain('data-page-blocks-more="loading"');
    expect(loading).toMatch(/<button[^>]*disabled[^>]*>Загружаю…<\/button>/);
    const failed = html(stripProps({ reading: shown({ complete: false }), moreFailed: true }));
    expect(failed).toContain('data-page-blocks-more="failed"');
    expect(failed).toContain('Следующую порцию не удалось загрузить.');
  });

  it('says unreadable blocks in one quiet sentence, with no strip and no press', () => {
    const markup = html(stripProps({ reading: { kind: 'unreadable', page: 3 } }));
    expect(markup).toContain('data-page-blocks="unreadable"');
    expect(markup).toContain('Блоки страницы 3 не удалось прочитать, поэтому полоска блоков не показана.');
    expect(markup).not.toContain('<section');
    expect(markup).not.toContain('<button');
    expect(markup).not.toContain('am-state--error');
  });
});

// ---------------------------------------------------------------------------- the strip over the cache

function connected(client: ReturnType<typeof newClient>, page: number, extra: { initialOpen?: number; staticOpen?: boolean } = {}): string {
  return renderScreen(
    client,
    createElement(ReviewPageBlocks, { projectUid: BLOCKS_PROJECT_UID, versionUid: BLOCKS_VERSION_UID, page, ...extra }),
  );
}

function seeded(...pages: ReturnType<typeof portalPage>[]) {
  const client = newClient();
  client.setQueryData(KEY, { pages, pageParams: pages.map((_, i) => (i === 0 ? undefined : `c${i}`)) });
  return client;
}

function apiError(): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.43.0', error_code: 'dependency_unavailable', message: 'm', correlation_id: 'cid-strip', retryable: true,
  };
  return new ApiError(503, envelope, 'cid-strip');
}

describe('the connected strip reads the «Блоки» tab’s own cache entry', () => {
  it('draws the page’s blocks from the version’s one read', () => {
    const markup = connected(seeded(loadedUpTo(blocksOfThePages(), false)), 3);
    expect(markup).toContain('Блоки страницы 3 (2)');
    expect(markup).not.toContain('Блоки страницы 7');
  });

  it('links the strip to the version’s «Блоки» tab, the project and the version in its path', () => {
    const markup = connected(seeded(loadedUpTo(blocksOfThePages(), false)), 3);
    expect(markup).toMatch(/href="\/projects\/prj_[0-9A-Z]+\/versions\/ver_[0-9A-Z]+\/blocks"[^>]*data-page-blocks-all|data-page-blocks-all[^>]*href="\/projects\/prj_[0-9A-Z]+\/versions\/ver_[0-9A-Z]+\/blocks"/);
  });

  it('draws nothing while that read is in flight', () => {
    expect(connected(newClient(), 3)).toBe('');
  });

  it('draws nothing for a version no run has read, and nothing for a page with no blocks', () => {
    expect(connected(seeded(notProducedPage()), 3)).toBe('');
    expect(connected(seeded(loadedUpTo(blocksOfThePages(), false)), 5)).toBe('');
  });

  it('says one quiet sentence when the read failed', () => {
    const client = newClient();
    seedError(client, KEY, apiError());
    const markup = connected(client, 3);
    expect(markup).toContain('Блоки страницы 3 не удалось прочитать, поэтому полоска блоков не показана.');
    expect(markup).not.toContain('data-page-block-type');
    expect(markup).not.toContain('cid-strip');
  });

  it('says a cited page past the loaded portion is not loaded', () => {
    const markup = connected(seeded(loadedUpTo(blocksOfThePages(), true)), 12);
    expect(markup).toContain('data-page-blocks="not-loaded"');
    expect(markup).toContain('Загрузить следующие блоки');
  });

  it('opens the block view over the page’s blocks only, with no findings list of its own', () => {
    // Three blocks are loaded, two on page 3: the walk is «2 / 2», never «2 / 3».
    const markup = connected(seeded(loadedUpTo(blocksOfThePages(), false)), 3, { initialOpen: 1, staticOpen: true });
    expect(markup).toContain('data-block-viewer');
    expect(markup).toContain('data-viewer-position="2"');
    expect(markup).toContain('2 / 2');
    expect(markup).not.toContain('2 / 3');
    expect(markup).not.toContain('data-page-findings-panel');
    expect(markup).not.toContain('Открыть в разборе');
  });

  it('keeps the block view closed until a thumbnail is pressed', () => {
    expect(connected(seeded(loadedUpTo(blocksOfThePages(), false)), 3)).not.toContain('data-block-viewer');
  });

  it('shows the strip in the full-screen view’s side column, after the finding and its actions', () => {
    const client = seeded(loadedUpTo(blocksOfThePages(), false));
    const markup = renderScreen(
      client,
      createElement(ReviewViewerAside, {
        findingUid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z',
        meta: 'Критическое · Лист 3 · стр. 3',
        text: 'Не указан класс огнестойкости перекрытия',
        recommendation: 'Указать предел огнестойкости REI 45 по СП 2.13130.',
        actions: createElement('span', { 'data-row-actions': '' }),
        blocks: createElement(ReviewPageBlocks, { projectUid: BLOCKS_PROJECT_UID, versionUid: BLOCKS_VERSION_UID, page: 3 }),
      }),
    );
    const at = (needle: string) => markup.indexOf(needle);
    expect(at('Указать предел огнестойкости')).toBeGreaterThan(-1);
    expect(at('data-row-actions')).toBeGreaterThan(at('Указать предел огнестойкости'));
    expect(at('data-page-blocks="blocks"')).toBeGreaterThan(at('data-row-actions'));
  });
});

// ------------------------------------------------------------------------------------ on the screen

function reviewMarkup(pages: readonly number[], seed: (client: ReturnType<typeof newClient>) => void): string {
  const detail = findingDetail({
    observation: observation({
      evidence: pages.map((page, at) => evidence({ evidence_ordinal: at + 1, page_number: page, quote: `Цитата со страницы ${page}.` })),
    }),
  });
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus());
  client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: [detail], page: { next_cursor: null } } });
  client.setQueryData(queryKeys.findings.detail(detail.finding_uid), { data: detail });
  client.setQueryData(queryKeys.findings.decisions(detail.finding_uid), { data: { items: [], page: { next_cursor: null } } });
  seed(client);
  return renderScreen(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
}

describe('«Разбор» shows the strip of the page the viewer opens on', () => {
  it('reads the version of the finding, under the page viewer, for the first cited page', () => {
    expect(VERSION_UID).toBe(BLOCKS_VERSION_UID);
    const markup = reviewMarkup([7, 3], (client) => {
      client.setQueryData(KEY, { pages: [loadedUpTo(blocksOfThePages(), false)], pageParams: [undefined] });
    });
    // The viewer opens on page 3 (the first cited page), and so does the strip.
    expect(markup).toContain('data-active-page="3"');
    expect(markup).toContain('Блоки страницы 3 (2)');
    expect(markup).not.toContain('Блоки страницы 7');
    expect(markup.indexOf('data-page-blocks="blocks"')).toBeGreaterThan(markup.indexOf('data-active-page="3"'));
    expect(markup).toContain(`src="${TEST_CROP_SRC(blocksOfThePages()[0] as PortalBlock)}"`);
  });

  it('draws no strip when the cited pages have no blocks, and says nothing about it', () => {
    const markup = reviewMarkup([4], (client) => {
      client.setQueryData(KEY, { pages: [loadedUpTo(blocksOfThePages(), false)], pageParams: [undefined] });
    });
    expect(markup).toContain('data-active-page="4"');
    expect(markup).not.toContain('data-page-blocks');
    expect(markup).not.toContain('Блоки страницы');
  });

  it('draws no strip while the version’s blocks have not been read', () => {
    const markup = reviewMarkup([3], () => {});
    expect(markup).toContain('data-active-page="3"');
    expect(markup).not.toContain('data-page-blocks');
  });

  it('says one quiet sentence, and keeps the page viewer, when the blocks cannot be read', () => {
    const markup = reviewMarkup([3], (client) => {
      seedError(client, KEY, apiError());
    });
    expect(markup).toContain('data-active-page="3"');
    expect(markup).toContain('Блоки страницы 3 не удалось прочитать, поэтому полоска блоков не показана.');
    expect(markup).not.toContain('cid-strip');
  });

  it('keeps the other strings the screen already asserted', () => {
    const markup = reviewMarkup([3], (client) => {
      client.setQueryData(KEY, { pages: [loadedUpTo(blocksOfThePages(), false)], pageParams: [undefined] });
    });
    expect(markup).not.toContain('data-evidence-expanded');
    expect(markup).toContain('data-finding-uid=');
    expect(markup).toContain('Цитаты на странице 3');
  });
});

// A block the server omits members of is still one thumbnail: the strip reads `crop`, nothing else.
describe('a block without the optional members', () => {
  it('is one thumbnail with no picture', () => {
    const bare = omit(imageBlock({ portal_block_id: blockId(41), page_number: 3 }), 'crop', 'portal_description');
    const markup = html(stripProps({ reading: shown({ blocks: [bare] }) }));
    expect(markup).toContain('Блоки страницы 3 (1)');
    expect(markup).toContain('data-page-block-picture="absent"');
  });
});
