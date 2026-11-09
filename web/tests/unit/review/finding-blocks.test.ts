/**
 * «Блоки замечания» under the page on «Разбор» (`UI-PARITY-C6`, the original's thumbnails under an opened finding): the portal
 * blocks that hold the finding's own evidence, each opening the block view over just those blocks.
 *
 * The server derives the relation (`listRunFindingBlocks`); the screen reads it with the version's blocks (the «Блоки» tab's own
 * cache entry) and draws the blocks of the finding. The cases are aimed at these mutations (not run as mutations in this lane):
 * the page's blocks drawn instead of the finding's, a block id with no block behind it drawn anyway, `complete` always true, a
 * strip drawn for a finding the server linked to nothing, a strip drawn while the links are not produced, the walk of the block
 * view widened to the version, the strip left out of the full-screen view.
 */

import { createElement, isValidElement } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { PortalBlock, RunFindingBlockLinks } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { portalBlocksQueryOptions } from '@/entities/block';
import {
  FindingBlocksStrip,
  ReviewFindingBlocks,
  ReviewPage,
  ReviewViewerAside,
  readFindingBlocks,
} from '@/_pages/review';
import type { FindingBlocksShown, FindingBlocksStripProps } from '@/_pages/review';

import { newClient, renderScreen } from '../screens/harness';
import {
  BLOCKS_PROJECT_UID,
  BLOCKS_VERSION_UID,
  TEST_CROP_SRC,
  blockId,
  imageBlock,
  notProducedPage,
  portalPage,
  stampBlock,
  textBlock,
} from '../blocks/fixtures';
import { FINDING_UID, PROJECT_UID, RUN_ID, VERSION_UID, evidence, findingDetail, observation, runStatus } from './fixtures';

const KEY = portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey;

beforeEach(() => {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
});
afterEach(() => {
  vi.unstubAllEnvs();
});

/** Page 1: an image (21), a stamp (22) and a text block (23); page 7: a text block (24). */
function blocksOfTheVersion(): PortalBlock[] {
  return [
    imageBlock({ portal_block_id: blockId(21), page_number: 1, page_label: 1, ordinal: 1 }),
    stampBlock({ portal_block_id: blockId(22), page_number: 1, page_label: 1 }),
    textBlock({
      portal_block_id: blockId(23), page_number: 1, page_label: 1, ordinal: 2,
      recognised_text: { quote_source: 'recognised', text: 'Предел огнестойкости перекрытия не указан.', flags: [] },
    }),
    textBlock({ portal_block_id: blockId(24), page_number: 7, page_label: 7, ordinal: 1 }),
  ];
}

function loadedUpTo(blocks: readonly PortalBlock[], more: boolean) {
  return portalPage(blocks, { block_count: more ? 300 : blocks.length, page: { next_cursor: more ? 'c1' : null } });
}

function links(ids: readonly string[], over: Partial<RunFindingBlockLinks> = {}): RunFindingBlockLinks {
  return {
    run_id: RUN_ID,
    version_uid: VERSION_UID,
    status: 'produced',
    unlinked_pages: [],
    items: [{ finding_uid: FINDING_UID, portal_block_ids: [...ids] }],
    ...over,
  };
}

// ------------------------------------------------------------------------------------ what is shown

