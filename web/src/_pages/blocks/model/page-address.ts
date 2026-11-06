/**
 * The page chosen above the tiles of «Блоки», in the address of the version's tab.
 *
 * `?page=N` (a PDF page number) or `?page=all`. Reading is `pageSelectionOf` (`entities/block`), which
 * takes an absent or unreadable value for «Все блоки»; writing is here: the same query with only `page`
 * set, every other parameter kept, so a reload or a pasted link opens the same page. Pure, so the
 * address a press writes is a string a test compares and not a browser history only a browser shows.
 */

import type { PageSelection } from '@/entities/block';
import { pageSelectionParam } from '@/entities/block';

/** The path and query the address holds after `selection` is chosen; `search` is the current query string. */
export function addressWithPage(pathname: string, search: string, selection: PageSelection): string {
  const params = new URLSearchParams(search);
  params.set('page', pageSelectionParam(selection));
  return `${pathname}?${params.toString()}`;
}
