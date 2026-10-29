/**
 * The reader's final word on one proposed set, and the request that carries it
 * (`confirmComparisonUploadSet`, `CMP-INGEST-01` section 2.4).
 *
 * The reader proposes grouping, order, labels, stage and section; the user confirms or changes them; nothing is
 * admitted as a version until a set is confirmed. The request lists **exactly the set's own files** in the order the
 * reader chose (the array order is the version order); a file cannot move to another set here, because the
 * confirmation refuses a member of another set (`comparison_set_members`) — to regroup, upload again. The stage and the
 * section go together or not at all (`required_together`). An existing document is offered, never applied for the
 * reader: «Добавить версии в «…»» is a choice.
 */

import type { ComparisonProposalSet, ConfirmComparisonUploadSetRequest, DocumentUid } from '@/shared/api';

export interface DraftFile {
  readonly fileId: string;
  readonly label: string;
}

export interface SetDraft {
  readonly designation: string;
  /** Whether the versions are added to the existing document the reader offered. */
  readonly addToExisting: boolean;
  readonly files: readonly DraftFile[];
  /** Whether the proposed stage and section are confirmed with the set. */
  readonly confirmClassification: boolean;
}

/** The files of a proposal in its own order. */
export function proposedFiles(set: ComparisonProposalSet): DraftFile[] {
  return [...set.files]
    .sort((a, b) => a.position - b.position)
    .map((file) => ({ fileId: file.file_id, label: file.version_label ?? '' }));
}

export function draftOf(set: ComparisonProposalSet): SetDraft {
  return {
    designation: set.designation ?? '',
    addToExisting: false,
    files: proposedFiles(set),
    confirmClassification: set.project_stage !== undefined && set.section_code !== undefined,
  };
}

/** Move the file at `index` one place up (`-1`) or down (`+1`). */
export function moveFile(draft: SetDraft, index: number, direction: -1 | 1): SetDraft {
  const target = index + direction;
  if (index < 0 || index >= draft.files.length || target < 0 || target >= draft.files.length) return draft;
  const files = [...draft.files];
  const moved = files[index] as DraftFile;
  files[index] = files[target] as DraftFile;
  files[target] = moved;
  return { ...draft, files };
}

export function relabel(draft: SetDraft, index: number, label: string): SetDraft {
  return { ...draft, files: draft.files.map((file, position) => (position === index ? { ...file, label } : file)) };
}

/** The request of one confirmation. */
export function confirmationOf(set: ComparisonProposalSet, draft: SetDraft): ConfirmComparisonUploadSetRequest {
  const designation = draft.designation.trim();
  const classify = draft.confirmClassification && set.project_stage !== undefined && set.section_code !== undefined;
  return {
    files: draft.files.map((file) => {
      const label = file.label.trim();
      return label === '' ? { file_id: file.fileId } : { file_id: file.fileId, version_label: label };
    }),
    ...(designation === '' ? {} : { designation }),
    ...(draft.addToExisting && set.existing_document_uid !== undefined
      ? { existing_document_uid: set.existing_document_uid as DocumentUid }
      : {}),
    ...(classify ? { project_stage: set.project_stage, section_code: set.section_code } : {}),
  } as ConfirmComparisonUploadSetRequest;
}

/** «Подтвердить порядок во всех проектах»: every set as the reader proposed it, with the proposed stage and section. */
export function proposedConfirmation(set: ComparisonProposalSet): ConfirmComparisonUploadSetRequest {
  return confirmationOf(set, draftOf(set));
}

/** The sets «Подтвердить порядок во всех проектах» acts on: those waiting for the reader's word. */
export function awaitingConfirmation(sets: readonly ComparisonProposalSet[]): ComparisonProposalSet[] {
  return sets.filter((set) => set.state === 'needs_confirmation');
}
