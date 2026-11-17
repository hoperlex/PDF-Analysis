'use client';

/**
 * The page selector above the tiles: «Все блоки (N)» and one chip per page, «Лист N (count)» or «Стр. N (count)».
 *
 * **A chip is named as the original names it** (`UIP-S07-01`): by the sheet the portal gave the page, the very label the
 * «Лист» column of «Разбор» shows, when the container can say it (`sheetOf`); the page's PDF number stands in the chip's
 * `title`. A page the portal named no single sheet (two sheets on one page, labels still being read or not read) keeps
 * «Стр. N». Two pages that would get the same «Лист N» are told apart: the first keeps the bare word, the second and
 * the following say «Лист N · стр. P». Without `sheetOf` (the static renders of the census and the guard tests) every
 * chip is «Стр. N».
 *
 * «Без сущностей (N)» follows the pages when the run's block links are known (`UI-PARITY-C6`): the blocks no finding of the run
 * sits in. It is not drawn without them, nor when there are none.
 *
 * The counts are of the blocks loaded so far. While the API has another page of blocks to give
 * (`partial`) the selector says that the counts are of what has arrived, in words beside it, rather
 * than letting «Все блоки (100)» pass for the version's whole list. A «Стр. N» chip of a page the portal labels
 * differently carries that label in its `title`, as the page's heading says it.
 */

import type { PageChip, PageSelection } from '@/entities/block';

import styles from './portal-blocks.module.css';

export interface PageSelectorProps {
  readonly chips: readonly PageChip[];
  /** The loaded blocks, all pages. */
  readonly total: number;
  /** Whether the API has more blocks than are loaded. */
  readonly partial: boolean;
  readonly selection: PageSelection;
  readonly onSelect: (selection: PageSelection) => void;
  /** How many loaded blocks no finding holds, when that is known and not zero; absent draws no «Без сущностей». */
  readonly noEntities?: number | undefined;
  /** The sheet the portal gave a PDF page, or `undefined` when it named none; absent, every chip is «Стр. N». */
  readonly sheetOf?: ((page: number) => number | undefined) | undefined;
}

/** What one chip says, and what its hint says; the pages are named in the order the chips are drawn. */
function chipWords(chips: readonly PageChip[], sheetOf: PageSelectorProps['sheetOf']): readonly { text: string; title: string | undefined }[] {
  const named = new Set<number>();
  return chips.map((chip) => {
    const sheet = sheetOf?.(chip.pageNumber);
    if (sheet === undefined) {
      return {
        text: `Стр. ${chip.pageNumber} (${chip.count})`,
        title: chip.differingLabel === null ? undefined : `У портала страница названа ${chip.differingLabel}.`,
      };
    }
    const repeated = named.has(sheet);
    named.add(sheet);
    return {
      text: repeated ? `Лист ${sheet} · стр. ${chip.pageNumber} (${chip.count})` : `Лист ${sheet} (${chip.count})`,
      title: `Страница ${chip.pageNumber} PDF; у портала это лист ${sheet}.`,
    };
  });
}

export function PageSelector({ chips, total, partial, selection, onSelect, noEntities, sheetOf }: PageSelectorProps) {
  const words = chipWords(chips, sheetOf);
  return (
    <div className={styles.selector} role="group" aria-label="Страницы документа" data-page-selector="">
      <button
        type="button"
        className={styles.chip}
        aria-pressed={selection === 'all'}
        data-page-chip="all"
        {...(partial ? { title: 'Загружены не все блоки комплекта: число — по загруженным.' } : {})}
        onClick={() => {
          onSelect('all');
        }}
      >
        {`Все блоки (${total})`}
      </button>
      {chips.map((chip, at) => (
        <button
          key={chip.pageNumber}
          type="button"
          className={styles.chip}
          aria-pressed={selection === chip.pageNumber}
          data-page-chip={chip.pageNumber}
          title={words[at]?.title}
          onClick={() => {
            onSelect(chip.pageNumber);
          }}
        >
          {words[at]?.text}
        </button>
      ))}
      {noEntities === undefined || noEntities === 0 ? null : (
        <button
          type="button"
          className={styles.chip}
          aria-pressed={selection === 'empty'}
          data-page-chip="empty"
          title={`Блоки, в которых не лежит ни одно замечание прогона${partial ? '; число — по загруженным блокам' : ''}.`}
          onClick={() => {
            onSelect('empty');
          }}
        >
          {`Без сущностей (${noEntities})`}
        </button>
      )}
    </div>
  );
}
