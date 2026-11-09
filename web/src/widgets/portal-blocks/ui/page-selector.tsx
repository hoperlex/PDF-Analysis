'use client';

/**
 * The page selector above the tiles: «Все блоки (N)» and one chip per page, «Стр. N (count)».
 *
 * «Без сущностей (N)» follows the pages when the run's block links are known (`UI-PARITY-C6`): the blocks no finding of the run
 * sits in. It is not drawn without them, nor when there are none.
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
  /** How many loaded blocks no finding holds, when that is known and not zero; absent draws no «Без сущностей». */
  readonly noEntities?: number | undefined;
}

export function PageSelector({ chips, total, partial, selection, onSelect, noEntities }: PageSelectorProps) {
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
