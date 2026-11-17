'use client';

/** @jsxRuntime automatic */

/**
 * The verdict mark (`UIP-S06-01`): ✓ green, ✕ red, a dash where nothing is decided.
 *
 * The one-glyph form of a verdict, for a cell or a line that has no room for `VerdictBadge`'s words (the decision column of a
 * table, the verdict of an event in a list). The glyph is the sight; the accessible name is the word, «Принято» or «Отклонено»
 * (`role="img"` with `aria-label`, and the same word as a tooltip), so colour is never the only carrier of the verdict.
 *
 * Same discipline as `VerdictBadge`: the value set is the generated `Verdict`, the words come from `VERDICT_LABELS`, the contract
 * value stays on `data-verdict` and is not rendered as prose, and a value outside the closed union is shown as a fault instead of
 * as a dash. `pending` and `needs_manual_review` are both a dash: neither is a decision. They differ in the name.
 *
 * `'use client'`, like `VerdictBadge`: the words are read from the badge's module, which is a client module, so a server
 * component importing this one would otherwise get a reference where `VERDICT_LABELS` should be.
 */

import type { Verdict } from '@/shared/api';
import { VERDICT_VALUES } from '@/shared/api';

import styles from './verdict-mark.module.css';
import { VERDICT_LABELS } from './verdict-badge';

export interface VerdictMarkProps {
  readonly verdict: Verdict;
}

/** «принято» as «Принято»: the name of the mark is the sentence-initial form of the label the badge already has. */
function nameOf(verdict: Verdict): string {
  const label = VERDICT_LABELS[verdict];
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`;
}

export function VerdictMark({ verdict }: VerdictMarkProps) {
  if (!(VERDICT_VALUES as readonly unknown[]).includes(verdict)) {
    return (
      <span className={styles.fault} role="alert" data-closed-vocabulary-fault="verdict">
        Неизвестный вердикт
      </span>
    );
  }
  const name = nameOf(verdict);
  const tone = verdict === 'accepted' ? styles.accepted : verdict === 'rejected' ? styles.rejected : styles.undecided;
  const glyph = verdict === 'accepted' ? '✓' : verdict === 'rejected' ? '✕' : '—';
  return (
    <span className={`${styles.mark} ${tone}`} role="img" aria-label={name} title={name} data-verdict={verdict}>
      {glyph}
    </span>
  );
}
