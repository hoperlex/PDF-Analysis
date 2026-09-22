/**
 * The stage-status element.
 *
 * A separate component from `RunStateBadge` on purpose. Its value set is exactly the
 * contract's `StageStatus`: `succeeded`, `partial`, `failed`, `skipped`.
 *
 * `succeeded` is legal here and illegal on a run badge. That is the whole reason these
 * are two components and not one with a wider union.
 */

import type { StageStatus } from '@/shared/api';
import { assertNever } from '@/shared/lib';

function toneFor(status: StageStatus): string {
  switch (status) {
    case 'succeeded':
      return 'ok';
    case 'partial':
      return 'degraded';
    case 'failed':
      return 'failed';
    case 'skipped':
      return 'inert';
    default:
      return assertNever(status, 'StageStatusBadge');
  }
}

export interface StageStatusBadgeProps {
  readonly status: StageStatus;
  /**
   * The typed reason a non-`succeeded` stage carries. A `succeeded` stage has none, and
   * passing one is a caller bug rather than something to render.
   */
  readonly errorCode?: string | null | undefined;
}

/** Russian labels. The contract value stays in `data-stage-status`; see `RunStateBadge`. */
const STAGE_STATUS_LABELS: Readonly<Record<StageStatus, string>> = {
  succeeded: 'выполнен',
  partial: 'частично',
  failed: 'отказ',
  skipped: 'пропущен',
};

export function StageStatusBadge({ status, errorCode }: StageStatusBadgeProps) {
  const reason = status === 'succeeded' ? null : (errorCode ?? null);
  return (
    <span className={`am-badge am-badge--${toneFor(status)}`} data-stage-status={status}>
      <span className="am-badge__label">{STAGE_STATUS_LABELS[status]}</span>
      {reason !== null ? <span className="am-badge__qualifier">{reason}</span> : null}
    </span>
  );
}
