/**
 * «Отличия: N» with ← and → (`CMP-VIEWER-01`, `version-comparison-viewer.js:134-144`): the differences the engine found,
 * the toggles that bring the shifts and the look of lines into the list, and a click that shows a difference on the sheet.
 */

import type { ComparisonDifference } from '@/shared/api';

import { type DifferenceFilter, countDifferences, shownIndices } from '../model/differences';
import { regionClassLabel } from '../model/labels';

import { BeforeAfter } from './before-after';
import styles from './comparison-viewer.module.css';

export interface DifferenceListProps {
  readonly differences: readonly ComparisonDifference[];
  readonly filter: DifferenceFilter;
  readonly selected: number | null;
  readonly onSelect: (index: number) => void;
  readonly onStep: (direction: -1 | 1) => void;
  readonly onShifts: (on: boolean) => void;
  readonly onStyleOnly: (on: boolean) => void;
}

export function DifferenceList({ differences, filter, selected, onSelect, onStep, onShifts, onStyleOnly }: DifferenceListProps) {
  const counts = countDifferences(differences, filter);
  const indices = shownIndices(differences, filter);
  return (
    <section className={styles.panel} aria-label="Отличия" data-differences={counts.shown}>
      <h3 className={styles.panelTitle}>
        <span>Отличия: {counts.shown}</span>
        <span className={styles.stepper}>
          <button type="button" className="am-button am-button--quiet am-button--small" aria-label="Предыдущее отличие" disabled={counts.shown === 0} onClick={() => onStep(-1)}>
            ←
          </button>
          <button type="button" className="am-button am-button--quiet am-button--small" aria-label="Следующее отличие" disabled={counts.shown === 0} onClick={() => onStep(1)}>
            →
          </button>
        </span>
      </h3>
      {counts.shifts === 0 ? null : (
        <label className={styles.choice}>
          <input type="checkbox" checked={filter.showShifts} onChange={(event) => onShifts(event.target.checked)} />
          сдвиги (не изменение): {counts.shifts} — показать в списке
        </label>
      )}
      {counts.styleOnly === 0 ? null : (
        <label className={styles.choice}>
          <input type="checkbox" checked={filter.showStyleOnly} onChange={(event) => onStyleOnly(event.target.checked)} />
          оформление линий: {counts.styleOnly} — показать в списке
        </label>
      )}
      {indices.length === 0 ? (
        <p className={styles.empty}>В списке нет отличий.</p>
      ) : (
        <ol className={styles.list}>
          {indices.map((index) => {
            const difference = differences[index] as ComparisonDifference;
            const chosen = selected === index;
            return (
              <li key={index}>
                <button
                  type="button"
                  className={chosen ? `${styles.item} ${styles.itemSelected}` : styles.item}
                  aria-current={chosen ? 'true' : undefined}
                  data-region-class={difference.region_class}
                  onClick={() => onSelect(index)}
                >
                  <span className={styles.itemClass}>{regionClassLabel(difference.region_class)}</span>
                  <BeforeAfter before={difference.before_text} after={difference.after_text} />
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