describe('which blocks the finding’s strip may show', () => {
  const pages = [loadedUpTo(blocksOfTheVersion(), false)];

  it('shows the finding’s blocks, in the portal’s order and not the order of the ids', () => {
    const reading = readFindingBlocks({ pages, hasMore: false }, [blockId(24), blockId(21)]);
    expect(reading.kind === 'blocks' && reading.blocks.map((block) => block.portal_block_id)).toEqual([blockId(21), blockId(24)]);
    expect(reading.kind === 'blocks' && [reading.missing, reading.complete]).toEqual([0, true]);
  });

  it('never shows a block the finding does not hold, though it lies on the same page', () => {
    const reading = readFindingBlocks({ pages, hasMore: false }, [blockId(21)]);
    expect(reading.kind === 'blocks' && reading.blocks.map((block) => block.portal_block_id)).toEqual([blockId(21)]);
  });

  it('draws nothing for a finding with no linked block, however many blocks its page has', () => {
    expect(readFindingBlocks({ pages, hasMore: false }, [])).toEqual({ kind: 'none' });
  });

  it('draws nothing for a version no run has read, and for blocks that could not be read', () => {
    expect(readFindingBlocks({ pages: [notProducedPage()], hasMore: false }, [blockId(21)])).toEqual({ kind: 'none' });
    expect(readFindingBlocks({ pages: undefined, hasMore: false }, [blockId(21)])).toEqual({ kind: 'none' });
  });

  it('counts the linked blocks that are not loaded, and says the strip may still grow while another portion exists', () => {
    const partial = [loadedUpTo(blocksOfTheVersion().slice(0, 2), true)];
    const reading = readFindingBlocks({ pages: partial, hasMore: true }, [blockId(21), blockId(24)]);
    expect(reading.kind === 'blocks' && [reading.blocks.length, reading.missing, reading.complete]).toEqual([1, 1, false]);
  });

  it('says a block id the complete list does not hold is missing for good, not waiting', () => {
    const reading = readFindingBlocks({ pages, hasMore: false }, [blockId(21), blockId(99)]);
    expect(reading.kind === 'blocks' && [reading.blocks.length, reading.missing, reading.complete]).toEqual([1, 1, true]);
  });

  it('counts a block named twice once', () => {
    const reading = readFindingBlocks({ pages, hasMore: false }, [blockId(21), blockId(21)]);
    expect(reading.kind === 'blocks' && [reading.blocks.length, reading.missing]).toEqual([1, 0]);
  });
});

// ------------------------------------------------------------------------------------- the view itself

function shown(over: Partial<Extract<FindingBlocksShown, { kind: 'blocks' }>> = {}): FindingBlocksShown {
  return { kind: 'blocks', blocks: blocksOfTheVersion().slice(0, 3), missing: 0, complete: true, ...over };
}

