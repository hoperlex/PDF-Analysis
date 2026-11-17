'use client';

/**
 * The bottom bar of a section's selection (`UIP-S02-03`, the original's «Выбрано: N · Запустить все (N)»).
 *
 * While at least one card is chosen the bar sticks to the bottom of the area: «Выбрано: N», «Запустить все (N)» and «Снять выделение».
 * «Запустить все» opens the existing batch panel (`SectionBatchBar` holds it) — the estimate and the ONE consent for the batch, which stay
 * on the server (`R-151c`, `BatchStartPanel`); no native window is involved. The bar is the last thing of the page, so scrolled to its end
 * it stands after the last row and covers no card, and the page keeps room under the cards while it is drawn; it is plain buttons in the
 * order of the page, so the keyboard reaches it, and its count is a live status. It is drawn for whoever may start an audit and only while
 * something is chosen: `BatchSelection.selection` is `undefined` for a session that cannot start one, and while the batch panel holds the
 * choice.
 *
 * The choosing is the header's (`SectionHeader`); the notes of the listing being read are the row over the cards (`SectionBatchBar`).
 */

import type { BatchSelection } from '@/widgets/project-sections';

import styles from './section-selection-bar.module.css';

export interface SectionSelectionBarProps {
  readonly selection: BatchSelection;
}

export function SectionSelectionBar({ selection }: SectionSelectionBarProps) {
  if (selection.selection === undefined || selection.chosenCount === 0) return null;
  return (
    <div className={styles.bar} role="region" aria-label="Выбранные документы" data-batch-bar="" data-batch-selection={selection.chosenCount}>
      <span className={styles.count} role="status">Выбрано: {selection.chosenCount}</span>
      <span className={styles.actions}>
        <button type="button" className="am-button am-button--small" onClick={selection.openBatch} data-batch-start="">
          Запустить все ({selection.chosenCount})
        </button>
        <button type="button" className="am-button am-button--quiet am-button--small" onClick={selection.clear} data-clear-selection="">
          Снять выделение
        </button>
      </span>
    </div>
  );
}
