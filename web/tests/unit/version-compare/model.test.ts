/**
 * The model of «Сравнение версий» (`CMP-VC-UI-01`): the words of the steps, the groups and sorts of the overview, the verdict
 * of a transition, the draft of manual edits and its rebase, the gestures that make edits, the notes a click gets, the order of
 * the versions, and the sentences of the module's refusals.
 *
 * Every expectation is a literal. A test that built its expectation from the table it checks would move with it and could not
 * see it being wrong (`OPERATING_CONSTRAINTS.md` §12).
 */

import { describe, expect, it } from 'vitest';

import type { ComparisonMatrix, ComparisonOverviewSet, ComparisonSheetPair, ComparisonTransitionSummary } from '@/shared/api';
import { ApiError } from '@/shared/api';
import {
  ALREADY_THERE,
  CHAIN_NOTE,
  COMPARISON_CONFLICT_SENTENCES,
  COMPARISON_CONSTRAINT_SENTENCES,
  COMPARISON_DEPENDENCY_SENTENCES,
  EMPTY_DRAFT,
  NO_REFERENCE_SHEET,
  SOLE_SHEET,
  WRONG_COLUMN,
  addEdit,
  adjacentSides,
  answerClick,
  baseRevisionOf,
  changedRows,
  codeOf,
  columnNames,
  comparisonFailure,
  comparisonReasonSentence,
  countsOf,
  defaultSides,
  describeEdit,
  dragPayload,
  dropOnCell,
  groupOf,
  isSoleSheet,
  isStale,
  linkCandidate,
  markAbsent,
  markOf,
  moveVersion,
  nextSort,
  pairOfRow,
  parseDragged,
  rebase,
  referencePage,
  removeAt,
  removeLast,
  requestOf,
  splitDirection,
  canRestart,
  continueOf,
  hasLeftovers,
  pairReasonWords,
  partsLine,
  stepActions,
  stepView,
  unlinkSheet,
  validSides,
  verdictSentence,
  visibleSets,
} from '@/entities/version-series';
import type { DraftEdit, OverviewView } from '@/entities/version-series';

import { DOCUMENT_UID, MATRIX_ID, V1, V2, V3, matrix, overview, page, pairs, series, transition, uid } from './fixtures';

const REVISION = { matrix_id: MATRIX_ID, edit_no: 3 };
const LATIN = /[A-Za-z]/;

function envelope(code: ApiError['errorCode'], details: Record<string, string>, retryable = false): ApiError {
  return new ApiError(
    code === 'dependency_unavailable' ? 503 : code === 'conflict' ? 409 : 422,
    {
      contract_version: '1.10.0',
      error_code: code,
      message: 'A caller-safe sentence in English.',
      correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100',
      retryable,
      details,
    },
    '0f0e9d8c-7b6a-4948-b726-150413021100',
  );
}

describe('the words of a step (version-comparison-projects.js:41-94)', () => {
  it('says the original\'s word for the state, and the figures the contract names', () => {
    expect(stepView('profile', 'failed', { ready: 20, total: 24, failed: 2 })).toMatchObject({
      text: 'ошибка', note: '20 из 24 · ошибок 2', tone: 'bad', icon: '✕',
    });
    expect(stepView('profile', 'done', { ready: 24, total: 24, failed: 0 })).toMatchObject({ text: 'готов', note: '24 из 24', tone: 'ok' });
    expect(stepView('matrix', 'attention', { rows: 31, unmatched: 4, manual_edits: 2 })).toMatchObject({
      text: 'не сопост. 4', note: 'строк 31 · ✎ 2', tone: 'warn',
    });
    expect(stepView('matrix', 'not_started').text).toBe('не собрано');
    expect(stepView('series', 'done', { done: 3, total: 3, with_changes: 2 })).toMatchObject({ text: 'готово', note: '3 из 3 · с изм. 2' });
    expect(stepView('series', 'stale').text).toBe('по старому порядку');
    expect(stepView('upload', 'done', { total: 5 })).toMatchObject({ text: 'загружен', note: 'файлов 5' });
  });

  it('prints no figure the server did not send, and never a code', () => {
    expect(stepView('series', 'running').note).toBe('');
    expect(stepView('profile', 'running').note).toBe('');
    expect(stepView('matrix', 'done', {}).note).toBe('');
    for (const state of ['not_started', 'queued', 'running', 'pausing', 'paused', 'interrupted', 'done', 'partial', 'stale', 'attention', 'failed', 'blocked', 'not_applicable'] as const) {
      for (const id of ['upload', 'profile', 'matrix', 'series', 'ai_pairs', 'ai_changes', 'report'] as const) {
        const view = stepView(id, state, { ready: 1, total: 2, failed: 0, rows: 1, unmatched: 0, done: 1, with_changes: 0 });
        expect(view.text, `${id}/${state}`).not.toMatch(LATIN);
        expect(view.text.length, `${id}/${state}`).toBeGreaterThan(0);
      }
    }
  });

  it('offers a button only where the original did, and only for the right state', () => {
    expect(stepActions('profile', 'failed')).toEqual([{ id: 'prepare', label: 'Повторить' }]);
    expect(stepActions('profile', 'done', { failed: 0 })).toEqual([]);
    expect(stepActions('profile', 'done', { failed: 1 })).toEqual([{ id: 'prepare', label: 'Повторить' }]);
    expect(stepActions('matrix', 'not_started')).toEqual([{ id: 'prepare', label: 'Подготовить' }]);
    expect(stepActions('matrix', 'stale')).toEqual([{ id: 'prepare', label: 'Подготовить' }]);
    expect(stepActions('matrix', 'done')).toEqual([]);
    expect(stepActions('series', 'not_started')).toEqual([{ id: 'start', label: 'Запустить' }]);
    expect(stepActions('series', 'running')).toEqual([{ id: 'pause', label: 'Пауза' }]);
    expect(stepActions('series', 'paused')).toEqual([{ id: 'resume', label: 'Продолжить' }, { id: 'restart', label: 'Заново' }]);
    expect(stepActions('series', 'interrupted')).toEqual([{ id: 'finish', label: 'Продолжить' }, { id: 'restart', label: 'Заново' }]);
    expect(stepActions('series', 'done')).toEqual([{ id: 'restart', label: 'Заново' }]);
    expect(stepActions('series', 'blocked')).toEqual([]);
    expect(stepActions('upload', 'failed')).toEqual([]);
    expect(stepActions('ai_pairs', 'not_started')).toEqual([]);
  });
});

