/**
 * The files a reader picks for a comparison upload, and what is said about them before anything is sent
 * (`frontend/static/js/version-comparison.js:435-502`, `version-comparison-batch.js:9-22`).
 *
 * Only PDFs go (`Q-CMP-5`: a plain PDF is admitted for comparison; a ZIP of a whole stage is the reader of a later
 * wave), and the name a file carries is a **hint** for the grouping proposal, never an identity: the declared name is
 * the relative path the browser reports (`webkitRelativePath`), cut to the contract's 255 characters. The limits are
 * ADR-0025 decisions 9 and 10 and the PDF envelope's 250 MiB; the server refuses all of them with a typed reason, and
 * this check only spares a reader the wait.
 */

export const PART_SIZE_BYTES = 16 * 1024 * 1024;
export const MAX_FILES = 10_000;
export const MAX_SETS = 100;
export const MAX_FILE_BYTES = 250 * 1024 * 1024;
export const MAX_BATCH_BYTES = 8 * 1024 * 1024 * 1024;
export const MAX_NAME_LENGTH = 255;

/** One picked PDF and the project folder it was picked as part of (a hint for the reader, not sent as an identity). */
export interface PickedFile {
  readonly file: File;
  /** The relative path the browser reports, or the bare name for a file picked alone. */
  readonly path: string;
  /** The folder the reader added it with; `''` for a file picked alone. */
  readonly group: string;
}

export function isPdfName(name: string): boolean {
  return name.toLowerCase().endsWith('.pdf');
}

function relativePathOf(file: File): string {
  const relative = (file as File & { readonly webkitRelativePath?: string }).webkitRelativePath;
  return relative !== undefined && relative !== '' ? relative : file.name;
}

/** The name declared for a file: its path, and when that is too long, its tail (the end is what tells files apart). */
export function declaredName(path: string): string {
  return path.length <= MAX_NAME_LENGTH ? path : path.slice(path.length - MAX_NAME_LENGTH);
}

export type FolderMode = 'one' | 'many';

/**
 * The project a file belongs to when a folder is added: with «Добавить папку» the folder itself; with «Добавить папку
 * с проектами» each subfolder of it. A file that lies directly in the folder belongs to the folder.
 */
export function groupOf(path: string, mode: FolderMode): string {
  const parts = path.split('/');
  if (parts.length <= 1) return '';
  const folders = parts.slice(0, -1);
  if (mode === 'one') return folders.join('/');
  return folders.length >= 2 ? folders.slice(0, 2).join('/') : (folders[0] ?? '');
}

export interface Picked {
  readonly files: readonly PickedFile[];
  /** Files that are not PDFs and were left out. */
  readonly skipped: number;
}

export function pickFiles(list: Iterable<File>, mode: FolderMode | 'files'): Picked {
  const files: PickedFile[] = [];
  let skipped = 0;
  for (const file of list) {
    if (!isPdfName(file.name)) {
      skipped += 1;
      continue;
    }
    const path = relativePathOf(file);
    files.push({ file, path, group: mode === 'files' ? '' : groupOf(path, mode) });
  }
  return { files, skipped };
}

export interface Group {
  readonly group: string;
  readonly files: readonly PickedFile[];
  readonly bytes: number;
}

/** The picked files by the folder they were added with, in the order of first appearance. */
export function groupsOf(files: readonly PickedFile[]): Group[] {
  const by = new Map<string, PickedFile[]>();
  for (const picked of files) by.set(picked.group, [...(by.get(picked.group) ?? []), picked]);
  return [...by].map(([group, members]) => ({
    group,
    files: members,
    bytes: members.reduce((sum, member) => sum + member.file.size, 0),
  }));
}

export function formatMebibytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(bytes >= 10 * 1024 * 1024 ? 0 : 1)} МБ`;
}

export type PrecheckProblem = 'nothing' | 'too_many_files' | 'too_many_projects' | 'file_too_large' | 'empty_file' | 'batch_too_large';

export const PRECHECK_SENTENCES: Readonly<Record<PrecheckProblem, string>> = {
  nothing: 'Выберите папку с PDF или отдельные файлы.',
  too_many_files: 'Файлов больше 10 000. Разделите загрузку.',
  too_many_projects: 'Папок-проектов больше 100. Разделите загрузку.',
  file_too_large: 'Один из файлов больше 250 МиБ: так много система не принимает.',
  empty_file: 'Один из файлов пуст.',
  batch_too_large: 'Вместе файлы больше 8 ГиБ. Разделите загрузку.',
};

/** What a browser can honestly know before sending: counts and sizes; the server checks the rest. */
export function precheck(files: readonly PickedFile[]): PrecheckProblem | null {
  if (files.length === 0) return 'nothing';
  if (files.length > MAX_FILES) return 'too_many_files';
  if (groupsOf(files).length > MAX_SETS) return 'too_many_projects';
  if (files.some((picked) => picked.file.size === 0)) return 'empty_file';
  if (files.some((picked) => picked.file.size > MAX_FILE_BYTES)) return 'file_too_large';
  if (files.reduce((sum, picked) => sum + picked.file.size, 0) > MAX_BATCH_BYTES) return 'batch_too_large';
  return null;
}

/** The number of parts a file of this size is sent in (`ceil(size / part)`, at least one). */
export function partCount(sizeBytes: number, partSize: number = PART_SIZE_BYTES): number {
  return Math.max(1, Math.ceil(sizeBytes / partSize));
}
