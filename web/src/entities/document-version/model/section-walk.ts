/**
 * The documents of one section, walked page after page (`UI-A-28`).
 *
 * The section page (`R-151l`) lists the documents whose current version an expert confirmed for the section, in
 * the server's `order=audit` (`UI-A-49`), and draws one page of them. A document page that says «N из M» has to
 * know the whole listing, so it follows the cursor to its end. This module is the pure half: given the cursors a
 * reader holds and the pages read under them, which cursor comes next, whether the end was reached, and where one
 * document stands. It reads nothing and orders nothing: the order is the server's, the same one the section page
 * shows, and a document's place is its index in that listing.
 *
 * **No silent cap.** The walk stops only when the server says there is no next cursor. A cursor the walk has
 * already used would loop for ever, so it is reported as a fault of the listing and never followed twice.
 */

import type { DocumentVersion, DocumentVersionPage } from '@/shared/api';

/** What the walk knows after the pages it holds. */
export type SectionWalkStep =
  /** The next page to read is under `cursors.at(-1)`; `items` are the pages read so far. */
  | { readonly kind: 'reading'; readonly cursors: readonly (string | undefined)[]; readonly items: readonly DocumentVersion[] }
  /** The server said there is no next cursor: `items` is the whole section, in the server's order. */
  | { readonly kind: 'complete'; readonly cursors: readonly (string | undefined)[]; readonly items: readonly DocumentVersion[] }
  /** The listing sent a cursor the walk had already followed. A defect of the listing, never a page to retry. */
  | { readonly kind: 'cycle'; readonly cursors: readonly (string | undefined)[] };

/**
 * Advances the walk as far as the pages in hand allow.
 *
 * `held` are the cursors a reader asked under, in order, starting at `undefined` (the first page); `pages[i]` is
 * the answer under `held[i]`, or `undefined` while it is not read. A page counts only while the cursor it was read
 * under is the one the previous page named, so a first page that changed after a refetch cannot leave a stale chain
 * behind: the walk returns the cursors it should now hold, and the reader adopts them.
 */
export function advanceSectionWalk(
  held: readonly (string | undefined)[],
  pages: readonly (DocumentVersionPage | undefined)[],
): SectionWalkStep {
  const cursors: (string | undefined)[] = [undefined];
  const items: DocumentVersion[] = [];
  for (let index = 0; ; index += 1) {
    const page = held[index] === cursors[index] ? pages[index] : undefined;
    if (page === undefined) return { kind: 'reading', cursors, items };
    items.push(...page.items);
    const next = page.page.next_cursor;
    if (next === null) return { kind: 'complete', cursors, items };
    if (cursors.includes(next)) return { kind: 'cycle', cursors };
    cursors.push(next);
  }
}

/** Where one document stands among the documents of its section. */
export interface SectionPosition {
  /** 1-based, the n of «n из m». */
  readonly position: number;
  /** How many documents the section holds. */
  readonly total: number;
  readonly previous: DocumentVersion | null;
  readonly next: DocumentVersion | null;
}

/**
 * The place of `documentUid` in the section's whole listing, or `null` when that document is not in it (an
 * archived one, or one whose current version is not confirmed for this section): then there is no true «n из m»
 * to say, and the screen says none.
 */
export function sectionPosition(items: readonly DocumentVersion[], documentUid: string): SectionPosition | null {
  const index = items.findIndex((item) => item.document_uid === documentUid);
  if (index < 0) return null;
  return {
    position: index + 1,
    total: items.length,
    previous: items[index - 1] ?? null,
    next: items[index + 1] ?? null,
  };
}