describe('the words of the series (CMP-SERIES-01 section 10)', () => {
  it('says the series of step 5 in the integrator\'s words: queued and running are «идёт»', () => {
    expect(stepView('series', 'queued').text).toBe('идёт');
    expect(stepView('series', 'running').text).toBe('идёт');
    expect(stepView('series', 'paused').text).toBe('пауза');
    expect(stepView('series', 'interrupted').text).toBe('прервано');
    expect(stepView('series', 'stale').text).toBe('по старому порядку');
  });

  it('offers «Продолжить» to a paused series, «Досчитать» to a finished one with something left, «Заново» to one that is not live', () => {
    const clean = series({ state: 'completed', transitions: (series().transitions ?? []).map((item) => ({ ...item, summary: { ...item.summary, failed: 0 } })) });
    expect(hasLeftovers(clean)).toBe(false);
    expect(continueOf(clean)).toBeNull();
    expect(continueOf(series({ state: 'completed' }))).toBe('finish');
    expect(hasLeftovers(series({ state: 'completed' }))).toBe(true);
    const unfinished = series({ state: 'completed', transitions: [transition({ transition_id: uid('ctn', 9), source_version_uid: V1, target_version_uid: V2, state: 'failed' })] });
    expect(continueOf(unfinished)).toBe('finish');
    expect(continueOf(series({ state: 'paused' }))).toBe('resume');
    expect(continueOf(series({ state: 'failed' }))).toBe('finish');
    expect(continueOf(series({ state: 'cancelled' }))).toBe('finish');
    expect(continueOf(series({ state: 'running' }))).toBeNull();
    expect(canRestart('completed')).toBe(true);
    expect(canRestart('failed')).toBe(true);
    expect(canRestart('cancelled')).toBe(true);
    expect(canRestart('paused')).toBe(false);
    expect(canRestart('running')).toBe(false);
    expect(canRestart('queued')).toBe(false);
  });

  it('says the reasons of a pair, including the series\' own and the unchecked channels, and never a code it does not know', () => {
    expect(pairReasonWords('SPLIT_SHEET')).toBe('лист разделён между версиями: проверьте части');
    expect(pairReasonWords('NO_TEXT_LAYER')).toBe('нет текстового слоя');
    expect(pairReasonWords('UNCHECKED_CHANNEL_TEXT')).toBe('не проверено: текст');
    expect(pairReasonWords('UNCHECKED_CHANNEL_SPEC_POSITIONS')).toBe('не проверено: позиции СО');
    expect(pairReasonWords('UNCHECKED_CHANNEL_SOMETHING_NEW')).toBe('причина не описана');
    expect(pairReasonWords('A_CODE_FROM_THE_FUTURE')).toBe('причина не описана');
  });

  it('says how a split sheet is covered', () => {
    expect(partsLine({ role: 'whole', covered_percent: 100, parts: [] })).toBe('лист целиком · покрытие 100 %');
    expect(partsLine({ role: 'part', covered_percent: 61.5, parts: [] })).toBe('часть листа · части вместе покрывают 61,5 % прежнего листа');
  });
});