function stripProps(over: Partial<FindingBlocksStripProps> = {}): FindingBlocksStripProps {
  return { reading: shown(), versionUid: BLOCKS_VERSION_UID, onOpen: () => {}, onMore: () => {}, loadingMore: false, moreFailed: false, ...over };
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

function html(props: FindingBlocksStripProps): string {
  return renderScreen(newClient(), createElement(FindingBlocksStrip, props));
}

describe('the strip as a view', () => {
  it('is headed «Блоки замечания» with the count, and says what a block of it is', () => {
    const markup = html(stripProps());
    expect(markup).toContain('data-finding-blocks="3"');
    expect(markup).toContain('Блоки замечания (3)');
    expect(markup).toContain('Блоки, в которых лежит цитата замечания: каждый покрывает не менее половины её места на странице.');
    // It is not the page strip: nothing here says «страницы N».
    expect(markup).not.toContain('Блоки страницы');
    expect(markup).not.toContain('data-page-blocks');
  });

  it('draws the crop of a picture block from the seam’s address', () => {
    const [image] = blocksOfTheVersion() as [PortalBlock];
    const markup = html(stripProps());
    expect(markup).toContain(`src="${TEST_CROP_SRC(image)}"`);
    expect(markup).toContain('data-page-block-picture="shown"');
  });

  it('draws a text block’s recognised text, marked as recognised, where it has no picture', () => {
    const markup = html(stripProps());
    expect(markup).toContain('распознано: Предел огнестойкости перекрытия не указан.');
  });

  it('cuts a long recognised text with «…», and leaves the stamp with the quiet note', () => {
    const long = textBlock({ portal_block_id: blockId(30), recognised_text: { quote_source: 'recognised', text: `Начало. ${'Продолжение. '.repeat(30)}`, flags: [] } });
    const markup = html(stripProps({ reading: shown({ blocks: [long, stampBlock({ portal_block_id: blockId(31) })] }) }));
    expect(markup).toContain('распознано: Начало.');
    expect(markup).toContain('…');
    expect(markup).toContain('Без изображения');
  });

  it('opens the block pressed, by its place among the finding’s blocks', () => {
    const opened: number[] = [];
    const tree = FindingBlocksStrip(stripProps({ onOpen: (at) => opened.push(at) }));
    const thumbs = find(tree, (element) => typeof element.props.onOpen === 'function');
    expect(thumbs).toHaveLength(3);
    (thumbs[2]?.props.onOpen as () => void)();
    (thumbs[0]?.props.onOpen as () => void)();
    expect(opened).toEqual([2, 0]);
  });

  it('draws no “more” footer when every linked block is shown', () => {
    const markup = html(stripProps());
    expect(markup).not.toContain('data-finding-blocks-more');
    expect(markup).not.toContain('Загрузить следующие блоки');
  });

  it('counts the blocks it could not show in the heading and offers the next portion as a press', () => {
    const markup = html(stripProps({ reading: shown({ blocks: blocksOfTheVersion().slice(0, 1), missing: 2, complete: false }) }));
    expect(markup).toContain('Блоки замечания (3)');
    expect(markup).toContain('data-finding-blocks-more="idle"');
    expect(markup).toContain('Ещё 2 из блоков замечания лежат на страницах, которые не загружены: блоки версии приходят порциями.');
    expect(markup).toContain('Загрузить следующие блоки');
  });

  it('holds the press while a portion is on its way and says when one failed', () => {
    const waiting = html(stripProps({ reading: shown({ missing: 1, complete: false }), loadingMore: true }));
    expect(waiting).toContain('data-finding-blocks-more="loading"');
    expect(waiting).toMatch(/<button[^>]*disabled[^>]*>Загружаю…<\/button>/);
    const failed = html(stripProps({ reading: shown({ missing: 1, complete: false }), moreFailed: true }));
    expect(failed).toContain('data-finding-blocks-more="failed"');
    expect(failed).toContain('Следующую порцию не удалось загрузить.');
  });

  it('says a block the complete list does not hold is not found, with no press', () => {
    const markup = html(stripProps({ reading: shown({ missing: 1, complete: true }) }));
    expect(markup).toContain('data-finding-blocks-more="absent"');
    expect(markup).toContain('Ещё 1 из блоков замечания в списке блоков версии не найдено.');
    expect(markup).not.toContain('Загрузить следующие блоки');
  });
});

// ---------------------------------------------------------------------------- the strip over the cache

function connected(client: ReturnType<typeof newClient>, extra: { initialOpen?: number; staticOpen?: boolean } = {}): string {
  return renderScreen(
    client,
    createElement(ReviewFindingBlocks, {
      projectUid: BLOCKS_PROJECT_UID,
      versionUid: BLOCKS_VERSION_UID,
      runId: RUN_ID,
      findingUid: FINDING_UID,
      ...extra,
    }),
  );
}

function seeded(answer: RunFindingBlockLinks | undefined, ...pages: ReturnType<typeof portalPage>[]) {
  const client = newClient();
  if (pages.length > 0) client.setQueryData(KEY, { pages, pageParams: pages.map((_, i) => (i === 0 ? undefined : `c${i}`)) });
  if (answer !== undefined) client.setQueryData(queryKeys.runs.findingBlocks(RUN_ID), answer);
  return client;
}

describe('the connected strip reads the run’s links and the version’s blocks from the cache', () => {
  const blocks = loadedUpTo(blocksOfTheVersion(), false);

  it('draws the blocks the server linked to the finding, and no other block of its page', () => {
    const markup = connected(seeded(links([blockId(23)]), blocks));
    expect(markup).toContain('Блоки замечания (1)');
    expect(markup.split('data-page-block-type=').length - 1).toBe(1);
    expect(markup).toContain('data-page-block-type="text"');
    expect(markup).not.toContain('data-page-block-type="image"');
  });

  it('draws nothing while the links are in flight, or while the version’s blocks are', () => {
    expect(connected(seeded(undefined, blocks))).toBe('');
    expect(connected(seeded(links([blockId(23)])))).toBe('');
  });

  it('draws nothing when the server did not produce the links', () => {
    expect(connected(seeded(links([blockId(23)], { status: 'not_produced', items: [] }), blocks))).toBe('');
  });

  it('draws nothing for a finding the server linked to no block, and for one it does not name', () => {
    expect(connected(seeded(links([]), blocks))).toBe('');
    expect(connected(seeded(links([], { items: [] }), blocks))).toBe('');
  });

  it('draws nothing for a version whose blocks are not produced', () => {
    expect(connected(seeded(links([blockId(23)]), notProducedPage()))).toBe('');
  });

  it('opens the block view over the finding’s blocks only: «2 / 2», never the page’s or the version’s', () => {
    const markup = connected(seeded(links([blockId(21), blockId(24)]), blocks), { initialOpen: 1, staticOpen: true });
    expect(markup).toContain('data-block-viewer');
    expect(markup).toContain('data-viewer-position="2"');
    expect(markup).toContain('2 / 2');
    expect(markup).not.toContain('2 / 4');
    // The screen is already the findings' own: the view carries no findings list of its own.
    expect(markup).not.toContain('data-page-findings-panel');
  });

  it('keeps the block view closed until a thumbnail is pressed', () => {
    expect(connected(seeded(links([blockId(23)]), blocks))).not.toContain('data-block-viewer');
  });

  it('asks for the next portion only by a press: a block on an unloaded page is counted, not fetched', () => {
    const partial = loadedUpTo(blocksOfTheVersion().slice(0, 3), true);
    const markup = connected(seeded(links([blockId(21), blockId(24)]), partial));
    expect(markup).toContain('Блоки замечания (2)');
    expect(markup).toContain('data-finding-blocks-more="idle"');
  });

  it('shows the strip in the full-screen view’s side column, after the finding and its actions', () => {
    const markup = renderScreen(
      seeded(links([blockId(23)]), blocks),
      createElement(ReviewViewerAside, {
        findingUid: FINDING_UID,
        meta: 'Критическое · Лист 1 · стр. 1',
        text: 'Не указан класс огнестойкости перекрытия',
        recommendation: 'Указать предел огнестойкости REI 45 по СП 2.13130.',
        actions: createElement('span', { 'data-row-actions': '' }),
        blocks: createElement(ReviewFindingBlocks, { projectUid: BLOCKS_PROJECT_UID, versionUid: BLOCKS_VERSION_UID, runId: RUN_ID, findingUid: FINDING_UID }),
      }),
    );
    expect(markup.indexOf('data-finding-blocks="1"')).toBeGreaterThan(markup.indexOf('data-row-actions'));
  });
});

// ------------------------------------------------------------------------------------ on the screen

function reviewMarkup(seed: (client: ReturnType<typeof newClient>) => void): string {
  const detail = findingDetail({
    observation: observation({
      evidence: [evidence({ evidence_ordinal: 1, page_number: 1, quote: 'Цитата со страницы 1.' })],
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

describe('«Разбор» shows the finding’s blocks above the page’s', () => {
  const seedBlocks = (client: ReturnType<typeof newClient>) => {
    client.setQueryData(KEY, { pages: [loadedUpTo(blocksOfTheVersion(), false)], pageParams: [undefined] });
  };

  it('puts «Блоки замечания» under the page viewer and above «Блоки страницы N»', () => {
    const markup = reviewMarkup((client) => {
      seedBlocks(client);
      client.setQueryData(queryKeys.runs.findingBlocks(RUN_ID), links([blockId(23)]));
    });
    expect(markup).toContain('Блоки замечания (1)');
    expect(markup).toContain('Блоки страницы 1 (3)');
    expect(markup.indexOf('data-finding-blocks="1"')).toBeGreaterThan(markup.indexOf('data-active-page="1"'));
    expect(markup.indexOf('data-finding-blocks="1"')).toBeLessThan(markup.indexOf('data-page-blocks="blocks"'));
  });

  it('draws only the page’s blocks when the finding has no link, as it did before', () => {
    const markup = reviewMarkup((client) => {
      seedBlocks(client);
      client.setQueryData(queryKeys.runs.findingBlocks(RUN_ID), links([]));
    });
    expect(markup).not.toContain('data-finding-blocks');
    expect(markup).not.toContain('Блоки замечания');
    expect(markup).toContain('Блоки страницы 1 (3)');
  });

  it('draws only the page’s blocks while the links are not in the cache', () => {
    const markup = reviewMarkup(seedBlocks);
    expect(markup).not.toContain('Блоки замечания');
    expect(markup).toContain('Блоки страницы 1 (3)');
  });
});
