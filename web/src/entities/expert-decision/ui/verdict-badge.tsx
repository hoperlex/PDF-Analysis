'use client';

/** @jsxRuntime automatic */

/**
 * The verdict badge.
 *
 * `shared/ui` freezes a badge for `RunState` and one for `StageStatus`; there is no
 * `Verdict` badge there, so it lives here with the entity that owns the vocabulary. Same
 * discipline as those two: the value set is exactly the generated `Verdict`, only contract
 * names are rendered, and nothing invents "approved", "OK" or "undecided".
 *
 * `needs_manual_review` is in the closed union and has no PC-01 producer
 * (`P02_SEAMS.md` §5.4). It is still rendered rather than omitted — a value the server can
 * legally return must have a display, and a badge that silently renders nothing for a
 * legal value is how a UI shows a blank where a verdict should be.
 */

import type { Verdict } from '@/shared/api';
import { assertNever } from '@/shared/lib';

function toneFor(verdict: Verdict): string {
  switch (verdict) {
    case 'pending':
      return 'pending';
    case 'accepted':
      return 'ok';
    case 'rejected':
      return 'failed';
    case 'needs_manual_review':
      return 'degraded';
    default:
      return assertNever(verdict, 'VerdictBadge');
  }
}

export interface VerdictBadgeProps {
  readonly verdict: Verdict;
}

/** Russian labels. The contract value stays in `data-verdict`; see `RunStateBadge`. */
const VERDICT_LABELS: Readonly<Record<Verdict, string>> = {
  pending: 'не решено',
  accepted: 'принято',
  rejected: 'отклонено',
  needs_manual_review: 'нужен ручной разбор',
};

export function VerdictBadge({ verdict }: VerdictBadgeProps) {
  return (
    <span className={`am-badge am-badge--${toneFor(verdict)}`} data-verdict={verdict}>
      <span className="am-badge__label">{VERDICT_LABELS[verdict]}</span>
    </span>
  );
}