describe('the group of a row as the screen reads it', () => {
  const sets = overview().sets;

  it('groups a set by the step it proposes and that step\'s state, as the server counts', () => {
    const byState = (state: string) => sets.find((set) => set.steps[1]?.state === state);
    expect(groupOf(byState('failed') as never)).toBe('failed');
    expect(groupOf(byState('queued') as never)).toBe('running');
    expect(groupOf(byState('stale') as never)).toBe('waiting');
    expect(groupOf(byState('done') as never)).toBe('ready');
    // a failed step the set does not propose is not the row's colour, and a running step it does not propose is not "Идут"
    const mixed = { ...(byState('done') as object), next_step: 'series' } as never as ComparisonOverviewSet;
    const withStates = (states: Record<string, string>): ComparisonOverviewSet =>
      ({ ...mixed, steps: mixed.steps.map((entry) => ({ ...entry, state: states[entry.step] ?? entry.state })) }) as never;
    expect(groupOf(withStates({ profile: 'failed', matrix: 'running', series: 'stale' }))).toBe('waiting');
    expect(groupOf(withStates({ profile: 'done', series: 'failed' }))).toBe('waiting');
    expect(groupOf(withStates({ series: 'running' }))).toBe('running');
  });
});

describe('the group of a row and the counters are the server\'s rule (CMP-VC-OVERVIEW-01 section 6.3)', () => {
  const STEP_IDS = ['upload', 'profile', 'matrix', 'ai_pairs', 'series', 'ai_changes', 'report'] as const;
  const STATES = [
    'not_started', 'queued', 'running', 'pausing', 'paused', 'interrupted', 'done', 'partial', 'stale', 'attention', 'failed', 'blocked',
    'not_applicable',
  ] as const;
  type Group = 'waiting' | 'running' | 'failed' | 'ready';

  /** The group by the state of the PROPOSED step, written out for the upload, the profile and the matrix (a failure there is red). */
  const RED_STEPS: Readonly<Record<(typeof STATES)[number], Group>> = {
    not_started: 'waiting', queued: 'running', running: 'running', pausing: 'running', paused: 'waiting', interrupted: 'waiting',
    done: 'waiting', partial: 'waiting', stale: 'waiting', attention: 'waiting', failed: 'failed', blocked: 'waiting', not_applicable: 'waiting',
  };
  /** The same for every other step: a failed series is «Ждут действия», as in the original (`OV:321-322`). */
  const OTHER_STEPS: Readonly<Record<(typeof STATES)[number], Group>> = { ...RED_STEPS, failed: 'waiting' };

  /** A set whose proposed step has `state` and whose other six steps all have `others`: they must not matter. */
  function setProposing(next: (typeof STEP_IDS)[number] | undefined, state: (typeof STATES)[number], others: (typeof STATES)[number], n: number): ComparisonOverviewSet {
    return {
      document_uid: uid('doc', n),
      version_count: 3,
      ...(next === undefined ? {} : { next_step: next }),
      steps: STEP_IDS.map((step) => ({ step, state: step === next ? state : others })),
    } as ComparisonOverviewSet;
  }

  it('puts every proposed step in every state in the group the server counts it in, whatever the other steps say', () => {
    let n = 0;
    for (const next of STEP_IDS) {
      const table = next === 'upload' || next === 'profile' || next === 'matrix' ? RED_STEPS : OTHER_STEPS;
      for (const state of STATES) {
        for (const others of ['failed', 'running', 'done'] as const) {
          n += 1;
          expect(groupOf(setProposing(next, state, others, n)), `${next}/${state} among ${others}`).toBe(table[state]);
        }
      }
    }
    expect(n).toBe(7 * 13 * 3);
  });

  it('puts a set that proposes nothing in «Готовы», whatever its steps say', () => {
    for (const state of STATES) {
      expect(groupOf(setProposing(undefined, state, state, 1)), state).toBe('ready');
    }
  });

  it('recomputes the counters over every state combination exactly as the server counts them', () => {
    const rows: ComparisonOverviewSet[] = [];
    for (const next of STEP_IDS) for (const state of STATES) rows.push(setProposing(next, state, 'failed', rows.length + 1));
    for (const state of STATES) rows.push(setProposing(undefined, state, 'running', rows.length + 1));
    // By hand: each of the 3 red-when-failed steps has 3 running states, 1 failed and 9 waiting; each of the other 4 has
    // 3 running, 0 failed and 10 waiting; the 13 rows with nothing proposed are ready. 91 + 13 = 104.
    const server = { all: 104, waiting: 3 * 9 + 4 * 10, running: 7 * 3, failed: 3, ready: 13 };
    expect(server).toEqual({ all: 104, waiting: 67, running: 21, failed: 3, ready: 13 });
    expect(countsOf(rows)).toEqual(server);
    for (const group of ['waiting', 'running', 'failed', 'ready'] as const) {
      expect(visibleSets(rows, { query: '', mark: '', filter: group, sort: { key: 'code', direction: 'asc' } }).length, group).toBe(server[group]);
    }
  });

  it('recomputes the fixture overview\'s counters to the ones its read carries', () => {
    const read = overview();
    expect(countsOf(read.sets)).toEqual(read.counters);
    expect(read.counters).toEqual({ all: 13, waiting: 6, running: 3, failed: 1, ready: 3 });
  });
});

