'use client';

/** @jsxRuntime automatic */

/**
 * The rail of chips (`RUN-SCREEN-01a`, plan §9.2): one button per phase of this run, drawn from `runChips`.
 *
 * A chip is not drawn when the run does not have it. Each shows its short name, its state in a word as well as a colour, the time it
 * took where the reading has both ends («из прогона» for a chip taken from the run this one was started from), and — on a chip that
 * calls a model — the short name of the run's model. Token figures are not drawn: the reading has none per phase, and a chip with no
 * figure shows none. A click opens «Этапы анализа раздела» on that chip.
 */

import { CHIP_STATE_LABELS, formatElapsed } from '@/entities/audit-run';
import type { RunChip, RunChipId } from '@/entities/audit-run';

import styles from './run-progress.module.css';

export interface RunRailProps {
  readonly chips: readonly RunChip[];
  /** The run's model, short and full, for the chips that call one; `null` when the reading names none. */
  readonly model: { readonly short: string; readonly pin: string } | null;
  readonly onOpen: (chip: RunChipId | 'ar_v3') => void;
}

/** The model shows on a chip that calls one and has not been ruled out. */
function showsModel(chip: RunChip): boolean {
  return chip.definition.callsModel && chip.state !== 'skipped' && chip.state !== 'unavailable';
}

export function RunRail({ chips, model, onOpen }: RunRailProps) {
  if (chips.length === 0) return null;
  return (
    <ol className={styles.rail} aria-label="Этапы этого прогона" data-run-rail="">
      {chips.map((chip) => {
        const id = chip.definition.id;
        const took = chip.reused ? 'из прогона' : chip.elapsedMs === null ? null : formatElapsed(chip.elapsedMs);
        return (
          <li key={id} className={styles.railItem}>
            <button
              type="button"
              className={styles.chip}
              data-run-chip={id}
              data-chip-state={chip.state}
              {...(chip.reused ? { 'data-chip-reused': '' } : {})}
              aria-haspopup="dialog"
              onClick={() => onOpen(id)}
            >
              <span className={styles.chipName}>{chip.definition.short}</span>
              <span className={styles.chipState}>{CHIP_STATE_LABELS[chip.state]}</span>
              {took === null ? null : <span className={styles.chipTook} data-chip-took={took}>{took}</span>}
              {model !== null && showsModel(chip) ? <span className={styles.chipModel} title={model.pin}>{model.short}</span> : null}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
