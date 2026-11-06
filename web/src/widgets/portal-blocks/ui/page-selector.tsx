'use client';

/**
 * The page selector above the tiles: «Все блоки (N)» and one chip per page, «Стр. N (count)».
 *
 * The counts are of the blocks loaded so far. While the API has another page of blocks to give
 * (`partial`) the selector says that the counts are of what has arrived, in words beside it, rather
 * than letting «Все блоки (100)» pass for the version's whole list. A page the portal labels
 * differently carries that label in the chip's `title`, as the page's heading says it.
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
}

export function PageSelector({ chips, total, partial, selection, onSelect }: PageSelectorProps) {
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
      {chips.map((chip) => (
        <button
          key={chip.pageNumber}
          type="button"
          className={styles.chip}
          aria-pressed={selection === chip.pageNumber}
          data-page-chip={chip.pageNumber}
          {...(chip.differingLabel === null ? {} : { title: `У портала страница названа ${chip.differingLabel}.` })}
          onClick={() => {
            onSelect(chip.pageNumber);
          }}
        >
          {`Стр. ${chip.pageNumber} (${chip.count})`}
        </button>
      ))}
    </div>
  );
}
