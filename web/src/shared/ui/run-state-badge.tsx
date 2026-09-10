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

export function RunStateBadge({ state, providerMode }: RunStateBadgeProps) {
  return (
    <span className={`am-badge am-badge--${toneFor(state)}`} data-run-state={state}>
      <span className="am-badge__label">{state}</span>
      {providerMode !== undefined ? (
        <span className="am-badge__qualifier" data-provider-mode={providerMode}>
          {providerMode}
        </span>
      ) : null}
    </span>
  );
}
