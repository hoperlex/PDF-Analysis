'use client';

/**
 * The dispatcher's reads (`W61-DISPATCHER-01`): a page of `listAssignments` and one
 * `getAssignment` with its history, under `queryKeys.assignments`.
 *
 * The server decides what a viewer reads: an administrator every assignment, an expert only
 * the ones currently given to them. Nothing here filters by role; a filter the server did
 * not apply would be a second, weaker rule.
 */

import { useQuery } from '@tanstack/react-query';

import type { AssignmentDetail, AssignmentListFilters, AssignmentPage } from '@/shared/api';
import { getAssignment, listAssignments, queryKeys } from '@/shared/api';

/** One page of the dispatcher's list. */
export const ASSIGNMENT_PAGE_LIMIT = 50;

export function useAssignments(filters: AssignmentListFilters) {
  return useQuery<AssignmentPage>({
    queryKey: queryKeys.assignments.list(filters),
    queryFn: async () => (await listAssignments({ query: filters })).data,
  });
}

export function useAssignment(assignmentUid: string, enabled = true) {
  return useQuery<AssignmentDetail>({
    queryKey: queryKeys.assignments.detail(assignmentUid),
    queryFn: async () => (await getAssignment({ path: { assignment_uid: assignmentUid } })).data,
    enabled,
  });
}
