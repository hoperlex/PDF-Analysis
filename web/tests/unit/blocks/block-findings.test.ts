/**
 * «Блоки» with the findings of each BLOCK (`UI-PARITY-C6`, contract 1.41.0): the number on a tile is the findings whose evidence
 * sits in the block, «Без сущностей» lists the blocks no finding sits in, and the block view lists the block's own findings.
 *
 * The server derives which portal blocks hold a finding's evidence (`listRunFindingBlocks`); everything here is what the screen
 * does with that answer. The cases are aimed at these mutations (not run as mutations in this lane): the block scope folded into
 * the page scope, an unlinked page read as «no findings», «not produced» read as an index, the content split reversed, the
 * «Без сущностей» chip drawn without links, the walk of the empty selection widened to the whole list.
 *
 * The blocks and findings are `fixtures.ts`'s: blocks 1..9 over five pages, findings A..E citing pages. The relation used here:
 *
 *   A  (critical)           -> block 1                       one block
 *   B  (economic)           -> blocks 1, 2, 4                three blocks, over two pages
 *   C  (undecided, proposed critical) -> block 4
 *   D  (operational, page 3)  -> none; page 3 is unlinked: the portal's raster did not describe the PDF page
 *   E  (undecided, page 4)  -> none; page 4 is linked and no block holds E's evidence
 *
 * So block 1 has 2 findings (worst: critical), block 2 has 1 (economic), block 4 has 2 (worst: economic, not C's proposal) and
 * every other block of a linked page has none. Blocks 6 and 7 lie on page 3: unknown, in no list.
 */

import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { PortalBlock, RunFindingBlockLinks } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { AR_V3_BETA_PROFILE_ID, runListQueryOptions } from '@/entities/audit-run';
import {
  blocksOfFinding,
  effectiveSelection,
  findingBlockIndex,
  hasMeaningfulContent,
  pageSelectionOf,
  pageSelectionParam,
  portalBlocksQueryOptions,
  sectionsByPage,
  sectionsOfSelection,
} from '@/entities/block';
import {
  PortalBlockListView,
  PortalBlocks,
  blockReading,
  blocksWithoutFindings,
  findingsByBlock,
  findingsByPage,
  noEntityWalk,
} from '@/widgets/portal-blocks';
import type { PageFindingsReading } from '@/widgets/portal-blocks';

import { runStatus } from '../review/fixtures';
import { newClient, renderScreen } from '../screens/harness';
import {
  BLOCKS_PROJECT_UID,
  BLOCKS_RUN_ID,
  BLOCKS_VERSION_UID,
  blockId,
  blocksOnFivePages,
  blocksVersion,
  imageBlock,
  omit,
  portalPage,
  runFindings,
  stampBlock,
  textBlock,
} from './fixtures';

beforeEach(() => {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
});
afterEach(() => {
  vi.unstubAllEnvs();
});

const FINDINGS = runFindings();
const UID = {
  A: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
  B: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
  C: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8D',
  D: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8E',
  E: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
};
const BLOCKS = blocksOnFivePages();
const RUN_AT = '2026-09-10T08:00:00.000Z';

function links(over: Partial<RunFindingBlockLinks> = {}): RunFindingBlockLinks {
  return {
    run_id: BLOCKS_RUN_ID,
    version_uid: BLOCKS_VERSION_UID,
    status: 'produced',
    unlinked_pages: [3],
    items: [
      { finding_uid: UID.A, portal_block_ids: [blockId(1)] },
      { finding_uid: UID.B, portal_block_ids: [blockId(1), blockId(2), blockId(4)] },
      { finding_uid: UID.C, portal_block_ids: [blockId(4)] },
      { finding_uid: UID.D, portal_block_ids: [] },
      { finding_uid: UID.E, portal_block_ids: [] },
    ],
    ...over,
  };
}