describe('the search, the mark and the sorts of the overview', () => {
  const sets = overview().sets;

  it('takes the mark from the tail of the designation', () => {
    expect(markOf('133/23-ГК-ЭМ2')).toBe('ЭМ');
    expect(markOf('133/23-ГК-ТХ.ВТ')).toBe('ТХ');
    expect(markOf('133/23-гк-эм')).toBe('ЭМ');
    expect(markOf(undefined)).toBe('—');
    expect(markOf('133/23')).toBe('—');
  });

  it('counts what the search and the mark let through, and filters by the chosen group', () => {
    const view: OverviewView = { query: 'эм', mark: '', filter: 'all', sort: { key: 'code', direction: 'asc' } };
    const found = visibleSets(sets, view);
    expect(found.length).toBe(3);
    expect(found.every((set) => codeOf(set).toLowerCase().includes('эм'))).toBe(true);
    expect(countsOf(found).all).toBe(3);
    const failed = visibleSets(sets, { ...view, query: '', filter: 'failed' });
    expect(failed.length).toBe(1);
    expect(visibleSets(sets, { ...view, query: '', mark: 'АР' }).map((set) => markOf(set.designation))).toEqual(['АР', 'АР']);
  });

  it('sorts naturally by code, and flips a column on the second click', () => {
    const asc = visibleSets(sets, { query: '', mark: '', filter: 'all', sort: { key: 'code', direction: 'asc' } });
    const desc = visibleSets(sets, { query: '', mark: '', filter: 'all', sort: { key: 'code', direction: 'desc' } });
    expect(desc.map((set) => set.document_uid)).toEqual([...asc].reverse().map((set) => set.document_uid));
    expect(nextSort({ key: 'code', direction: 'asc' }, 'code')).toEqual({ key: 'code', direction: 'desc' });
    expect(nextSort({ key: 'code', direction: 'asc' }, 'versions')).toEqual({ key: 'versions', direction: 'desc' });
    const byAction = visibleSets(sets, { query: '', mark: '', filter: 'all', sort: { key: 'step', direction: 'asc' } });
    expect(groupOf(byAction[0] as never)).toBe('failed');
  });
});

describe('the verdict of a transition, in the original\'s words (series.py:54-62)', () => {
  const summary = (over: Partial<ComparisonTransitionSummary> = {}): ComparisonTransitionSummary => ({
    sheets: 10, compared: 10, same: 4, zones_only: 1, different: 3, style_only: 0, needs_review: 2, added: 1, removed: 2, failed: 1, ...over,
  });

  it('builds each sentence from its code and its figure', () => {
    expect(verdictSentence(['incomplete'], summary())).toBe('переход досчитан не полностью');
    expect(verdictSentence(['content_same'], summary())).toBe('основное содержание совпадает');
    expect(verdictSentence(['content_same', 'zones_only'], summary())).toBe('основное содержание совпадает, изменены только служебные зоны');
    expect(verdictSentence(['zones_only'], summary())).toBe('изменены только служебные зоны');
    expect(verdictSentence(['different'], summary())).toBe('есть отличия на 3 л.');
    expect(verdictSentence(['different'], summary({ style_only: 2 }))).toBe('есть отличия на 3 л. (из них только оформление линий — 2)');
    expect(verdictSentence(['composition_changed'], summary())).toBe('изменён состав (+1 / −2 л.)');
    expect(verdictSentence(['needs_review'], summary())).toBe('нужна проверка: 2');
    expect(verdictSentence(['calculation_failed'], summary())).toBe('ошибка расчёта: 1');
  });

  it('joins the parts with «; » in the order they come, and says so when a transition rests on an AI link', () => {
    expect(verdictSentence(['different', 'composition_changed', 'needs_review'], summary())).toBe(
      'есть отличия на 3 л.; изменён состав (+1 / −2 л.); нужна проверка: 2',
    );
    expect(verdictSentence(['content_same'], summary({ ai_dependent: 2 }))).toBe(
      'основное содержание совпадает; 2 пар опираются на связь, предложенную ИИ',
    );
  });

  it('says that nothing is concluded yet rather than printing an empty cell', () => {
    expect(verdictSentence(undefined, summary())).toBe('вывод ещё не сформирован');
    expect(verdictSentence([], summary())).toBe('вывод ещё не сформирован');
  });
});

