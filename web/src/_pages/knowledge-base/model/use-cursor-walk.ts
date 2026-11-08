/**
 * The cursors of the pages walked past, oldest first; the last one is the page on screen and an empty stack is the first page.
 *
 * The server's cursors are opaque and one-way, so «Назад» is a pop, not a computation, and a cursor belongs to the filters it was
 * issued under (the server refuses it under others). The stack is therefore held WITH the key of those filters (the project, the
 * category, the verdict): a stack whose key is not the current one is not read at all, and is dropped during the render, not in an
 * effect, so a request with the old cursor and the new filter is never made, not even for one render. That is what lets a filter
 * come from the address: a link, a reload or the header's project change alters it without this page having pressed anything.
 */

import { useState } from 'react';

export const NO_CURSORS: readonly string[] = [];

interface Walk {
  readonly key: string;
  readonly cursors: readonly string[];
}

export function useCursorWalk(key: string): readonly [readonly string[], (next: readonly string[]) => void] {
  const [walk, setWalk] = useState<Walk>({ key, cursors: NO_CURSORS });
  if (walk.key !== key) setWalk({ key, cursors: NO_CURSORS });
  const cursors = walk.key === key ? walk.cursors : NO_CURSORS;
  return [cursors, (next) => setWalk({ key, cursors: next })] as const;
}
