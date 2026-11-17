/**
 * The page buttons of «Блоки» are named by the sheet the portal gave the page (`UIP-S07-01`).
 *
 * The original's buttons say «Лист N (n)»: N is the page's sheet, n the blocks it holds. Ours said «Стр. N (n)» by the PDF
 * page. Here the button says the sheet when the portal named one, the same read the «Лист» column of «Разбор» shows
 * (`listVersionSheetLabels`), and keeps «Стр. N» when it named none or the read is not here. Held, each with what could break it:
 *
 *   - a sheet the portal named is the word of the button, and its `title` names the PDF page (the hint the owner's wording asks for);
 *   - a page with no sheet (the portal named it two, the read is on its way or failed, the render has no reader at all) is
 *     «Стр. N (n)», never a guessed number and never the page number dressed as a sheet;
 *   - two pages with one sheet are told apart: the first keeps «Лист N», the second and the following say «Лист N · стр. P»;
 *   - the container (`PortalBlocks`) hands the chips what it read, and a read that failed does not break the list;
 *   - «Все блоки» is one grid with no heading per page and a chosen page keeps its heading; the tile minimum leaves
 *     five tiles in a row on a 1440 px window, counted from the frame's own numbers so a wider minimum fails here.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { VersionSheetLabelList } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { pageChips, portalBlocksQueryOptions, sectionsByPage } from '@/entities/block';
import { PageSelector, PortalBlocks } from '@/widgets/portal-blocks';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderScreen, seedError } from '../screens/harness';
import { BLOCKS_VERSION_UID, blocksVersion, everyKindOfBlock, portalPage } from './fixtures';

const noop = (): void => undefined;

// The tiles build a crop address from the API base: the render needs the setting, as the other «Блоки» suites give it.
beforeEach(() => {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
});
afterEach(() => {
  vi.unstubAllEnvs();
});

/** The chips of `everyKindOfBlock()`: pages 1, 2 and 3 holding 3, 2 and 2 blocks. */
const CHIPS = pageChips(sectionsByPage(everyKindOfBlock()));

function selector(sheetOf?: (page: number) => number | undefined): string {
  return renderScreen(
    newClient(),
    createElement(PageSelector, { chips: CHIPS, total: 7, partial: false, selection: 'all', onSelect: noop, ...(sheetOf === undefined ? {} : { sheetOf }) }),
  );
}

/** The `<button …>…</button>` of each page chip, in order. */
function chipButtons(markup: string): string[] {
  return markup.match(/<button\b[^>]*data-page-chip="\d+"[^>]*>[\s\S]*?<\/button>/g) ?? [];
}

const textOf = (html: string): string => html.replace(/<[^>]*>/g, '').trim();
const titleOf = (html: string): string | null => /\stitle="([^"]*)"/.exec(html)?.[1] ?? null;

describe('a page button is named by the sheet the portal gave the page', () => {
  it('says «Лист N (n)» for each page that has a sheet, and its title names the page of the PDF', () => {
    const chips = chipButtons(selector((page) => ({ 1: 11, 2: 12, 3: 13 })[page]));
    expect(chips.map(textOf)).toEqual(['Лист 11 (3)', 'Лист 12 (2)', 'Лист 13 (2)']);
    expect(titleOf(chips[0] as string)).toBe('Страница 1 PDF; у портала это лист 11.');
    expect(titleOf(chips[1] as string)).toBe('Страница 2 PDF; у портала это лист 12.');
    expect(titleOf(chips[2] as string)).toBe('Страница 3 PDF; у портала это лист 13.');
  });

  it('is not the page number dressed as a sheet: a sheet equal to the page is still the sheet the portal said', () => {
    expect(chipButtons(selector((page) => page)).map(textOf)).toEqual(['Лист 1 (3)', 'Лист 2 (2)', 'Лист 3 (2)']);
  });

  it('keeps «Стр. N (n)» for a page the portal named no single sheet, beside the pages that have one', () => {
    const chips = chipButtons(selector((page) => (page === 2 ? undefined : page + 10)));
    expect(chips.map(textOf)).toEqual(['Лист 11 (3)', 'Стр. 2 (2)', 'Лист 13 (2)']);
    // the page that is not named a sheet keeps the old hint: the portal's own label of the page, when it differs
    expect(titleOf(chips[1] as string)).toBe('У портала страница названа 5.');
  });

  it('keeps «Стр. N (n)» on every button when the render has no reader of sheets', () => {
    const chips = chipButtons(selector());
    expect(chips.map(textOf)).toEqual(['Стр. 1 (3)', 'Стр. 2 (2)', 'Стр. 3 (2)']);
    expect(chips.some((chip) => textOf(chip).includes('Лист'))).toBe(false);
    expect(titleOf(chips[0] as string)).toBeNull();
    expect(titleOf(chips[1] as string)).toBe('У портала страница названа 5.');
  });

  it('can fail: a reader that names a sheet changes the button, one that names none does not', () => {
    expect(chipButtons(selector(() => 7)).map(textOf)).not.toEqual(chipButtons(selector(() => undefined)).map(textOf));
  });
});

