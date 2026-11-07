/** @jsxRuntime automatic */

/**
 * `UI-A-73`: the mark of a decision an expert carried over from an earlier version, «↩ Перенесено из V2».
 *
 * It renders nothing for a decision made directly, so a caller passes whatever the contract serves
 * (`carried_from`, `current_verdict_carried_from`) without a branch of its own. The ordinal in the text is the source
 * version's display order; the source decision, finding and version stay in the data the caller already holds.
 */

import { carriedFromMark } from '../model/carried-from';
import styles from './carried-mark.module.css';

export interface CarriedMarkProps {
  readonly carriedFrom: { readonly version_ordinal: number } | null | undefined;
}

export function CarriedMark({ carriedFrom }: CarriedMarkProps) {
  const label = carriedFromMark(carriedFrom);
  if (label === null || carriedFrom === null || carriedFrom === undefined) return null;
  return (
    <span
      className={styles.mark}
      data-carried-from={carriedFrom.version_ordinal}
      title="Решение перенесено из предыдущей версии после подтверждения экспертом"
    >
      {label}
    </span>
  );
}
