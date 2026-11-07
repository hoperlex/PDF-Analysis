import type { Assignment } from '@/shared/api';

function normal(value: string | null | undefined): string {
  return (value ?? '').toLocaleLowerCase('ru-RU');
}

/**
 * The assignments of one page that contain every word of `text`, in any case and order, in the project, the document, the
 * expert's or the assigning administrator's label, the note or the reason. The server filters by status, project and
 * «Только мои» (those are the chips and the header); this narrows the page already read and the screen says so.
 */
export function filterAssignments(items: readonly Assignment[], text: string): readonly Assignment[] {
  const words = normal(text).split(/\s+/).filter((word) => word !== '');
  if (words.length === 0) return items;
  return items.filter((assignment) => {
    const haystack = [
      assignment.project_name,
      assignment.document_title,
      assignment.assignee_label,
      assignment.created_by_label,
      assignment.note,
      assignment.status_reason,
    ].map(normal).join(' ');
    return words.every((word) => haystack.includes(word));
  });
}
