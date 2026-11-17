'use client';

/**
 * Where several files dropped on the single form's field go (`UIP-S22-03`): to «Несколько файлов», which opens to show them.
 *
 * The state is the drop (each drop a new `id`, so the same files dropped twice are a new choice) and whether that disclosure is
 * open. A drop opens it; the reader's own opening and closing is kept in step through `onToggle`. The widget that draws the two
 * forms side by side holds no state of its own: it passes these to both.
 */

import { useState } from 'react';

import type { DroppedFiles } from './drop-files';

export interface DropToMany {
  /** The latest drop of several files; `undefined` until there is one. */
  readonly dropped: DroppedFiles | undefined;
  /** «Несколько файлов» is open. */
  readonly open: boolean;
  /** Several files were dropped on the single field. */
  readonly onDropMany: (files: readonly File[]) => void;
  /** The reader opened or closed «Несколько файлов» by hand. */
  readonly onToggle: (open: boolean) => void;
}

export function useDropToMany(): DropToMany {
  const [dropped, setDropped] = useState<DroppedFiles | undefined>(undefined);
  const [open, setOpen] = useState(false);
  return {
    dropped,
    open,
    onDropMany: (files) => {
      setDropped((last) => ({ id: (last?.id ?? 0) + 1, files }));
      setOpen(true);
    },
    onToggle: setOpen,
  };
}
