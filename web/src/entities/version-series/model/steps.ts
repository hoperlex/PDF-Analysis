/**
 * The seven steps of «Проекты и этапы» and the words a cell of the table says about each state
 * (`frontend/static/js/version-comparison-projects.js:6-16` for the steps, `:41-94` `stageView`
 * for the words, `:15-16` for the tones and icons).
 *
 * The contract gives each step a state code (`ComparisonStepState`) and the figures the original's
 * note quotes (`ComparisonStepCounts`); the Russian is this file's. A state a step has no word of its
 * own for gets the generic word of the state, so no code is ever printed. Steps 4, 6 and 7 belong to
 * wave C2: the table has no column for them (see {@link LATER_STEPS}), but the next-step chip may
 * still name them, so they have a label here.
 */

import type { ComparisonStepCounts, ComparisonStepId, ComparisonStepState } from '@/shared/api';

export const STEP_LABELS: Readonly<Record<ComparisonStepId, string>> = {
  upload: 'Загрузка',
  profile: 'Разбор версий',
  matrix: 'Сопоставление листов',
  ai_pairs: 'ИИ-проверка сомнительных пар',
  series: 'Сравнение соседних',
  ai_changes: 'ИИ-описание изменений',
  report: 'Сводка и отчёт',
};

/** The number the original prints before each step (`STAGES[].num`). */
export const STEP_NUMBERS: Readonly<Record<ComparisonStepId, number>> = {
  upload: 1,
  profile: 2,
  matrix: 3,
  ai_pairs: 4,
  series: 5,
  ai_changes: 6,
  report: 7,
};

/** What each step means, said under its header (`STAGES[].hint`, `:6-16`). */
export const STEP_HINTS: Readonly<Record<ComparisonStepId, string>> = {
  upload: 'Все версии PDF комплекта загружены в раздел.',
  profile: 'Система прочитала каждую версию: какие в ней листы, их номера и названия по штампу.',
  matrix:
    'Таблица «какой лист одной версии соответствует какому листу другой». «Не сопост.» — листы, которые алгоритм не связал уверенно.',
  ai_pairs: 'ИИ смотрит только листы, которые алгоритм не связал уверенно, и ставит пару или подсказку.',
  series: 'Каждая версия сравнивается со следующей (№1→№2, №2→№3 …) по изображению листов. ИИ не используется.',
  ai_changes: 'ИИ описывает словами изменения на листах и собирает «Сводку изменений (MD)».',
  report: '«Сводка изменений (MD)» — все изменения комплекта одним файлом; PDF-отчёт — короткий анализ по этой сводке.',
};

/** The columns the table draws: steps 1, 2, 3 and 5. */
export const SHOWN_STEPS = ['upload', 'profile', 'matrix', 'series'] as const satisfies readonly ComparisonStepId[];
export type ShownStep = (typeof SHOWN_STEPS)[number];

/** The steps of wave C2 (4, 6, 7): no column, and the screen says so. */
export const LATER_STEPS = ['ai_pairs', 'ai_changes', 'report'] as const satisfies readonly ComparisonStepId[];

export const LATER_STEPS_NOTE =
  'Шаги 4 «ИИ-проверка сомнительных пар», 6 «ИИ-описание изменений» и 7 «Сводка и отчёт» появятся позже: в таблице их столбцов пока нет.';

export type StepTone = 'ok' | 'warn' | 'run' | 'todo' | 'bad' | 'off';

/** The icon the original draws for each tone (`ICON`, `:16`). */
export const TONE_ICONS: Readonly<Record<StepTone, string>> = {
  ok: '✓',
  warn: '!',
  run: '⟳',
  todo: '○',
  bad: '✕',
  off: '·',
};

/** The `.am-badge` tone class for each of the original's tones. */
export const TONE_BADGES: Readonly<Record<StepTone, string>> = {
  ok: 'ok',
  warn: 'degraded',
  run: 'active',
  todo: 'pending',
  bad: 'failed',
  off: 'inert',
};

const TONES: Readonly<Record<ComparisonStepState, StepTone>> = {
  not_started: 'todo',
  queued: 'run',
  running: 'run',
  pausing: 'run',
  paused: 'warn',
  interrupted: 'warn',
  done: 'ok',
  partial: 'warn',
  stale: 'warn',
  attention: 'warn',
  failed: 'bad',
  blocked: 'off',
  not_applicable: 'off',
};

