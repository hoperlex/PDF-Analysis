/**
 * The run-state badge.
 *
 * Its value set is exactly the contract's `RunState`: `created`, `queued`, `running`,
 * `validating`, `published`, `partial`, `failed`, `cancelled`. The success terminal is
 * `published`.
 *
 * `succeeded` is **not** in this set and cannot be. It is a `StageResult` status on a
 * different aggregate, and it is legal on a stage row and illegal on a run badge — see
 * `StageStatusBadge` below it in this directory and section 3 of the UI seam document.
 * The type system enforces the split: `RunState` is generated from the contract enum, so
 * passing `'succeeded'` here does not compile.
 *
 * Only contract state names are rendered. No slice invents "in progress", "done" or "OK".
 */

import type { RunState } from '@/shared/api';
import { assertNever } from '@/shared/lib';

/** Presentation tone per contract state. Nothing here renames a state. */
function toneFor(state: RunState): string {
  switch (state) {
    case 'created':
    case 'queued':
      return 'pending';
    case 'running':
    case 'validating':
      return 'active';
    case 'published':
      return 'ok';
    case 'partial':
      return 'degraded';
    case 'failed':
      return 'failed';
    case 'cancelled':
      return 'inert';
    default:
      return assertNever(state, 'RunStateBadge');
  }
}

export interface RunStateBadgeProps {
  readonly state: RunState;
  /**
   * `provider_mode` from the run. A recorded run is not evidence of a live one, so the
   * badge carries it rather than leaving it to a caption somewhere else on the page.
   */
  readonly providerMode?: 'live' | 'recorded' | undefined;
}

/**
 * The Russian label for each contract state.
 *
 * The owner ruled by direct poll on 2026-09-21 that every value a reviewer can read is
 * shown in Russian. This is **not** the rename this file's header forbids: the contract
 * value stays intact in `data-run-state`, which is what `PA-01` criterion 4 was re-driven
 * against by `W30-CERT3`, and what the browser journey reads. A label is not an identity.
 *
 * Keyed on `RunState`, so a state added to the contract fails to compile until it is
 * given a label rather than silently rendering its own identifier.
 */
/**
 * Exported for the same reason `VERDICT_LABELS` was: a private table is one the next
 * consumer renders around. `run-progress` printed `<code>{status.state}</code>` in three
 * places of explanatory prose, so a reviewer read a Russian sentence ending in `published`.
 */
export const STATE_LABELS: Readonly<Record<RunState, string>> = {
  created: 'создан',
  queued: 'в очереди',
  running: 'выполняется',
  validating: 'проверяется',
  published: 'опубликован',
  partial: 'частично',
  failed: 'отказ',
  cancelled: 'отменён',
};

/*
 * Exported, and it is the FOURTH label map in this tree to need exporting after a second
 * consumer rendered around it. `run-progress` printed `live` twice as a bare contract value
 * beside a badge that already said `живой вызов` — found by photographing the run screen in
 * a browser, not by any test.
 */
export const PROVIDER_MODE_LABELS: Readonly<Record<'live' | 'recorded', string>> = {
  live: 'живой вызов',
  recorded: 'из записи',
};

export function RunStateBadge({ state, providerMode }: RunStateBadgeProps) {
  return (
    <span className={`am-badge am-badge--${toneFor(state)}`} data-run-state={state}>
      <span className="am-badge__label">{STATE_LABELS[state]}</span>
      {providerMode !== undefined ? (
        <span className="am-badge__qualifier" data-provider-mode={providerMode}>
          {PROVIDER_MODE_LABELS[providerMode]}
        </span>
      ) : null}
    </span>
  );
}

/**
 * The third provider-mode value a screen can show. `providerModeLabel()` narrows anything
 * unrecognised to `unknown`, which is itself a Latin word that reached the reviewer -- so it
 * needs a label exactly as the two contract values do.
 */
export const PROVIDER_MODE_UNKNOWN_LABEL = 'не сообщён';

/** The Russian label for a cost basis, for the same reason and found the same way. */
export const COST_BASIS_LABELS: Readonly<Record<'measured' | 'estimated', string>> = {
  measured: 'измерено',
  estimated: 'оценено',
};