describe('two pages with one sheet are told apart', () => {
  it('the first keeps «Лист N (n)», the second says «Лист N · стр. P (n)»', () => {
    const chips = chipButtons(selector((page) => (page === 2 ? 12 : 4)));
    expect(chips.map(textOf)).toEqual(['Лист 4 (3)', 'Лист 12 (2)', 'Лист 4 · стр. 3 (2)']);
    expect(titleOf(chips[2] as string)).toBe('Страница 3 PDF; у портала это лист 4.');
  });

  it('the second and every following say «Лист N · стр. P (n)», in the order of the buttons', () => {
    expect(chipButtons(selector(() => 9)).map(textOf)).toEqual(['Лист 9 (3)', 'Лист 9 · стр. 2 (2)', 'Лист 9 · стр. 3 (2)']);
  });

  it('never makes two buttons carry the same words', () => {
    for (const sheetOf of [() => 9, (page: number) => (page === 2 ? 12 : 4), (page: number) => page, () => undefined]) {
      const words = chipButtons(selector(sheetOf)).map(textOf);
      expect(new Set(words.map((word) => word.replace(/ \(\d+\)$/, ''))).size).toBe(words.length);
    }
  });

  it('presses the chip of the chosen page and leaves «Все блоки» and «Без сущностей» as they were', () => {
    const markup = renderScreen(
      newClient(),
      createElement(PageSelector, { chips: CHIPS, total: 7, partial: false, selection: 2, onSelect: noop, noEntities: 2, sheetOf: () => 9 }),
    );
    expect(markup).toMatch(/aria-pressed="true"[^>]*data-page-chip="2"|data-page-chip="2"[^>]*aria-pressed="true"/);
    expect(textOf(/<button\b[^>]*data-page-chip="all"[^>]*>[\s\S]*?<\/button>/.exec(markup)?.[0] ?? '')).toBe('Все блоки (7)');
    expect(textOf(/<button\b[^>]*data-page-chip="empty"[^>]*>[\s\S]*?<\/button>/.exec(markup)?.[0] ?? '')).toBe('Без сущностей (2)');
  });
});

describe('the container reads the sheets and hands them to the buttons', () => {
  function labels(items: VersionSheetLabelList['items'], status: VersionSheetLabelList['status'] = 'produced'): VersionSheetLabelList {
    return { status, version_uid: BLOCKS_VERSION_UID, items };
  }

  function open(prepare: (client: ReturnType<typeof newClient>) => void, page?: Parameters<typeof PortalBlocks>[0]['page']): string {
    const client = newClient();
    client.setQueryData(portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey, { pages: [portalPage(everyKindOfBlock())], pageParams: [undefined] });
    prepare(client);
    return renderScreen(client, createElement(PortalBlocks, { version: blocksVersion(true), ...(page === undefined ? {} : { page }) }));
  }

  const SHEETS = labels([
    { page_number: 1, page_label: 21, block_count: 3 },
    { page_number: 2, page_label: 22, block_count: 2 },
    { page_number: 3, page_label: 21, block_count: 2 },
  ]);

  it('names the buttons by the sheets the version’s read holds', () => {
    const markup = open((client) => client.setQueryData(queryKeys.versions.sheetLabels(BLOCKS_VERSION_UID), SHEETS));
    expect(chipButtons(markup).map(textOf)).toEqual(['Лист 21 (3)', 'Лист 22 (2)', 'Лист 21 · стр. 3 (2)']);
  });

  it('keeps «Стр. N» while the read is on its way, and when it failed', () => {
    expect(chipButtons(open(() => undefined)).map(textOf)).toEqual(['Стр. 1 (3)', 'Стр. 2 (2)', 'Стр. 3 (2)']);
    const failed = open((client) => seedError(client, queryKeys.versions.sheetLabels(BLOCKS_VERSION_UID), new Error('refused')));
    expect(chipButtons(failed).map(textOf)).toEqual(['Стр. 1 (3)', 'Стр. 2 (2)', 'Стр. 3 (2)']);
    // the tiles are still there: a sheet read that did not come never takes the list with it
    expect(failed).toContain('data-portal-grid="all"');
  });

  it('keeps «Стр. N» for a page the read does not list, and while no run has produced the geometry', () => {
    const partial = open((client) => client.setQueryData(queryKeys.versions.sheetLabels(BLOCKS_VERSION_UID), labels([{ page_number: 3, page_label: 21, block_count: 2 }])));
    expect(chipButtons(partial).map(textOf)).toEqual(['Стр. 1 (3)', 'Стр. 2 (2)', 'Лист 21 (2)']);
    const none = open((client) => client.setQueryData(queryKeys.versions.sheetLabels(BLOCKS_VERSION_UID), labels([], 'not_produced')));
    expect(chipButtons(none).map(textOf)).toEqual(['Стр. 1 (3)', 'Стр. 2 (2)', 'Стр. 3 (2)']);
  });
});