describe('the matrix as the screen reads it', () => {
  const m = matrix();
  const rows = m.rows ?? [];
  const cols = m.columns ?? [];

  it('names the columns by their place in the comparison order, not by the document\'s ordinal', () => {
    expect([...columnNames(cols).values()]).toEqual(['№1', '№2', '№3']);
  });

  it('picks the last two versions as the pair, and judges sides', () => {
    expect(defaultSides(cols)).toEqual({ a: V2, b: V3 });
    expect(validSides({ a: V2, b: V3 }, cols)).toBe(true);
    expect(validSides({ a: V2, b: V2 }, cols)).toBe(false);
    expect(validSides({ a: null, b: V3 }, cols)).toBe(false);
    expect(adjacentSides({ a: V1, b: V2 }, cols)).toBe(true);
    expect(adjacentSides({ a: V1, b: V3 }, cols)).toBe(false);
    expect(adjacentSides({ a: V3, b: V2 }, cols)).toBe(false);
  });

  it('chooses a reference sheet from another version than the one that joins it', () => {
    const r6 = rows[5];
    expect(referencePage(r6 as never, V3)).toEqual(page(V1, 6));
    expect(referencePage(rows[6] as never, V3)).toEqual(null);
    expect(referencePage(rows[6] as never, V1)).toEqual(page(V3, 9));
    expect(isSoleSheet(rows[6] as never)).toBe(true);
    expect(isSoleSheet(r6 as never)).toBe(false);
  });

  it('finds the pair of a row in the chosen transition and keeps only the changed rows', () => {
    const list = pairs();
    const sides = { a: V2, b: V3 };
    expect(pairOfRow(rows[0] as never, sides, list)?.status).toBe('same');
    expect(pairOfRow(rows[3] as never, sides, list)?.status).toBe('removed');
    expect(pairOfRow(rows[5] as never, sides, list)?.status).toBe('unmatched');
    expect(pairOfRow(rows[6] as never, sides, list)?.status).toBe('added');
    expect(changedRows(rows, sides, list).map((row) => row.title)).toEqual([
      'План этажа 1', 'Спецификация оборудования', 'План кровли', 'Разрез 1-1', 'Узел 3', 'План кровли, часть 2',
    ]);
    const none: readonly ComparisonSheetPair[] = [];
    expect(changedRows(rows, sides, none)).toEqual([]);
  });

  it('gives the second part of a split sheet its own pair although the older sheet stands in both (CMP-SERIES-01)', () => {
    const list = pairs();
    const sides = { a: V2, b: V3 };
    expect(pairOfRow(rows[4] as never, sides, list)?.sheet_pair_id).toBe(uid('ctp', 5));
    expect(pairOfRow(rows[7] as never, sides, list)).toMatchObject({ sheet_pair_id: uid('ctp', 8), parts: { role: 'part' } });
    expect(pairOfRow(rows[7] as never, sides, list)?.page_a?.page).toEqual(page(V2, 5));
  });

  it('reads a split cell as the whole sheet when the next version holds a split sheet too', () => {
    expect(splitDirection(rows[4] as never, V1)).toBe('whole');
    expect(splitDirection(rows[4] as never, V2)).toBe('whole');
    expect(splitDirection(rows[4] as never, V3)).toBe('part');
  });
});

describe('what a gesture turns into', () => {
  const rows = matrix().rows ?? [];

  it('«Связать» is link(row page, candidate), from the version that is not the candidate\'s', () => {
    const candidate = { page: page(V3, 7), score: 0.41 };
    expect(linkCandidate(rows[5] as never, V3, candidate)).toEqual({ edit: { kind: 'link', page: page(V1, 6), otherPage: page(V3, 7) } });
    expect(linkCandidate(rows[5] as never, V2, candidate)).toEqual({ refusal: NO_REFERENCE_SHEET });
    expect(linkCandidate(rows[6] as never, V2, { page: page(V2, 8), score: 0.3 })).toEqual({ edit: { kind: 'link', page: page(V3, 9), otherPage: page(V2, 8) } });
  });

  it('a thumbnail dropped on a cell links it, and only into the column of its own version', () => {
    expect(dropOnCell(rows[5] as never, V3, page(V3, 8))).toEqual({ edit: { kind: 'link', page: page(V1, 6), otherPage: page(V3, 8) } });
    expect(dropOnCell(rows[5] as never, V2, page(V3, 8))).toEqual({ refusal: WRONG_COLUMN });
    expect(dropOnCell(rows[0] as never, V2, page(V2, 1))).toEqual({ refusal: ALREADY_THERE });
    expect(dropOnCell(rows[6] as never, V3, page(V3, 8))).toEqual({ refusal: NO_REFERENCE_SHEET } satisfies unknown as never);
  });

  it('«⤫» is unlink and refuses a lone sheet; «листа нет» is mark_absent(reference page, version)', () => {
    expect(unlinkSheet(rows[0] as never, page(V2, 1))).toEqual({ edit: { kind: 'unlink', page: page(V2, 1) } });
    expect(unlinkSheet(rows[6] as never, page(V3, 9))).toEqual({ refusal: SOLE_SHEET });
    expect(markAbsent(rows[5] as never, V3)).toEqual({ edit: { kind: 'mark_absent', page: page(V1, 6), absentVersionUid: V3 } });
    expect(markAbsent(rows[6] as never, V3)).toEqual({ refusal: NO_REFERENCE_SHEET });
  });

  it('reads a dragged page back, and nothing else', () => {
    expect(parseDragged(dragPayload(page(V2, 4)))).toEqual(page(V2, 4));
    expect(parseDragged('')).toBeNull();
    expect(parseDragged('{"version_uid":3}')).toBeNull();
    expect(parseDragged('{"version_uid":"ver_x","page_number":0}')).toBeNull();
    expect(parseDragged('not json')).toBeNull();
  });
});

