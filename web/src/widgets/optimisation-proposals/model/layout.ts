/**
 * `UI-B-06`, `UIP-S09-01`: how a pass's proposals are laid out, and where that choice lives.
 *
 * The original lists the proposals as one dense table (ID, type, current solution, proposal, saving, risks, norm, decision, reason,
 * fifty rows to a page), and so does this tab by default. The same proposals can also be drawn as **cards** (a row of a grid), behind a
 * link «Показать карточками»; the table is one header over every row. It is a way of drawing the page that was read, so it changes no
 * decision, no filter and no cache key beyond the page size the table asks for.
 *
 * The choice is in the address (`?layout=cards`; «Таблица» is the absent parameter, and the earlier `?layout=table` still opens it), so a
 * link, a reload and Back/Forward keep it (`R-150c`). It is a view and not a place, so choosing it REPLACES the history entry. Pure: a
 * query string in, a query string out; a parameter that is not this one is carried through and a value outside the closed set is read as
 * the default, never echoed.
 */

export type ProposalLayout = 'cards' | 'table';

export const PROPOSAL_LAYOUT_PARAM = 'layout';

/** The default first: the table, then the cards. */
export const PROPOSAL_LAYOUTS: readonly ProposalLayout[] = ['table', 'cards'];

export const DEFAULT_PROPOSAL_LAYOUT: ProposalLayout = 'table';

export const PROPOSAL_LAYOUT_LABELS: Readonly<Record<ProposalLayout, string>> = {
  cards: 'Карточки',
  table: 'Таблица',
};

/** What the link that opens a layout says: from the table «Показать карточками», from the cards back to «Показать таблицей». */
export const PROPOSAL_LAYOUT_LINKS: Readonly<Record<ProposalLayout, string>> = {
  cards: 'Показать карточками',
  table: 'Показать таблицей',
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
