'use client';

/** @jsxRuntime automatic */

/**
 * The rail of chips (`RUN-SCREEN-01a`, plan §9.2): one button per phase of this run, drawn from `runChips`.
 *
 * A chip is not drawn when the run does not have it. Each shows its short name, its state in a word as well as a colour, the time it
 * took where the reading has both ends («из прогона» for a chip taken from the run this one was started from), and — on a chip that
 * calls a model — **one** short line, the model. Token figures are not drawn on the rail: they are in the window a click opens, «Этапы
 * анализа раздела», on that chip.
 *
 * The model line says what the stages of the run state (`getRunStages`, `RUN-STAGES-WEB-01`): the short name when every cell of the
 * chip is on one model, «2 модели» for an ensemble (the names are the tooltip), and nothing for a chip with no model cell. Until
 * the stages are read the line is what it was, the run's own model, so the rail is never blank while it waits for them.
 */

import { CHIP_STATE_LABELS, chipModelLine, formatElapsed, stageOfChip } from '@/entities/audit-run';
import type { RunChip, RunChipId } from '@/entities/audit-run';
import type { RunStages } from '@/shared/api';

import styles from './run-progress.module.css';

export interface RunRailProps {
  readonly chips: readonly RunChip[];
  /** The run's model, short and full, for the chips that call one; `null` when the reading names none. */
  readonly model: { readonly short: string; readonly pin: string } | null;
  /** The stages read for the run; absent until they are, and then the line is the run's model. */
  readonly stages?: RunStages | undefined;
  readonly onOpen: (chip: RunChipId) => void;
}

/** The model shows on a chip that calls one and has not been ruled out. */
function showsModel(chip: RunChip): boolean {
  return chip.definition.callsModel && chip.state !== 'skipped' && chip.state !== 'unavailable';
}

/** The line under a chip's name: its own models once the stages are read, the run's model before. */
function modelLine(chip: RunChip, model: RunRailProps['model'], stages: RunStages | undefined): { text: string; title: string } | null {
  if (!showsModel(chip)) return null;
  if (stages === undefined) return model === null ? null : { text: model.short, title: model.pin };
  return chipModelLine(stageOfChip(stages, chip.definition.id));
}

export function RunRail({ chips, model, stages, onOpen }: RunRailProps) {
  if (chips.length === 0) return null;
  return (
    <ol className={styles.rail} aria-label="Этапы этого прогона" data-run-rail="">
      {chips.map((chip) => {
        const id = chip.definition.id;
        const took = chip.reused ? 'из прогона' : chip.elapsedMs === null ? null : formatElapsed(chip.elapsedMs);
        const line = modelLine(chip, model, stages);
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
              {line === null ? null : <span className={styles.chipModel} title={line.title} data-chip-model="">{line.text}</span>}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