function reading(over: Partial<RunFindingBlockLinks> = {}): PageFindingsReading {
  const index = findingBlockIndex(links(over));
  if (index === null) throw new Error('the fixture must be produced');
  return {
    kind: 'read',
    runId: BLOCKS_RUN_ID,
    byPage: findingsByPage(FINDINGS),
    runAt: RUN_AT,
    blocks: { byBlock: findingsByBlock(FINDINGS, index), unlinkedPages: index.unlinkedPages },
  };
}

const BY_BLOCK = reading();
const BY_PAGE: PageFindingsReading = { kind: 'read', runId: BLOCKS_RUN_ID, byPage: findingsByPage(FINDINGS), runAt: RUN_AT };

// ================================================================================== the index

describe('the index of a run’s block links', () => {
  it('is none for a run the server did not produce links for: absent is not an empty index', () => {
    expect(findingBlockIndex(undefined)).toBeNull();
    expect(findingBlockIndex(links({ status: 'not_produced', items: [], unlinked_pages: [] }))).toBeNull();
  });

  it('names each finding’s blocks and the pages that have no link', () => {
    const index = findingBlockIndex(links());
    expect(blocksOfFinding(index, UID.B)).toEqual([blockId(1), blockId(2), blockId(4)]);
    expect(blocksOfFinding(index, UID.D)).toEqual([]);
    expect([...(index?.unlinkedPages ?? [])]).toEqual([3]);
  });

  it('has no blocks to show for a finding the answer does not name, or for no index', () => {
    expect(blocksOfFinding(findingBlockIndex(links()), 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q9Z')).toEqual([]);
    expect(blocksOfFinding(null, UID.A)).toEqual([]);
  });
});

describe('what a block holds', () => {
  it('is nothing for a stamp, nothing for a text block the portal read nothing in, and something for the rest', () => {
    expect(hasMeaningfulContent(stampBlock())).toBe(false);
    expect(hasMeaningfulContent(omit(textBlock(), 'recognised_text'))).toBe(false);
    expect(hasMeaningfulContent(textBlock())).toBe(true);
    expect(hasMeaningfulContent(imageBlock())).toBe(true);
    // An image block this product could not cut still holds an image.
    expect(hasMeaningfulContent(omit(imageBlock(), 'crop'))).toBe(true);
  });
});

// ============================================================================= the numbers

describe('the findings of each block', () => {
  const byBlock = BY_BLOCK.kind === 'read' ? (BY_BLOCK.blocks?.byBlock ?? new Map()) : new Map();

  it('counts a finding in every block that holds it, and each block once per finding', () => {
    expect([...byBlock.keys()].sort()).toEqual([blockId(1), blockId(2), blockId(4)]);
    expect(byBlock.get(blockId(1))?.count).toBe(2); // A and B
    expect(byBlock.get(blockId(2))?.count).toBe(1); // B
    expect(byBlock.get(blockId(4))?.count).toBe(2); // B and C
    expect(byBlock.get(blockId(1))?.scope).toBe('block');
  });

  it('takes the tone from the expert’s decided severity, never from the model’s proposal', () => {
    expect(byBlock.get(blockId(1))?.worst).toBe('critical');
    // C was proposed «critical» and is undecided: block 4 is as bad as B, which is economic.
    expect(byBlock.get(blockId(4))?.worst).toBe('economic');
  });

  it('says zero for a block of a linked page that no finding holds, as a fact of the block scope', () => {
    expect(blockReading(BY_BLOCK, BLOCKS[2] as PortalBlock)).toEqual({ scope: 'block', count: 0, worst: null, findings: [] }); // the stamp, page 1
    expect(blockReading(BY_BLOCK, BLOCKS[8] as PortalBlock)?.count).toBe(0); // page 5
  });

  it('says nothing for a block on a page the server could not place evidence on', () => {
    // Blocks 6 and 7 lie on page 3, which is unlinked: a zero there would read as «checked, nothing found».
    expect(blockReading(BY_BLOCK, BLOCKS[5] as PortalBlock)).toBeNull();
    expect(blockReading(BY_BLOCK, BLOCKS[6] as PortalBlock)).toBeNull();
  });

  it('falls back to the page’s count when the block links are not known, and to nothing when no findings were read', () => {
    expect(blockReading(BY_PAGE, BLOCKS[0] as PortalBlock)?.count).toBe(2);
    expect(blockReading(BY_PAGE, BLOCKS[0] as PortalBlock)?.scope).toBeUndefined();
    expect(blockReading({ kind: 'none' }, BLOCKS[0] as PortalBlock)).toBeNull();
    expect(blockReading({ kind: 'no-result', runId: BLOCKS_RUN_ID }, BLOCKS[0] as PortalBlock)).toBeNull();
  });

  it('counts only admitted findings: a diagnostic observation with no finding uid sits in no block', () => {
    const [first] = FINDINGS;
    const diagnostic = { ...first, finding_uid: '' } as (typeof FINDINGS)[number];
    const index = findingBlockIndex(links({ items: [{ finding_uid: '', portal_block_ids: [blockId(1)] }], unlinked_pages: [] }));
    expect(findingsByBlock([diagnostic], index as NonNullable<typeof index>).size).toBe(0);
  });
});

// ======================================================================= «Без сущностей»

describe('the blocks no finding holds', () => {
  const groups = blocksWithoutFindings(BLOCKS, BY_BLOCK);

  it('exists only when the block links are known', () => {
    expect(blocksWithoutFindings(BLOCKS, BY_PAGE)).toBeNull();
    expect(blocksWithoutFindings(BLOCKS, { kind: 'none' })).toBeNull();
    expect(groups).not.toBeNull();
  });

  it('splits them by what the block holds: something to read, or nothing', () => {
    // Free of findings: block 3 (a stamp), 5 (a text block with no recognised text), 8 and 9 (text). Blocks 1, 2 and 4 hold
    // findings; blocks 6 and 7 are on the unlinked page 3 and are in neither list.
    expect(groups?.withoutFindings.map((block) => block.portal_block_id)).toEqual([blockId(8), blockId(9)]);
    expect(groups?.withoutContent.map((block) => block.portal_block_id)).toEqual([blockId(3), blockId(5)]);
  });

  it('walks the first list and then the second, as the original’s prev/next does', () => {
    expect(noEntityWalk(groups as NonNullable<typeof groups>).map((block) => block.portal_block_id)).toEqual([
      blockId(8),
      blockId(9),
      blockId(3),
      blockId(5),
    ]);
  });

  it('leaves a block of an unlinked page out of both lists even though it holds nothing', () => {
    const everyone = [...(groups?.withoutFindings ?? []), ...(groups?.withoutContent ?? [])].map((block) => block.portal_block_id);
    expect(everyone).not.toContain(blockId(6));
    expect(everyone).not.toContain(blockId(7));
  });
});

describe('the selection «Без сущностей» in the address', () => {
  it('is read from and written to ?page=empty and survives the round trip', () => {
    expect(pageSelectionOf('empty')).toBe('empty');
    expect(pageSelectionParam('empty')).toBe('empty');
    expect(pageSelectionOf(pageSelectionParam('empty'))).toBe('empty');
    expect(pageSelectionOf('Empty')).toBe('all');
  });

  it('shows no page’s sections, and stays itself when the loaded pages change', () => {
    const sections = sectionsByPage(BLOCKS);
    expect(effectiveSelection(sections, 'empty')).toBe('empty');
    expect(sectionsOfSelection(sections, 'empty')).toEqual([]);
  });
});

// ================================================================================ the markup

function list(over: Partial<Parameters<typeof PortalBlockListView>[0]> = {}): string {
  return renderScreen(
    newClient(),
    createElement(PortalBlockListView, {
      projectUid: BLOCKS_PROJECT_UID,
      blockCount: BLOCKS.length,
      producedByRunId: BLOCKS_RUN_ID,
      blocks: BLOCKS,
      versionUid: BLOCKS_VERSION_UID,
      hasMore: false,
      loadingMore: false,
      moreFailure: null,
      onMore: () => {},
      ...over,
    }),
  );
}

function count(markup: string, needle: string): number {
  return markup.split(needle).length - 1;
}

function visibleText(markup: string): string {
  return markup
    .replace(/<code>[\s\S]*?<\/code>/g, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .trim();
}

/** The tile of block `n`: its button, by the block's crop or its position in the grid. */
function tiles(markup: string): string[] {
  return [...markup.matchAll(/<button\b[^>]*data-portal-block-type[^>]*>[\s\S]*?<\/button>/g)].map((m) => m[0]);
}

describe('the tiles with the block links', () => {
  // Rendered per test, after the top-level `beforeEach` has set the API base the crop address needs.
  let markup = '';
  let all: string[] = [];
  beforeEach(() => {
    markup = list({ pageFindings: BY_BLOCK });
    all = tiles(markup);
  });

  it('number a tile with its own block’s findings, not its page’s', () => {
    // Block 1 and block 3 are both on page 1, whose page count is 2: only block 1 holds the findings.
    expect(all[0]).toContain('data-tile-badge="2"');
    expect(all[2]).not.toContain('data-tile-badge');
    expect(all[2]).toContain('data-has-findings="false"');
    expect(all[1]).toContain('data-tile-badge="1"');
    expect(all[3]).toContain('data-tile-badge="2"');
  });

  it('say «в блоке» in the title and name the run', () => {
    expect(all[0]).toContain('title="Замечаний в блоке: 2 (по прогону от 2026-09-10 08:00:00 UTC)"');
    expect(all[0]).not.toContain('Замечаний на странице');
  });

  it('colour by the worst DECIDED severity of the block’s findings', () => {
    expect(all[0]).toContain('am-badge--failed'); // critical
    expect(all[1]).toContain('am-badge--degraded'); // economic
    expect(all[3]).toContain('am-badge--degraded'); // B economic, C undecided
  });

  it('carry no number on a page the server could not place evidence on, and no zero there', () => {
    // The tiles of page 3 are the sixth and seventh.
    for (const tile of [all[5], all[6]] as string[]) {
      expect(tile).not.toContain('data-tile-badge');
      expect(tile).toContain('data-has-findings="false"');
    }
  });

  it('keep the page’s number, and say so, when the block links are not known', () => {
    const page = list({ pageFindings: BY_PAGE });
    expect(tiles(page)[2]).toContain('data-tile-badge="2"');
    expect(page).toContain('title="Замечаний на странице 1: 2 (по прогону от 2026-09-10 08:00:00 UTC)"');
    expect(page).not.toContain('data-findings-scope="block"');
    expect(visibleText(page)).toContain('Привязки замечаний к блокам для этого прогона нет.');
  });

  it('explain the block number, its cover rule and the unknown pages in the note', () => {
    expect(markup).toContain('data-findings-scope="block"');
    expect(visibleText(markup)).toContain('цитата которых лежит в этом блоке');
    expect(visibleText(markup)).toContain('не менее половины места цитаты на странице');
    expect(visibleText(markup)).toContain('чисел нет: там неизвестно, есть ли замечания у блока');
  });
});

describe('the selector’s «Без сущностей»', () => {
  const chip = (markup: string) =>
    [...markup.matchAll(/<button\b[^>]*data-page-chip="empty"[^>]*>[\s\S]*?<\/button>/g)].map((m) => m[0]);

  it('is the last chip, with the number of blocks no finding holds', () => {
    const markup = list({ pageFindings: BY_BLOCK });
    expect(chip(markup)).toHaveLength(1);
    expect(chip(markup)[0]).toContain('>Без сущностей (4)<');
    expect(chip(markup)[0]).toContain('aria-pressed="false"');
    expect(markup.lastIndexOf('data-page-chip="empty"')).toBeGreaterThan(markup.lastIndexOf('data-page-chip="5"'));
  });

  it('is not drawn without the block links, or when no block is free of findings', () => {
    expect(chip(list({ pageFindings: BY_PAGE }))).toHaveLength(0);
    expect(chip(list())).toHaveLength(0);
    const every = reading({
      items: [{ finding_uid: UID.A, portal_block_ids: BLOCKS.map((block) => block.portal_block_id) }],
      unlinked_pages: [],
    });
    expect(chip(list({ pageFindings: every }))).toHaveLength(0);
  });

  it('says in its title that the number is of the loaded blocks while more are waiting', () => {
    const markup = list({ pageFindings: BY_BLOCK, hasMore: true });
    expect(chip(markup)[0]).toContain('; число — по загруженным блокам.');
    expect(chip(list({ pageFindings: BY_BLOCK }))[0]).not.toContain('по загруженным');
  });
});

describe('the list «Без сущностей»', () => {
  let markup = '';
  beforeEach(() => {
    markup = list({ pageFindings: BY_BLOCK, initialPage: 'empty' });
  });
  const section = (group: string) =>
    new RegExp(`<section\\b[^>]*data-portal-empty="${group}"[\\s\\S]*?</section>`).exec(markup)?.[0] ?? '';

  it('is the chosen chip and draws no page sections', () => {
    expect(markup).toContain('data-page-chip="empty"');
    expect(/data-page-chip="empty"[^>]*aria-pressed="true"|aria-pressed="true"[^>]*data-page-chip="empty"/.test(markup)).toBe(true);
    expect(markup).not.toContain('data-portal-page=');
  });

  it('draws the two lists the original draws, with their counts and what each means', () => {
    expect(visibleText(section('withoutFindings'))).toContain('Замечаний не выявлено (2)');
    expect(visibleText(section('withoutFindings'))).toContain('Ни одно замечание прогона не лежит в этих блоках');
    expect(visibleText(section('withoutContent'))).toContain('Без значимого содержимого (2)');
    expect(visibleText(section('withoutContent'))).toContain('нечего читать');
    // The first list comes first.
    expect(markup.indexOf('data-portal-empty="withoutFindings"')).toBeLessThan(markup.indexOf('data-portal-empty="withoutContent"'));
  });

  it('puts the right blocks in each: free text blocks in the first, the stamp and the empty text block in the second', () => {
    expect(tiles(section('withoutFindings'))).toHaveLength(2);
    expect(tiles(section('withoutFindings')).every((tile) => tile.includes('data-portal-block-type="text"'))).toBe(true);
    expect(tiles(section('withoutContent')).map((tile) => /data-portal-block-type="([a-z]+)"/.exec(tile)?.[1])).toEqual(['stamp', 'text']);
    expect(count(markup, 'data-portal-block-type')).toBe(4);
  });

  it('draws no number on these tiles: no finding holds them', () => {
    expect(markup).not.toContain('data-tile-badge');
  });

  it('opens a block view that walks both lists, as «i / 4»', () => {
    const open = list({ pageFindings: BY_BLOCK, initialPage: 'empty', initialOpen: 2, staticOpen: true });
    expect(open).toContain('data-viewer-position="3"');
    expect(open).toContain('3 / 4');
    expect(open).toContain('Штамп · стр. 1');
  });

  it('is «Все блоки» again when it is chosen without the block links', () => {
    for (const pageFindings of [BY_PAGE, undefined]) {
      const fallback = list({ ...(pageFindings === undefined ? {} : { pageFindings }), initialPage: 'empty' });
      expect(fallback).not.toContain('data-portal-empty');
      expect(count(fallback, 'data-portal-page=')).toBe(5);
    }
  });
});

describe('the block view’s findings panel', () => {
  const open = (at: number) => list({ pageFindings: BY_BLOCK, initialOpen: at, staticOpen: true });
  const panel = (markup: string) => /<section\b[^>]*data-page-findings-panel[\s\S]*?<\/section>/.exec(markup)?.[0] ?? '';

  it('lists the findings that sit in the block, and says they are the block’s', () => {
    const shown = panel(open(0));
    expect(shown).toContain('data-findings-scope="block"');
    expect(shown).toContain('data-page-findings-panel="2"');
    expect(visibleText(shown)).toContain('Замечания в блоке (2)');
    expect(visibleText(shown)).toContain('Замечания прогона, цитата которых лежит в этом блоке');
    expect(visibleText(shown)).toContain('(по прогону от 2026-09-10 08:00:00 UTC)');
    expect(count(shown, 'data-finding-uid=')).toBe(2);
    expect(shown).not.toContain('Замечание указывает страницу PDF');
  });

  it('says a block no finding holds has none', () => {
    const shown = panel(open(2)); // the stamp of page 1
    expect(shown).toContain('data-page-findings-panel="0"');
    expect(visibleText(shown)).toContain('Ни одно замечание прогона не лежит в этом блоке.');
    expect(shown).not.toContain('data-finding-uid');
  });

  it('is not drawn for a block on a page the server could not place evidence on', () => {
    expect(open(5)).not.toContain('data-page-findings-panel');
  });
});

// ============================================================ the widget over the seeded cache

describe('the widget reads the block links of the run in scope', () => {
  const run = BLOCKS_RUN_ID;

  function widget(client: ReturnType<typeof newClient>): string {
    return renderScreen(client, createElement(PortalBlocks, { version: blocksVersion(true) }));
  }

  function seeded(linksAnswer?: RunFindingBlockLinks) {
    const client = newClient();
    client.setQueryData(portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey, {
      pages: [portalPage(BLOCKS)],
      pageParams: [undefined],
    });
    client.setQueryData(runListQueryOptions(BLOCKS_VERSION_UID).queryKey, {
      items: [runStatus({ run_id: run, version_uid: BLOCKS_VERSION_UID })],
      page: { next_cursor: null },
    });
    client.setQueryData(queryKeys.runs.detail(run), runStatus({ run_id: run, created_at: RUN_AT }));
    client.setQueryData(queryKeys.runs.findings(run), { data: { items: [...FINDINGS], page: { next_cursor: null } } });
    if (linksAnswer !== undefined) client.setQueryData(queryKeys.runs.findingBlocks(run), linksAnswer);
    return client;
  }

  it('numbers the tiles by block and offers «Без сущностей» once the links are in the cache', () => {
    const markup = widget(seeded(links()));
    expect(markup).toContain('data-findings-scope="block"');
    expect(tiles(markup)[0]).toContain('data-tile-badge="2"');
    expect(tiles(markup)[2]).not.toContain('data-tile-badge');
    expect(markup).toContain('>Без сущностей (4)<');
  });

  it('keeps the page numbers, with no «Без сущностей», while the links are on their way', () => {
    const markup = widget(seeded());
    expect(tiles(markup)[2]).toContain('data-tile-badge="2"');
    expect(markup).not.toContain('data-findings-scope="block"');
    expect(markup).not.toContain('Без сущностей');
  });

  it('keeps the page numbers when the server answered that the links were not produced', () => {
    const markup = widget(seeded(links({ status: 'not_produced', items: [], unlinked_pages: [] })));
    expect(tiles(markup)[2]).toContain('data-tile-badge="2"');
    expect(markup).not.toContain('data-findings-scope="block"');
    expect(markup).not.toContain('Без сущностей');
  });

  it('does not ask for the links of a run that is not in scope', () => {
    // The v3 beta profile publishes no canonical findings: no findings are read, and the links are not used.
    const client = seeded(links());
    client.setQueryData(runListQueryOptions(BLOCKS_VERSION_UID).queryKey, {
      items: [runStatus({ run_id: run, version_uid: BLOCKS_VERSION_UID, analysis_profile_id: AR_V3_BETA_PROFILE_ID })],
      page: { next_cursor: null },
    });
    client.setQueryData(queryKeys.runs.detail(run), runStatus({ run_id: run, analysis_profile_id: AR_V3_BETA_PROFILE_ID }));
    const markup = widget(client);
    expect(markup).not.toContain('data-tile-badge');
    expect(markup).not.toContain('Без сущностей');
  });
});
