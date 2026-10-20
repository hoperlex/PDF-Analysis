/**
 * One assignment's status as a short label (`W61-DISPATCHER-01`). Presentation only.
 */

import type { AssignmentStatus } from '@/shared/api';

import { ASSIGNMENT_STATUS_LABELS } from '../model/presentation';

export interface AssignmentStatusLabelProps {
  readonly status: AssignmentStatus;
}

export function AssignmentStatusLabel({ status }: AssignmentStatusLabelProps) {
  return (
    <span className="am-badge" data-assignment-status={status}>
      {ASSIGNMENT_STATUS_LABELS[status]}
    </span>
  );
}
