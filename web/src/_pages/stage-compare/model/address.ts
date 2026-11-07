/**
 * What «Сравнение стадий» keeps in its address (`UI-B-93`, `R-150c`): the pair, the run and the tab, and whether the sheet map is folded
 * (`map`, below). The original remembered the last
 * pair of the object and the view in `localStorage` (`stage-comparison:*`); the address replaces it, so a reload, a pasted link and
 * Back/Forward open the same step of the same comparison. The project is `?project=` and is not touched here; `pair`, `run` and
 * `tab` are three of the `PROJECT_DEPENDENT_PARAMS`, dropped with the project when the header changes it.
 *
 * Pure: a query string in, a query string out. Whether the pair belongs to the project, and the run to the pair, is the workspace's
 * question once the reads have answered.
 */

export const PAIR_PARAM = 'pair';
export const RUN_PARAM = 'run';
export const TAB_PARAM = 'tab';

export const STAGE_TABS = ['documentation', 'sheets', 'changes', 'journal'] as const;
export type StageTab = (typeof STAGE_TABS)[number];
export const DEFAULT_STAGE_TAB: StageTab = 'documentation';

export interface StageAddress {
  /** The chosen pair, or `''`. */
  readonly pairId: string;
  /** The chosen run of that pair, or `null` for «the latest full run». */
  readonly runId: string | null;
  readonly tab: StageTab;
}

type Params = Pick<URLSearchParams, 'get' | 'toString'>;

export function isStageTab(value: unknown): value is StageTab {
  return typeof value === 'string' && (STAGE_TABS as readonly string[]).includes(value);
}

/** A run means nothing without its pair; an unknown tab is the first, as an absent one. */
export function readStageAddress(params: Params): StageAddress {
  const pair = params.get(PAIR_PARAM) ?? '';
  const run = params.get(RUN_PARAM);
  const tab = params.get(TAB_PARAM);
  return {
    pairId: pair,
    runId: pair === '' || run === null || run === '' ? null : run,
    tab: isStageTab(tab) ? tab : DEFAULT_STAGE_TAB,
  };
}

/** The query after the reader chooses a pair, a run or a step. The first step is the absent `tab`. */
export function writeStageAddress(params: Params, next: StageAddress): URLSearchParams {
  const written = new URLSearchParams(params.toString());
  if (next.pairId === '') written.delete(PAIR_PARAM);
  else written.set(PAIR_PARAM, next.pairId);
  if (next.pairId === '' || next.runId === null) written.delete(RUN_PARAM);
  else written.set(RUN_PARAM, next.runId);
  if (next.tab === DEFAULT_STAGE_TAB) written.delete(TAB_PARAM);
  else written.set(TAB_PARAM, next.tab);
  return written;
}

/**
 * `UI-B-93`: the fold of the sheet map. The original keeps four more things in `localStorage` (`stage-comparison:view-mode|thumbs|
 * sheet-map-collapsed|v3-model|upload-rows`); of them only the fold of the map has an equivalent on this screen, so it is the one
 * written here: `?map=closed` folds the rows of «Карта листов», and the open map is the absent parameter. It is a reader's choice about
 * how the screen looks, held apart from the pair so that choosing another pair keeps it, as the original's flag does.
 *
 * What is not kept, and why: the paged or continuous sheet viewer and the thumbnail rail (this screen's viewer has neither), the order of
 * the upload rows (the upload panel here lists one folder's candidates, not rows the reader arranged), and the analysis model, which
 * is a choice made for one start and is not carried by a link a colleague opens (`StageRunControls` keeps its own).
 */
export const MAP_PARAM = 'map';
const MAP_CLOSED = 'closed';

/** The map is open unless the address says it is folded. */
export function readMapOpen(params: Params): boolean {
  return params.get(MAP_PARAM) !== MAP_CLOSED;
}

/** The query after the reader folds or opens the map; every other parameter is carried through. */
export function writeMapOpen(params: Params, open: boolean): URLSearchParams {
  const written = new URLSearchParams(params.toString());
  if (open) written.delete(MAP_PARAM);
  else written.set(MAP_PARAM, MAP_CLOSED);
  return written;
}