describe('the draft of manual edits, and its rebase on a matrix that moved', () => {
  const link: DraftEdit = { kind: 'link', page: page(V1, 6), otherPage: page(V3, 7) };
  const unlink: DraftEdit = { kind: 'unlink', page: page(V2, 1) };
  const absent: DraftEdit = { kind: 'mark_absent', page: page(V1, 6), absentVersionUid: V3 };

  it('fixes the base revision at the first edit, ignores an equal edit and removes the last', () => {
    const one = addEdit(EMPTY_DRAFT, REVISION, link);
    expect(one).toEqual({ base: REVISION, edits: [link] });
    const later = addEdit(one as never, { matrix_id: MATRIX_ID, edit_no: 9 }, unlink);
    expect(later?.base).toEqual(REVISION);
    expect(later?.edits).toEqual([link, unlink]);
    expect(addEdit(later as never, REVISION, link)).toBe(later);
    expect(removeLast(later as never)).toEqual({ base: REVISION, edits: [link] });
    expect(removeLast(removeLast(later as never))).toEqual(EMPTY_DRAFT);
    expect(removeAt(later as never, 0).edits).toEqual([unlink]);
  });

  it('refuses the 501st edit', () => {
    let draft = EMPTY_DRAFT;
    for (let n = 1; n <= 500; n += 1) {
      const added = addEdit(draft, REVISION, { kind: 'unlink', page: { version_uid: V1, page_number: n } });
      expect(added).not.toBeNull();
      draft = added as never;
    }
    expect(addEdit(draft, REVISION, { kind: 'unlink', page: { version_uid: V1, page_number: 501 } })).toBeNull();
  });

  it('is sent as one batch against the base revision, in the order made', () => {
    const draft = addEdit(addEdit(EMPTY_DRAFT, REVISION, link) as never, REVISION, absent) as never;
    expect(requestOf(draft)).toEqual({
      base_revision: REVISION,
      edits: [
        { kind: 'link', page: page(V1, 6), other_page: page(V3, 7) },
        { kind: 'mark_absent', page: page(V1, 6), absent_version_uid: V3 },
      ],
    });
    expect(requestOf(EMPTY_DRAFT)).toBeNull();
  });

  it('knows that the matrix moved under it', () => {
    const draft = addEdit(EMPTY_DRAFT, REVISION, link) as never;
    expect(isStale(draft, REVISION)).toBe(false);
    expect(isStale(draft, { matrix_id: MATRIX_ID, edit_no: 4 })).toBe(true);
    expect(isStale(draft, { matrix_id: uid('cmx', 2), edit_no: 3 })).toBe(true);
    expect(isStale(EMPTY_DRAFT, { matrix_id: MATRIX_ID, edit_no: 4 })).toBe(false);
  });

  it('rebases on the fresh revision, keeps the edits that still fit and REPORTS the ones that do not', () => {
    const draft = addEdit(addEdit(EMPTY_DRAFT, REVISION, link) as never, REVISION, { kind: 'unlink', page: page(V2, 40) }) as never;
    const fresh: ComparisonMatrix = matrix({ revision: { matrix_id: MATRIX_ID, edit_no: 4 } });
    const result = rebase(draft, fresh);
    expect(result.draft.base).toEqual({ matrix_id: MATRIX_ID, edit_no: 4 });
    expect(result.draft.edits).toEqual([link]);
    expect(result.dropped).toEqual([{ kind: 'unlink', page: page(V2, 40) }]);
  });

  it('drops a mark_absent whose version the fresh matrix no longer has, and empties against a matrix with no build', () => {
    const draft = addEdit(EMPTY_DRAFT, REVISION, { kind: 'mark_absent', page: page(V1, 6), absentVersionUid: uid('ver', 9) }) as never;
    expect(rebase(draft, matrix()).dropped.length).toBe(1);
    const noBuild = matrix();
    delete (noBuild as { revision?: unknown }).revision;
    const empty = rebase(addEdit(EMPTY_DRAFT, REVISION, link) as never, noBuild);
    expect(empty.draft).toEqual(EMPTY_DRAFT);
    expect(empty.dropped).toEqual([link]);
  });

  it('says an edit in words, naming the versions by their column', () => {
    const name = (versionUid: string) => ({ [V1]: '№1', [V2]: '№2', [V3]: '№3' })[versionUid] ?? '?';
    expect(describeEdit(link, name)).toBe('Связать лист 7 (версия №3) с листом 6 (версия №1)');
    expect(describeEdit(unlink, name)).toBe('Отвязать лист 1 (версия №2) в отдельную строку');
    expect(describeEdit(absent, name)).toBe('Отметить, что листа 6 (версия №1) нет в версии №3');
  });
});

