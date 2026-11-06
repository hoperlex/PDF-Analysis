/**
 * Uploading several portal bundles at once (`R-151b`).
 *
 * The original guesses from a file name («…_V2») which project a new version belongs to. Ours never does: the owner
 * ruled that each file gets an explicit target — «Новый документ» (the default) or an existing document of the
 * project, which receives the file as its next version — chosen by the expert, and that the name is not even a
 * suggestion. A file name is not an identity here.
 *
 * Pure: the shapes, the default and the intent signature. The hook (`use-upload-many.ts`) sends.
 */

import type { DocumentUid, DocumentVersion } from '@/shared/api';
import type { UploadFailure, UploadPrecheckProblem } from '@/entities/document-version';

/** Where one chosen file goes. */
export type UploadTarget = { readonly kind: 'new' } | { readonly kind: 'version'; readonly documentUid: DocumentUid };

export const NEW_DOCUMENT: UploadTarget = { kind: 'new' };

export interface ManyFile {
  /** Stable within one choice: the position in the picker, never the name. */
  readonly id: string;
  readonly file: File;
  readonly precheck: UploadPrecheckProblem | null;
  readonly target: UploadTarget;
}

export type ManyOutcome =
  | { readonly kind: 'sending' }
  | { readonly kind: 'published'; readonly version: DocumentVersion }
  | { readonly kind: 'refused'; readonly failure: UploadFailure };

/** The idempotency intent of one file: the bytes as the browser sees them, and where they go. */
export function manyFileSignature(projectUid: string, item: ManyFile): string {
  const where = item.target.kind === 'new' ? 'new' : `version:${item.target.documentUid}`;
  return `upload-many:${projectUid}:${item.id}:${item.file.name}:${item.file.size}:${item.file.lastModified}:${where}`;
}

/** The value of a target `<select>`, and back: «Новый документ» is the empty value. */
export function targetValue(target: UploadTarget): string {
  return target.kind === 'new' ? '' : target.documentUid;
}

export function targetOf(value: string): UploadTarget {
  return value === '' ? NEW_DOCUMENT : { kind: 'version', documentUid: value as DocumentUid };
}

/** The files a press of «Загрузить» sends: the ones the browser did not already refuse and not yet published. */
export function sendable(files: readonly ManyFile[], outcomes: ReadonlyMap<string, ManyOutcome>): readonly ManyFile[] {
  return files.filter((item) => item.precheck === null && outcomes.get(item.id)?.kind !== 'published');
}
