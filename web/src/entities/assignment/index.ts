/** Public API of the `assignment` entity (`W61-DISPATCHER-01`). */

export { ASSIGNMENT_PAGE_LIMIT, useAssignment, useAssignments } from './api/use-assignments';
export type { AssignmentFailure } from './model/failure';
export { assignmentFailure } from './model/failure';
export {
  ASSIGNMENT_EVENT_LABELS,
  ASSIGNMENT_MOVE_LABELS,
  ASSIGNMENT_STATUS_LABELS,
  OPEN_ASSIGNMENT_STATUSES,
  assignmentScope,
  canAssignWork,
  isOpenAssignment,
  movesFor,
} from './model/presentation';
export type { AssignmentStatusLabelProps } from './ui/assignment-status';
export { AssignmentStatusLabel } from './ui/assignment-status';
