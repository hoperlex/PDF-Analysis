/**
 * What the «Память решений» tab keeps in the address (`D-495`): the five filters of the list (`?mstatus=`, `?mverdict=`,
 * `?mcategory=`, `?msection=`, `?mclass=`) and the case that is open (`?mcase=`). The tab itself is `?kind=memory`
 * (`model/address.ts`), and the project is the list's `origin_project_uid` (`?project=`, read elsewhere).
 *
 * The same rules as the rest of the screen's address: pure, every value read against its closed set (one outside it is the default
 * and is never echoed), the default of each is the ABSENT parameter, and a parameter that is not this tab's is carried through a
 * write untouched. A case id is read against the contract's pattern, so an address cannot make the page ask for anything else.
 */

import { DECISION_MEMORY_CASE_ID_PATTERN } from '@/shared/api';
import type { DecisionMemoryCaseId } from '@/shared/api';
import { MEMORY_DATA_CLASS_CHOICES, MEMORY_STATUS_CHOICES, MEMORY_VERDICT_CHOICES, NO_MEMORY_FILTERS } from '@/entities/decision-memory';
import type { MemoryFilters } from '@/entities/decision-memory';
import { CATEGORY_LABELS } from '@/entities/expert-decision';
import { PROJECT_SECTIONS } from '@/entities/project';

export interface MemoryAddress {
  readonly filters: MemoryFilters;
  /** The open case, or `null` for the list. */
  readonly caseId: DecisionMemoryCaseId | null;
}

export const DEFAULT_MEMORY_ADDRESS: MemoryAddress = { filters: NO_MEMORY_FILTERS, caseId: null };

export const MEMORY_STATUS_PARAM = 'mstatus';
export const MEMORY_VERDICT_PARAM = 'mverdict';
export const MEMORY_CATEGORY_PARAM = 'mcategory';
export const MEMORY_SECTION_PARAM = 'msection';
export const MEMORY_CLASS_PARAM = 'mclass';
export const MEMORY_CASE_PARAM = 'mcase';

/** Every parameter of this tab: the screen removes them all when it leaves the tab. */
export const MEMORY_PARAMS: readonly string[] = [
  MEMORY_STATUS_PARAM,
  MEMORY_VERDICT_PARAM,
  MEMORY_CATEGORY_PARAM,
  MEMORY_SECTION_PARAM,
  MEMORY_CLASS_PARAM,
  MEMORY_CASE_PARAM,
];

type Params = Pick<URLSearchParams, 'get' | 'toString'>;

const CATEGORY_CODES: readonly string[] = Object.keys(CATEGORY_LABELS);
const SECTION_CODES: readonly string[] = PROJECT_SECTIONS.map((section) => section.code);
const CASE_ID = new RegExp(DECISION_MEMORY_CASE_ID_PATTERN);

function pick<T extends string>(value: string | null, closed: readonly T[], fallback: T): T {
  return value !== null && (closed as readonly string[]).includes(value) ? (value as T) : fallback;
}

function pickCode(value: string | null, closed: readonly string[]): string {
  return value !== null && closed.includes(value) ? value : 'all';
}

export function readMemoryAddress(params: Params): MemoryAddress {
  const caseId = params.get(MEMORY_CASE_PARAM);
  return {
    filters: {
      status: pick(params.get(MEMORY_STATUS_PARAM), MEMORY_STATUS_CHOICES, 'all'),
      verdict: pick(params.get(MEMORY_VERDICT_PARAM), MEMORY_VERDICT_CHOICES, 'all'),
      category: pickCode(params.get(MEMORY_CATEGORY_PARAM), CATEGORY_CODES),
      section: pickCode(params.get(MEMORY_SECTION_PARAM), SECTION_CODES),
      dataClass: pick(params.get(MEMORY_CLASS_PARAM), MEMORY_DATA_CLASS_CHOICES, 'all'),
    },
    caseId: caseId !== null && CASE_ID.test(caseId) ? caseId : null,
  };
}

/** The query after the reader chooses; a value equal to its default is the absent parameter. */
export function writeMemoryAddress(params: Params, next: MemoryAddress): URLSearchParams {
  const written = new URLSearchParams(params.toString());
  const put = (name: string, value: string | null, fallback: string | null) => {
    if (value === fallback || value === null) written.delete(name);
    else written.set(name, value);
  };
  put(MEMORY_STATUS_PARAM, next.filters.status, 'all');
  put(MEMORY_VERDICT_PARAM, next.filters.verdict, 'all');
  put(MEMORY_CATEGORY_PARAM, next.filters.category, 'all');
  put(MEMORY_SECTION_PARAM, next.filters.section, 'all');
  put(MEMORY_CLASS_PARAM, next.filters.dataClass, 'all');
  put(MEMORY_CASE_PARAM, next.caseId, null);
  return written;
}
