/**
 * What a drop on the upload field hands over (`UIP-S22-03`).
 *
 * Pure: the browser's `DataTransfer` is read through the small shapes below, so the rule is the same for the real object and
 * for the stand-in a unit test builds. A drop may carry files, folders or both; only files are taken. A folder is told from a
 * file by `webkitGetAsEntry()`, which a browser answers only while the drop event is being handled, so the reading is done in
 * the handler and never later.
 */

/** One entry of a drop, as `DataTransferItem` shows it. */
export interface DroppedItem {
  readonly kind: string;
  getAsFile(): File | null;
  webkitGetAsEntry?(): { readonly isDirectory: boolean } | null;
}

/** The part of `DataTransfer` this rule reads. */
export interface DropTransfer {
  readonly types: readonly string[];
  readonly files: ArrayLike<File>;
  readonly items?: ArrayLike<DroppedItem> | undefined;
}

export interface DroppedFiles {
  /** Which drop this is: a second drop of the same files is still a new choice. */
  readonly id: number;
  readonly files: readonly File[];
}

/** What one drop gives: the files taken, and how many folders were left. */
export interface DropContents {
  readonly files: readonly File[];
  readonly folders: number;
}

/** Whether the drag carries files at all: a dragged piece of text is none of this field's business. */
export function carriesFiles(transfer: Pick<DropTransfer, 'types'>): boolean {
  return Array.from(transfer.types).includes('Files');
}

/**
 * The files of a drop and the number of folders that came with them. A folder is not taken: the unit of this product is a
 * portal ZIP, and a folder would need compressing in the browser. When the browser shows no item list (an old one), the plain
 * file list is read, and a folder in it meets the same browser checks as any other file that is not a ZIP.
 */
export function filesOfDrop(transfer: DropTransfer): DropContents {
  const items = Array.from(transfer.items ?? []).filter((item) => item.kind === 'file');
  if (items.length === 0) return { files: Array.from(transfer.files), folders: 0 };
  const files: File[] = [];
  let folders = 0;
  for (const item of items) {
    if (item.webkitGetAsEntry?.()?.isDirectory === true) {
      folders += 1;
      continue;
    }
    const file = item.getAsFile();
    if (file !== null) files.push(file);
  }
  return { files, folders };
}

/**
 * After a drop of one file, make the native field say what the form holds. A browser that cannot set a field's files leaves the
 * field as it was; the line «Выбран файл» under it names the file either way, and the form sends what it holds, not what the
 * field shows.
 */
export function showChosen(input: { files: FileList | null } | null, file: File): void {
  if (input === null || typeof DataTransfer === 'undefined') return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  input.files = transfer.files;
}
