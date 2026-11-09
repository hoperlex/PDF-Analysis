/**
 * What «База знаний» keeps in its address (`UI-PARITY-01`, completion scenario 5; `D-372`): the type of decisions (`?kind=`), how the
 * list is drawn (`?view=`), and the two filters of the decisions on findings (`?category=`, `?verdict=`). The project is the screen's
 * other address parameter and is read elsewhere (`readProjectContext`).
 *
 * A saved link, a reload and the side menu's «База знаний» (no query: the defaults) now return to the same filter. A filter is not a
 * place to go Back to, so the page REPLACES the entry when it writes one (as «Очередь» does).
 *
 * Pure: a query string in, a query string out. Every value is read against its closed set; one outside it is the default and is never
 * echoed. The default of each is the ABSENT parameter, so an address that narrows nothing is the plain `/knowledge-base`. A parameter
 * that is not this screen's (`project`, `foo`) is carried through a write untouched.
 */

import type { FindingCategory, Verdict } from '@/shared/api';

import { MEMORY_PARAMS } from './memory-address';

/**
 * «Тип»: the decisions on findings, on optimisation proposals, or both as one journal (`D-317`); and `memory`, «Память решений»
 * (`D-495`): the copy of what an expert saw and decided, which the expert and the administrator are offered and the viewer is not
 * (the tab's own filters and open case are in `model/memory-address.ts`).
 */
export type KbKind = 'all' | 'findings' | 'proposals' | 'memory';
/** `UI-B-34`: the original's table (the default) or the rows as events. */
export type KbView = 'table' | 'events';
/** `Все` is the absence of the parameter, never a value sent to the server. */
export type CategoryChoice = FindingCategory | 'all';
export type VerdictChoice = Verdict | 'all';

export const KB_KINDS: readonly KbKind[] = ['all', 'findings', 'proposals', 'memory'];
export const KB_VIEWS: readonly KbView[] = ['table', 'events'];

export const CATEGORY_CHOICES: readonly CategoryChoice[] = [
  'all',
  'internal_contradiction',
  'explicit_placeholder',
  'dimensions',
  'layout',
  'facade',
  'roof',
  'documentation',
  'evacuation',
  'fire_safety',
  'accessibility',
  'insulation',
  'sound',
];

/**
 * `needs_manual_review` is in the contract's closed union and has no PC-01 producer, so it is deliberately not offered: a filter that
 * can only ever return an empty page teaches a reviewer that the knowledge base is empty.
 */
export const VERDICT_CHOICES: readonly VerdictChoice[] = ['all', 'accepted', 'rejected', 'pending'];

export interface KbAddress {
  readonly kind: KbKind;
  readonly view: KbView;
  readonly category: CategoryChoice;
  readonly verdict: VerdictChoice;
}

/** «Замечания» stays the first screen, as it was before «Все»; the table is the default view, as the original's. */
export const DEFAULT_KB_ADDRESS: KbAddress = { kind: 'findings', view: 'table', category: 'all', verdict: 'all' };

export const KB_KIND_PARAM = 'kind';
export const KB_VIEW_PARAM = 'view';
export const KB_CATEGORY_PARAM = 'category';
export const KB_VERDICT_PARAM = 'verdict';

type Params = Pick<URLSearchParams, 'get' | 'toString'>;

function pick<T extends string>(value: string | null, closed: readonly T[], fallback: T): T {
  return value !== null && (closed as readonly string[]).includes(value) ? (value as T) : fallback;
}

export function readKbAddress(params: Params): KbAddress {
  return {
    kind: pick(params.get(KB_KIND_PARAM), KB_KINDS, DEFAULT_KB_ADDRESS.kind),
    view: pick(params.get(KB_VIEW_PARAM), KB_VIEWS, DEFAULT_KB_ADDRESS.view),
    category: pick(params.get(KB_CATEGORY_PARAM), CATEGORY_CHOICES, DEFAULT_KB_ADDRESS.category),
    verdict: pick(params.get(KB_VERDICT_PARAM), VERDICT_CHOICES, DEFAULT_KB_ADDRESS.verdict),
  };
}

/** The query after the reader chooses; a value equal to its default is the absent parameter. */
export function writeKbAddress(params: Params, next: KbAddress): URLSearchParams {
  const written = new URLSearchParams(params.toString());
  const put = (name: string, value: string, fallback: string) => {
    if (value === fallback) written.delete(name);
    else written.set(name, value);
  };
  put(KB_KIND_PARAM, next.kind, DEFAULT_KB_ADDRESS.kind);
  put(KB_VIEW_PARAM, next.view, DEFAULT_KB_ADDRESS.view);
  put(KB_CATEGORY_PARAM, next.category, DEFAULT_KB_ADDRESS.category);
  put(KB_VERDICT_PARAM, next.verdict, DEFAULT_KB_ADDRESS.verdict);
  // The memory tab's filters and open case belong to the tab: leaving it takes them off the address.
  if (next.kind !== 'memory') for (const name of MEMORY_PARAMS) written.delete(name);
  return written;
}