describe('what a click says when there is nothing to open', () => {
  const m = matrix();
  const cols = m.columns ?? [];
  const names = columnNames(cols);
  const context = { columns: cols, names, sides: { a: V2, b: V3 }, transitionExists: true, pair: pairs()[0] ?? null, versionUid: V3 };

  it('opens a finished pair', () => {
    expect(answerClick(context)).toEqual({ open: pairs()[0] });
  });

  it('explains each reason in the original\'s sentence', () => {
    expect(answerClick({ ...context, columns: cols.slice(0, 1) })).toEqual({ note: 'В проекте одна версия — сравнивать не с чем.' });
    expect(answerClick({ ...context, sides: { a: V2, b: V2 } })).toEqual({ note: 'Выберите две разные версии.' });
    expect(answerClick({ ...context, sides: { a: V1, b: V3 } })).toEqual({ note: CHAIN_NOTE });
    expect(answerClick({ ...context, transitionExists: false })).toEqual({
      note: 'Переход №2 → №3 ещё не посчитан: запустите «Сравнение соседних» на вкладке «Проекты и этапы».',
    });
    expect(answerClick({ ...context, pair: null })).toEqual({ note: 'У листа нет пары в версии №2.' });
    expect(answerClick({ ...context, pair: { ...(pairs()[0] as ComparisonSheetPair), state: 'computing' } })).toEqual({
      note: 'Сравнение этого листа ещё не готово.',
    });
  });
});

describe('the order of the versions', () => {
  it('moves one version a step and ignores a move off either end', () => {
    expect(moveVersion(['a', 'b', 'c'], 1, -1)).toEqual(['b', 'a', 'c']);
    expect(moveVersion(['a', 'b', 'c'], 1, 1)).toEqual(['a', 'c', 'b']);
    expect(moveVersion(['a', 'b', 'c'], 0, -1)).toEqual(['a', 'b', 'c']);
    expect(moveVersion(['a', 'b', 'c'], 2, 1)).toEqual(['a', 'b', 'c']);
    expect(moveVersion(['a', 'b', 'c'], 9, 1)).toEqual(['a', 'b', 'c']);
  });

  it('takes the latest revision number as the base, and 0 when there is none', () => {
    expect(baseRevisionOf(null)).toBe(0);
    expect(baseRevisionOf(undefined)).toBe(0);
    expect(
      baseRevisionOf({ order_id: uid('cvo', 1), document_uid: DOCUMENT_UID, revision_no: 4, version_uids: [V1], source: 'expert', created_at: '', created_by: 'usr_1' }),
    ).toBe(4);
  });
});

