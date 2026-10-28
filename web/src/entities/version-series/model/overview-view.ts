/**
 * What «Проекты и этапы» does with the overview the server sent: which of the five counters a document
 * set belongs to, its mark, the search, the filters and the sorts (`version-comparison-projects.js:18-34`,
 * `:310-319`, `:269`).
 *
 * The server sends one entry per document set with its seven steps and, beside them, the counters. The
 * screen filters and sorts what it has, so the group of a set is decided here, once, by a rule a test
 * pins; it is the rule the counters are assumed to follow (the report lists it for the integrator).
 */

import type { ComparisonOverviewCounters, ComparisonOverviewSet, ComparisonStepId, ComparisonStepState } from '@/shared/api';

import { isRunningState, stepRank } from './steps';

export type OverviewGroup = 'waiting' | 'running' | 'failed' | 'ready';
export type OverviewFilter = 'all' | OverviewGroup;

export const OVERVIEW_FILTERS: readonly { readonly key: OverviewFilter; readonly label: string; readonly hint: string }[] = [
  { key: 'all', label: 'Все', hint: 'Показать все комплекты проекта.' },
  { key: 'waiting', label: 'Ждут действия', hint: 'Комплекты, где следующий шаг за вами: что-то нужно запустить или проверить.' },
  { key: 'running', label: 'Идут', hint: 'Комплекты, где сейчас идёт расчёт или загрузка.' },
  { key: 'failed', label: 'Ошибки', hint: 'Комплекты с ошибкой разбора или одного из шагов.' },
  { key: 'ready', label: 'Готовы', hint: 'Комплекты, где всё посчитано и действий не требуется.' },
];

function stateOf(set: ComparisonOverviewSet, step: ComparisonStepId): ComparisonStepState | undefined {
  return set.steps.find((entry) => entry.step === step)?.state;
}

/**
 * The group of a set: an error in any step is «Ошибки»; else a step that is being computed is «Идут»;
 * else a proposed next step is «Ждут действия»; else «Готовы».
 */
export function groupOf(set: ComparisonOverviewSet): OverviewGroup {
  if (set.steps.some((entry) => entry.state === 'failed')) return 'failed';
  if (set.steps.some((entry) => isRunningState(entry.state))) return 'running';
  if (set.next_step !== undefined) return 'waiting';
  return 'ready';
}

/** The «шифр» a row is known by: the designation, else the title, else nothing a reader could use. */
export function codeOf(set: ComparisonOverviewSet): string {
  return set.designation ?? set.title ?? '';
}

/** The mark: the letters at the tail of the designation after the last hyphen («133/23-ГК-ЭМ2» → «ЭМ»). */
export function markOf(designation: string | undefined): string {
  const tail = (designation ?? '').split('-').pop() ?? '';
  const letters = /^[А-ЯЁA-Z]+/i.exec(tail);
  return letters === null ? '—' : letters[0].toUpperCase();
}

export type SortKey = 'code' | 'step' | 'updated' | 'versions' | ComparisonStepId;
export type SortDirection = 'asc' | 'desc';
export interface Sort {
  readonly key: SortKey;
  readonly direction: SortDirection;
}

/** The four presets of the «Порядок» select (`:113-118`). */
export const SORT_PRESETS: readonly { readonly value: string; readonly label: string; readonly sort: Sort }[] = [
  { value: 'code|asc', label: 'по шифру', sort: { key: 'code', direction: 'asc' } },
  { value: 'step|asc', label: 'сначала требующие действия', sort: { key: 'step', direction: 'asc' } },
  { value: 'updated|asc', label: 'по последней загрузке', sort: { key: 'updated', direction: 'asc' } },
  { value: 'versions|desc', label: 'по числу версий', sort: { key: 'versions', direction: 'desc' } },
];

export function sortValue(sort: Sort): string {
  return `${sort.key}|${sort.direction}`;
}

export function parseSort(value: string): Sort | null {
  return SORT_PRESETS.find((preset) => preset.value === value)?.sort ?? null;
}