/** The word of a state when the step has none of its own. */
const GENERIC_WORDS: Readonly<Record<ComparisonStepState, string>> = {
  not_started: 'не запускалось',
  queued: 'в очереди',
  running: 'идёт',
  pausing: 'на паузу…',
  paused: 'пауза',
  interrupted: 'прервано',
  done: 'готово',
  partial: 'частично',
  stale: 'устарело',
  attention: 'есть что проверить',
  failed: 'ошибка',
  blocked: 'ждёт предыдущего шага',
  not_applicable: '—',
};

/** The original's own words per step (`stageView`), where they differ from the generic ones. */
const STEP_WORDS: Readonly<Partial<Record<ComparisonStepId, Partial<Record<ComparisonStepState, string>>>>> = {
  upload: { done: 'загружен', not_started: 'не загружен' },
  profile: { done: 'готов', running: 'идёт', not_started: 'не начат', failed: 'ошибка' },
  matrix: { done: 'готово', stale: 'устарело', not_started: 'не собрано' },
  series: { done: 'готово', not_started: 'не запускалось', stale: 'по старому порядку', interrupted: 'прервано' },
};

export interface StepView {
  readonly text: string;
  readonly note: string;
  readonly tone: StepTone;
  readonly icon: string;
  /** The longer explanation, for a `title`. */
  readonly title: string;
}

function figure(value: number | undefined): number {
  return value ?? 0;
}

/** Whether a step state means that something is being computed right now. */
export function isRunningState(state: ComparisonStepState): boolean {
  return state === 'queued' || state === 'running' || state === 'pausing';
}

/**
 * The chip, the note and the tone of one cell. `counts` are the figures the contract names; a figure
 * the server did not send prints nothing (never a `0` that nothing computed).
 */
export function stepView(step: ComparisonStepId, state: ComparisonStepState, counts?: ComparisonStepCounts): StepView {
  const own = STEP_WORDS[step]?.[state];
  let text = own ?? GENERIC_WORDS[state];
  let note = '';
  let title = '';
  if (step === 'upload') {
    if (counts?.total !== undefined) note = `файлов ${counts.total}`;
  } else if (step === 'profile') {
    if (counts?.total !== undefined) {
      note = `${figure(counts.ready)} из ${counts.total}` + (figure(counts.failed) > 0 ? ` · ошибок ${figure(counts.failed)}` : '');
    }
    if (state === 'not_started') title = 'Разбор ещё не запускался — «Подготовить» в столбце сопоставления.';
    if (figure(counts?.failed) > 0) title = 'Разбор части версий закончился ошибкой — «Повторить».';
  } else if (step === 'matrix') {
    if (state === 'attention') text = `не сопост. ${figure(counts?.unmatched)}`;
    if (counts?.rows !== undefined && state !== 'not_applicable') {
      note = `строк ${counts.rows}` + (figure(counts.manual_edits) > 0 ? ` · ✎ ${figure(counts.manual_edits)}` : '');
    }
    if (state === 'attention') {
      title = `Не сопоставлено ячеек: ${figure(counts?.unmatched)}. Разберите их на вкладке «Сравнение листов».`;
    } else if (state === 'stale') {
      title = 'Версии или их порядок изменились — «Подготовить» пересоберёт сопоставление.';
    } else if (state === 'not_started') {
      title = 'Сопоставление ещё не собиралось — «Подготовить».';
    }
  } else if (step === 'series') {
    if (state !== 'not_applicable' && counts?.total !== undefined) {
      note =
        `${figure(counts.done)} из ${counts.total}` +
        (state === 'done' && counts.with_changes !== undefined ? ` · с изм. ${counts.with_changes}` : '');
      title = `Переходов посчитано: ${figure(counts.done)} из ${counts.total}`;
      if (counts.with_changes !== undefined) title += `; с изменениями: ${counts.with_changes}`;
    }
    if (state === 'stale') {
      title = 'Сводка посчитана для прежнего порядка или состава версий — нужно «Заново» в столбце «Сравнение соседних».';
    }
  }
  const tone = TONES[state];
  return { text, note, tone, icon: TONE_ICONS[tone], title };
}

/** How far along a state is, for sorting a column: the cells that need attention first. */
export function stepRank(state: ComparisonStepState): number {
  const order: readonly ComparisonStepState[] = [
    'failed', 'interrupted', 'attention', 'stale', 'paused', 'partial', 'not_started', 'blocked',
    'queued', 'running', 'pausing', 'done', 'not_applicable',
  ];
  return order.indexOf(state);
}
