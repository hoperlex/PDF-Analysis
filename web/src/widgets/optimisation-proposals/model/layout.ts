/**
 * `UI-B-06`: how a pass's proposals are laid out, and where that choice lives.
 *
 * The original lists the proposals as one dense table (ID, type, current solution, proposal, saving, risks, norm, decision, reason,
 * fifty rows to a page). Here the same proposals can be drawn two ways: as **cards** (a row of a grid, the default, which the PC-01
 * journey and the document tab were built on) or as a **table** with one header over every row. It is a way of drawing the page that
 * was read, so it changes no decision, no filter and no cache key beyond the page size the table asks for.
 *
 * The choice is in the address (`?layout=table`; «Карточки» is the absent parameter), so a link, a reload and Back/Forward keep it
 * (`R-150c`). It is a view and not a place, so choosing it REPLACES the history entry. Pure: a query string in, a query string out;
 * a parameter that is not this one is carried through and a value outside the closed set is read as the default, never echoed.
 */

export type ProposalLayout = 'cards' | 'table';

export const PROPOSAL_LAYOUT_PARAM = 'layout';

/** In the order the switch offers them. */
export const PROPOSAL_LAYOUTS: readonly ProposalLayout[] = ['cards', 'table'];

export const DEFAULT_PROPOSAL_LAYOUT: ProposalLayout = 'cards';

export const PROPOSAL_LAYOUT_LABELS: Readonly<Record<ProposalLayout, string>> = {
  cards: 'Карточки',
  table: 'Таблица',
};

/** The rows of a table page, as the original pages its table; the contract allows up to 200 and answers 50 without a limit. */
export const TABLE_PAGE_LIMIT = 50;

type Params = Pick<URLSearchParams, 'get' | 'toString'>;

export function isProposalLayout(value: unknown): value is ProposalLayout {
  return typeof value === 'string' && (PROPOSAL_LAYOUTS as readonly string[]).includes(value);
}

export function readProposalLayout(params: Params): ProposalLayout {
  const value = params.get(PROPOSAL_LAYOUT_PARAM);
  return isProposalLayout(value) ? value : DEFAULT_PROPOSAL_LAYOUT;
}

/** The query after the reader chooses a layout; the default is the absent parameter. */
export function writeProposalLayout(params: Params, next: ProposalLayout): URLSearchParams {
  const written = new URLSearchParams(params.toString());
  if (next === DEFAULT_PROPOSAL_LAYOUT) written.delete(PROPOSAL_LAYOUT_PARAM);
  else written.set(PROPOSAL_LAYOUT_PARAM, next);
  return written;
}

/** The page size a layout asks the server for: the table's fifty, or the cards' own page (`cardsLimit`). */
export function pageLimitOf(layout: ProposalLayout, cardsLimit: number): number {
  return layout === 'table' ? TABLE_PAGE_LIMIT : cardsLimit;
}