describe('«Все блоки» is one solid grid and a chosen page keeps its heading', () => {
  const grid = (markup: string): string => /<section\b[^>]*data-portal-grid="all"[\s\S]*?<\/section>/.exec(markup)?.[0] ?? '';

  function open(page?: Parameters<typeof PortalBlocks>[0]['page']): string {
    const client = newClient();
    client.setQueryData(portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey, { pages: [portalPage(everyKindOfBlock())], pageParams: [undefined] });
    return renderScreen(client, createElement(PortalBlocks, { version: blocksVersion(true), ...(page === undefined ? {} : { page }) }));
  }

  it('«Все блоки»: every tile in one list, no «Страница N», the page in each tile’s caption', () => {
    const markup = open();
    expect(markup.split('data-portal-grid="all"').length - 1).toBe(1);
    expect(markup).not.toContain('data-portal-page=');
    expect(markup).not.toMatch(/<h3[^>]*>\s*Страница/);
    expect(grid(markup).split('<li>').length - 1).toBe(7);
    expect(grid(markup).split('<ol').length - 1).toBe(1);
    for (const page of [1, 2, 3]) expect(grid(markup)).toContain(`стр. ${page}`);
  });

  it('a chosen page: its own section under «Страница N», and no solid grid beside it', () => {
    const markup = open(2);
    expect(markup).not.toContain('data-portal-grid=');
    expect(markup.split('data-portal-page=').length - 1).toBe(1);
    expect(markup).toMatch(/<h3[^>]*>Страница (?:<!-- -->)?2/);
  });
});

describe('the tile minimum leaves five tiles in a row on a 1440 px window', () => {
  // The frame's own numbers, read from the styles and not repeated here: the sidebar column, the page padding, the panel
  // of the «Блоки» tab (its padding and border) and the tile gap.
  const css = (relative: string): string => readFileSync(join(WEB_ROOT, relative), 'utf8');
  const globals = css('src/app/globals.css');
  const px = (source: string, pattern: RegExp): number => Number((pattern.exec(source) ?? [])[1]);

  const SIDEBAR = px(globals, /\.am-app\s*\{[^}]*grid-template-columns:\s*(\d+)px/);
  const PAGE_PAD = px(globals, /--am-page-pad-x:\s*(\d+)px/);
  const GAP = px(globals, /--am-gap-sm:\s*(\d+)px/);
  const PANEL_PAD = px(globals, /--am-gap:\s*(\d+)px/);
  const MINIMUM = px(css('src/widgets/portal-blocks/ui/portal-blocks.module.css'), /\.blocks\s*\{[^}]*grid-template-columns:\s*repeat\(auto-fill,\s*minmax\((\d+)px/);

  it('reads every number from the styles', () => {
    for (const value of [SIDEBAR, PAGE_PAD, GAP, PANEL_PAD, MINIMUM]) expect(Number.isFinite(value) && value > 0).toBe(true);
  });

  it('fits five minimum-width tiles and their gaps in the width the tab leaves, and no sixth', () => {
    // 1 px of border on each side of the panel
    const width = 1440 - SIDEBAR - 2 * PAGE_PAD - 2 * (PANEL_PAD + 1);
    const columns = Math.floor((width + GAP) / (MINIMUM + GAP));
    expect(columns).toBeGreaterThanOrEqual(5);
  });

  it('still holds five when the frame is 303 px wide instead of the sidebar’s column', () => {
    const width = 1440 - 303 - 2 * PAGE_PAD - 2 * (PANEL_PAD + 1);
    expect(Math.floor((width + GAP) / (MINIMUM + GAP))).toBeGreaterThanOrEqual(5);
  });

  it('can fail: a minimum of 250 px leaves four', () => {
    const width = 1440 - 303 - 2 * PAGE_PAD - 2 * (PANEL_PAD + 1);
    expect(Math.floor((width + GAP) / (250 + GAP))).toBeLessThan(5);
  });
});
