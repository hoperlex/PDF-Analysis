/**
 * Which model a waiting run waits for, and why, in one line (`HOSTS-L1`, `D-660`; over `RunStatus.wait_cells`, contract 1.48.0).
 *
 * A run started on the stage layout waits when a cell of its plan has no server to take it (`wait_reason` `model_unavailable` or
 * `executor_at_capacity`); the reason alone does not say which model is missing. While such a run is `queued`, the server names the
 * cells that cannot be bound now, each with the model of the plan, the access and a cause from a closed set. This module turns them into
 * the words of the run page:
 *
 *   «Ждём gpt-6-sol: нет сервера с этой моделью; gpt-6-astra: все места сервера заняты; и ещё 2»
 *
 * - **One line, no control.** The cells are grouped by model (a model that waits in several cells, or by both accesses, is named once);
 *   at most `WAIT_MODELS_SHOWN` models are named and the rest are counted.
 * - **The cause of a model** is the most actionable one of its cells, in the order of the contract's `RunWaitCause`: a model that has a
 *   cell on no server and another on a full server is named for the first, because waiting does not mend it.
 * - **A cause this table does not know** (a word the contract gains later) draws nothing, so the screen keeps the sentence it has rather
 *   than guess one; so does a run that is not `queued`, and a reading without cells.
 * - It names a model and a cause and **never a server**: which server serves a model is the administrator's, not the reader's.
 */

import type { RunStatus, RunWaitCause } from '@/shared/api';
import { RUN_WAIT_CAUSE_VALUES } from '@/shared/api';

/** The words of each cause; a `Record` over the contract's own set, so a new value is a type error here. */
export const WAIT_CAUSE_LABELS: Readonly<Record<RunWaitCause, string>> = {
  host_disabled: 'сервер выключен',
  host_offline: 'сервер не на связи',
  login_required: 'на сервере нужно войти в клиент',
  model_not_verified: 'сервер ещё не подтвердил модель',
  model_cooling_down: 'сервер временно снял модель',
  not_on_any_server: 'нет сервера с этой моделью',
  at_capacity: 'все места сервера заняты',
  vector_window: 'идёт ночное окно векторов',
};

/** How many models the line names before it counts the rest. */
export const WAIT_MODELS_SHOWN = 2;

export interface RunWaitModel {
  /** The model of the plan, as the plan names it. */
  readonly model: string;
  readonly cause: RunWaitCause;
  /** The cause in words. */
  readonly text: string;
}

export interface RunWaitCellsLine {
  /** The models named, in the order of the plan, at most `WAIT_MODELS_SHOWN`. */
  readonly models: readonly RunWaitModel[];
  /** How many more models wait and are not named. */
  readonly more: number;
}

/** A cause this screen knows the word for, or `null` for a value it does not know. */
export function knownWaitCause(cause: string | null | undefined): RunWaitCause | null {
  if (cause === undefined || cause === null) return null;
  return (RUN_WAIT_CAUSE_VALUES as readonly string[]).includes(cause) ? (cause as RunWaitCause) : null;
}

const rank = (cause: RunWaitCause): number => (RUN_WAIT_CAUSE_VALUES as readonly string[]).indexOf(cause);

/** The line of a queued run's waiting cells, or `null` when the run is not queued or the reading names none this screen knows. */
export function runWaitCellsLine(run: Pick<RunStatus, 'state' | 'wait_cells'>): RunWaitCellsLine | null {
  if (run.state !== 'queued' || run.wait_cells === undefined) return null;
  const byModel = new Map<string, RunWaitCause>();
  for (const cell of run.wait_cells) {
    const cause = knownWaitCause(cell.cause);
    if (cause === null || cell.model_id.trim() === '') continue;
    const had = byModel.get(cell.model_id);
    if (had === undefined || rank(cause) < rank(had)) byModel.set(cell.model_id, cause);
  }
  if (byModel.size === 0) return null;
  const all = [...byModel].map(([model, cause]): RunWaitModel => ({ model, cause, text: WAIT_CAUSE_LABELS[cause] }));
  return { models: all.slice(0, WAIT_MODELS_SHOWN), more: Math.max(0, all.length - WAIT_MODELS_SHOWN) };
}

/** «Ждём gpt-6-sol: нет сервера с этой моделью; gpt-6-astra: все места сервера заняты; и ещё 2» — the line as one sentence. */
export function runWaitCellsSentence(line: RunWaitCellsLine): string {
  const named = line.models.map((item) => `${item.model}: ${item.text}`).join('; ');
  return `Ждём ${named}${line.more > 0 ? `; и ещё ${line.more}` : ''}`;
}
