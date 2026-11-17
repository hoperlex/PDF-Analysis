'use client';

/**
 * The field a portal ZIP may be dropped on (`UIP-S22-03`, `UIC-S22-07`): the picker stays, and a file dragged over its field
 * is taken as if it had been chosen there.
 *
 * What a drop may carry is decided here and nowhere else: files are taken, a folder is not (the product's unit is a ZIP), and
 * more than one file is taken only where the caller says it has a place for them (`several`). Whatever is left out is said on
 * the screen, never dropped silently. What becomes of the files is the caller's: the form runs the same browser checks on them
 * as on a picked file.
 *
 * {@link DropZoneView} is pure markup (the highlight and the note are its props); {@link DropZone} holds the drag and sends.
 */

import { useRef, useState } from 'react';
import type { DragEvent, ReactNode } from 'react';

import { carriesFiles, filesOfDrop } from '../model/drop-files';

import styles from './drop-zone.module.css';

/** Said when a drop carried a folder. */
export const FOLDER_NOT_TAKEN = 'Папку принять нельзя: бросьте ZIP-архив.';
/** Said when several files were dropped where only one fits. */
export const ONE_ARCHIVE_ONLY = 'Здесь принимается один архив.';

export type DropNote = 'folder' | 'one-only';

export interface DropZoneViewProps {
  /** A drag with files is over the field. */
  readonly over: boolean;
  /** What the last drop left out, if anything. */
  readonly note: DropNote | null;
  readonly onDragEnter?: ((event: DragEvent<HTMLDivElement>) => void) | undefined;
  readonly onDragOver?: ((event: DragEvent<HTMLDivElement>) => void) | undefined;
  readonly onDragLeave?: ((event: DragEvent<HTMLDivElement>) => void) | undefined;
  readonly onDrop?: ((event: DragEvent<HTMLDivElement>) => void) | undefined;
  readonly children?: ReactNode | undefined;
}

export function DropZoneView({ over, note, onDragEnter, onDragOver, onDragLeave, onDrop, children }: DropZoneViewProps) {
  return (
    <div
      className={over ? `${styles.zone} ${styles.over}` : styles.zone}
      data-drop-zone={over ? 'over' : ''}
      onDragEnter={onDragEnter}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {children}
      {note === null ? null : (
        <p className="am-form__problem" role="alert">{note === 'folder' ? FOLDER_NOT_TAKEN : ONE_ARCHIVE_ONLY}</p>
      )}
    </div>
  );
}

export interface DropZoneProps {
  /** The files of a drop, folders left out; never empty. */
  readonly onFiles: (files: readonly File[]) => void;
  /** More than one file fits where this goes. */
  readonly several: boolean;
  readonly children: ReactNode;
}

export function DropZone({ onFiles, several, children }: DropZoneProps) {
  const [over, setOver] = useState(false);
  const [note, setNote] = useState<DropNote | null>(null);
  // `dragleave` also fires when the pointer passes from the field onto something inside it, so the highlight follows a count of
  // what the drag has entered and not left, which is the one reading that does not flicker over a child.
  const depth = useRef(0);

  /** Say that a drop is welcome here, for a drag that carries files; a drag of anything else is left to the browser. */
  const welcome = (event: DragEvent<HTMLDivElement>): boolean => {
    if (!carriesFiles(event.dataTransfer)) return false;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
    return true;
  };

  return (
    <DropZoneView
      over={over}
      note={note}
      onDragEnter={(event) => {
        if (!welcome(event)) return;
        depth.current += 1;
        setOver(true);
      }}
      onDragOver={(event) => { welcome(event); }}
      onDragLeave={(event) => {
        if (!carriesFiles(event.dataTransfer)) return;
        depth.current = Math.max(0, depth.current - 1);
        if (depth.current === 0) setOver(false);
      }}
      onDrop={(event) => {
        if (!welcome(event)) return;
        depth.current = 0;
        setOver(false);
        const dropped = filesOfDrop(event.dataTransfer);
        if (dropped.files.length > 1 && !several) {
          setNote('one-only');
          return;
        }
        setNote(dropped.folders > 0 ? 'folder' : null);
        if (dropped.files.length > 0) onFiles(dropped.files);
      }}
    >
      {children}
    </DropZoneView>
  );
}