describe('the sentences of the module\'s refusals (CMP-SEAL-C0, CMP-SEAL-C1)', () => {
  const CONFLICT_REASONS = [
    'comparison_upload_active', 'comparison_upload_state', 'comparison_set_state', 'comparison_version_order_stale',
    'comparison_matrix_stale', 'comparison_edit_none', 'comparison_series_active', 'comparison_series_state',
  ];
  const CONSTRAINTS = [
    'comparison_files_limit', 'comparison_sets_limit', 'comparison_batch_bytes_limit', 'comparison_batch_pages_limit',
    'comparison_project_bytes_limit', 'comparison_part_number', 'comparison_part_size', 'comparison_set_members',
    'comparison_edit_invalid', 'comparison_edits_limit', 'comparison_versions_few', 'display_name', 'required_together', 'declared_page_count',
    'comparison_zip_unreadable', 'comparison_zip_entry_count', 'comparison_zip_member_name', 'comparison_zip_symlink',
    'comparison_zip_encrypted_member', 'comparison_zip_compression_method', 'comparison_zip_duplicate_member',
    'comparison_zip_member_kind', 'comparison_zip_nested_depth', 'comparison_zip_member_size', 'comparison_zip_total_size',
    'comparison_zip_compression_ratio', 'comparison_zip_empty',
  ];
  const DEPENDENCIES = [
    'comparison_uploads', 'comparison_version_orders', 'version_pages', 'comparison_matrix', 'comparison_series',
    'comparison_pair_tiles', 'comparison_overview', 'comparison_modules', 'comparison_versions_module',
  ];

  it('has a Russian sentence for every reason the two seals registered', () => {
    for (const reason of CONFLICT_REASONS) {
      const sentence = comparisonReasonSentence(envelope('conflict', { conflict_reason: reason }));
      expect(sentence, reason).not.toBeNull();
      expect(sentence, reason).toMatch(/[А-Яа-я]/);
    }
    for (const reason of CONSTRAINTS) {
      const sentence = comparisonReasonSentence(envelope('validation_failed', { constraint: reason, field: 'files' }));
      expect(sentence, reason).not.toBeNull();
    }
    for (const reason of DEPENDENCIES) {
      const sentence = comparisonReasonSentence(envelope('dependency_unavailable', { dependency: reason }, true));
      expect(sentence, reason).not.toBeNull();
    }
    expect(Object.keys(COMPARISON_CONFLICT_SENTENCES).sort()).toEqual([...CONFLICT_REASONS].sort());
    expect(Object.keys(COMPARISON_CONSTRAINT_SENTENCES).sort()).toEqual([...CONSTRAINTS].sort());
    expect(Object.keys(COMPARISON_DEPENDENCY_SENTENCES).sort()).toEqual([...DEPENDENCIES].sort());
  });

  it('writes no Latin word into a sentence except the names the sentences give on purpose', () => {
    const all = [
      ...Object.values(COMPARISON_CONFLICT_SENTENCES),
      ...Object.values(COMPARISON_CONSTRAINT_SENTENCES),
      ...Object.values(COMPARISON_DEPENDENCY_SENTENCES),
    ];
    for (const sentence of all) {
      // `deflate` (the one compression method the archive reader allows) and `ZIP` are names, not words to translate.
      const stripped = sentence.replace(/deflate|ZIP|PDF|МиБ|ГиБ/g, '');
      expect(stripped, sentence).not.toMatch(LATIN);
    }
  });

  it('words the matrix that is not ready, and the document set of one version, for the start of a series', () => {
    const notReady = comparisonReasonSentence(envelope('conflict', { conflict_reason: 'comparison_matrix_stale' }));
    expect(notReady).toContain('либо ещё не готово');
    expect(notReady).toContain('оно изменилось после того, как вы его открыли');
    expect(comparisonReasonSentence(envelope('validation_failed', { constraint: 'comparison_versions_few' }))).toBe(
      'В комплекте одна версия: сравнивать соседние версии не с чем. Загрузите ещё одну версию, затем запустите сравнение.',
    );
  });

  it('classifies a module that is not wired as a state of the module, and a stale matrix as a stale matrix', () => {
    const wired = comparisonFailure(envelope('dependency_unavailable', { dependency: 'comparison_overview' }, true));
    expect(wired.moduleUnavailable).toBe(true);
    expect(wired.kind).toBe('module_unavailable');
    expect(wired.detail).toMatch(/^Модуль «Сравнение версий» ещё недоступен/);
    const stale = comparisonFailure(envelope('conflict', { conflict_reason: 'comparison_matrix_stale' }));
    expect(stale.matrixStale).toBe(true);
    expect(stale.moduleUnavailable).toBe(false);
    expect(comparisonFailure(envelope('conflict', { conflict_reason: 'comparison_version_order_stale' })).orderStale).toBe(true);
  });

  it('does not take a dependency of another module for this one, and falls back to the code\'s own sentence', () => {
    const other = comparisonFailure(envelope('dependency_unavailable', { dependency: 'provider' }, true));
    expect(other.moduleUnavailable).toBe(false);
    expect(other.detail).toMatch(/[А-Яа-я]/);
    const unknown = comparisonFailure(envelope('conflict', { conflict_reason: 'a_reason_from_the_future' }));
    expect(unknown.detail).toMatch(/[А-Яа-я]/);
    expect(unknown.detail).not.toMatch(/English/);
  });

  it('says the integrity refusal of a received file without echoing a digest', () => {
    const sentence = comparisonReasonSentence(envelope('storage_integrity_error', { expected_sha256: 'x', actual_sha256: 'y' }));
    expect(sentence).toMatch(/^Принятый файл не совпал с заявленным/);
    expect(sentence).not.toContain('x');
  });
});