const GROUP_RANK: Readonly<Record<OverviewGroup, number>> = { failed: 0, waiting: 1, running: 2, ready: 3 };

function natural(a: string, b: string): number {
  return a.localeCompare(b, 'ru', { numeric: true, sensitivity: 'base' });
}

function compare(a: ComparisonOverviewSet, b: ComparisonOverviewSet, key: SortKey): number {
  switch (key) {
    case 'code': return natural(codeOf(a), codeOf(b));
    case 'step': return GROUP_RANK[groupOf(a)] - GROUP_RANK[groupOf(b)] || natural(codeOf(a), codeOf(b));
    case 'updated': return (b.updated_at ?? '').localeCompare(a.updated_at ?? '') || natural(codeOf(a), codeOf(b));
    case 'versions': return a.version_count - b.version_count || natural(codeOf(a), codeOf(b));
    default: {
      const left = stateOf(a, key);
      const right = stateOf(b, key);
      return (left === undefined ? 99 : stepRank(left)) - (right === undefined ? 99 : stepRank(right)) ||
        natural(codeOf(a), codeOf(b));
    }
  }
}

export interface OverviewView {
  readonly query: string;
  readonly mark: string;
  readonly filter: OverviewFilter;
  readonly sort: Sort;
}

export const INITIAL_VIEW: OverviewView = { query: '', mark: '', filter: 'all', sort: { key: 'code', direction: 'asc' } };

/** The sets the search and the mark let through: what the five counters count (`:318`). */
export function inScope(sets: readonly ComparisonOverviewSet[], view: Pick<OverviewView, 'query' | 'mark'>): ComparisonOverviewSet[] {
  const needle = view.query.trim().toLowerCase();
  return sets.filter(
    (set) =>
      (needle === '' || codeOf(set).toLowerCase().includes(needle)) &&
      (view.mark === '' || markOf(set.designation) === view.mark),
  );
}

export function countsOf(sets: readonly ComparisonOverviewSet[]): ComparisonOverviewCounters {
  const counts = { all: sets.length, waiting: 0, running: 0, failed: 0, ready: 0 };
  for (const set of sets) counts[groupOf(set)] += 1;
  return counts;
}

/** The rows of the table: the scope, the chosen group, in the chosen order. */
export function visibleSets(sets: readonly ComparisonOverviewSet[], view: OverviewView): ComparisonOverviewSet[] {
  const scoped = inScope(sets, view).filter((set) => view.filter === 'all' || groupOf(set) === view.filter);
  const direction = view.sort.direction === 'asc' ? 1 : -1;
  return [...scoped].sort((a, b) => direction * compare(a, b, view.sort.key));
}

/** The marks present among the sets, with how many each has, for the «Марка» select. */
export function marksOf(sets: readonly ComparisonOverviewSet[]): { readonly key: string; readonly count: number }[] {
  const counted = new Map<string, number>();
  for (const set of sets) counted.set(markOf(set.designation), (counted.get(markOf(set.designation)) ?? 0) + 1);
  return [...counted].map(([key, count]) => ({ key, count })).sort((a, b) => natural(a.key, b.key));
}

/** A header click: the same column flips its direction, another starts ascending. */
export function nextSort(current: Sort, key: SortKey): Sort {
  if (current.key === key) return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' };
  return { key, direction: key === 'versions' ? 'desc' : 'asc' };
}

/** Whether anything is being computed, which makes the page poll faster (5 s against 30 s, `:296-300`). */
export function anythingRunning(sets: readonly ComparisonOverviewSet[], uploads: number): boolean {
  return uploads > 0 || sets.some((set) => groupOf(set) === 'running');
}

/** The proposed next step, as a chip says it. */
export const NEXT_STEP_LABELS: Readonly<Record<ComparisonStepId, string>> = {
  upload: 'Загрузить версии',
  profile: 'Разобрать версии',
  matrix: 'Собрать сопоставление листов',
  ai_pairs: 'ИИ-проверка сомнительных пар',
  series: 'Сравнить соседние версии',
  ai_changes: 'ИИ-описание изменений',
  report: 'Сводка и отчёт',
};
