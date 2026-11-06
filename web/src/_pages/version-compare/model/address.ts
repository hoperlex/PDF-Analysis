/**
 * What «Сравнение версий» keeps in its address (`UI-B-102`, `R-150c`): the document set that is open and the tab. The
 * original remembered both in `localStorage` (`version-comparison:view|project`); the address replaces it, so a reload, a
 * pasted link and Back/Forward all open the same screen. The project is `?project=` (written by the header and by the
 * chooser) and is not touched here; `set` and `tab` are the two parameters of `PROJECT_DEPENDENT_PARAMS` this screen uses.
 *
 * Pure: a query string in, a query string out. Whether a set belongs to the project is the screen's question, answered once the
 * overview has loaded.
 */

import { isCompareTab } from './tabs';
import type { CompareTab } from './tabs';

export const SET_PARAM = 'set';
export const TAB_PARAM = 'tab';

export interface CompareAddress {
  /** The open document set, or `null` when the table is the only thing open. */
  readonly documentUid: string | null;
  readonly tab: CompareTab;
}

type Params = Pick<URLSearchParams, 'get' | 'toString'>;

/** `tab=sheets` means nothing without a set; an unknown tab is the table, as an absent one. */
export function readCompareAddress(params: Params): CompareAddress {
  const set = params.get(SET_PARAM);
  const documentUid = set === null || set === '' ? null : set;
  const tab = params.get(TAB_PARAM);
  return { documentUid, tab: documentUid !== null && isCompareTab(tab) ? tab : 'projects' };
}

/** The query after the reader opens a set or a tab. `documentUid: null` closes the set; the table is the absent `tab`. */
export function writeCompareAddress(params: Params, next: CompareAddress): URLSearchParams {
  const written = new URLSearchParams(params.toString());
  if (next.documentUid === null) written.delete(SET_PARAM);
  else written.set(SET_PARAM, next.documentUid);
  if (next.documentUid === null || next.tab === 'projects') written.delete(TAB_PARAM);
  else written.set(TAB_PARAM, next.tab);
  return written;
}
