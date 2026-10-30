/**
 * The words of the sheet matrix: a cell, its flags, why a sheet was not matched, a row's status badge, and
 * the state of the whole matrix (`version-comparison.js:9-16` statuses, `:372-409` cells,
 * `version_comparison/resolve.py:43-57` and `lineage.py:631-646` reasons).
 *
 * The contract sends codes (`ComparisonCellConfidence`, `ComparisonCellFlag`, the reason of a cell) and
 * these tables are the only place that turns them into Russian. A reason this table does not know is shown
 * as «причина не описана»; its code stays in a `data-` attribute and is never printed.
 */

import type {
  ComparisonCellConfidence,
  ComparisonCellFlag,
  ComparisonCellState,
  ComparisonMatrixEditKind,
  ComparisonMatrixEditSource,
  ComparisonMatrixEditStatus,
  ComparisonMatrixStaleReason,
  ComparisonMatrixState,
  ComparisonSheetStatus,
} from '@/shared/api';

export const CELL_STATE_LABELS: Readonly<Record<ComparisonCellState, string>> = {
  matched: 'сопоставлен',
  unmatched: 'не сопоставлен',
  absent: 'нет в версии',
};

/** The mark a confidence puts on a thumbnail, or `null` for the ordinary one, and what the mark means. */
export const CONFIDENCE_MARKS: Readonly<Record<ComparisonCellConfidence, { readonly mark: string | null; readonly title: string }>> = {
  high: { mark: null, title: 'Сопоставлено уверенно.' },
  medium: { mark: '?', title: 'Сопоставлено с невысокой уверенностью.' },
  group: { mark: '▤ группа', title: 'Лист из группы листов таблицы: строки перенесены между листами.' },
  manual: { mark: '✎', title: 'Связь задана вручную.' },
  ai: { mark: 'ИИ', title: 'Связь предложена ИИ и принята проверкой. Это не решение эксперта.' },
};

export const FLAG_MARKS: Readonly<Record<ComparisonCellFlag, { readonly mark: string; readonly title: string }>> = {
  duplicate: { mark: '⧉', title: 'Дубль листа: то же содержание стоит на нескольких страницах.' },
  scan: {
    mark: 'скан',
    title: 'Скан: страница — картинка, текст не извлекается и не сравнивается; сравнивается только изображение.',
  },
  split: { mark: '◫', title: 'Лист разделён между версиями.' },
  bridge: { mark: '↷', title: 'Связь проведена через версию, в которой этого листа нет.' },
};

export const SPLIT_PART_MARK = {
  mark: '◫',
  title: 'Часть листа, разделённого в этой версии: сравнивается своя область.',
};
export const SPLIT_WHOLE_MARK = {
  mark: '⇉',
  title: 'Лист разделён в следующей версии на части.',
};

/** The reasons a sheet was not matched or a cell is empty (`REASON_LABELS`, `resolve.py:43-57`). */
export const CELL_REASON_WORDS: Readonly<Record<string, string>> = {
  twin: 'одинаковые страницы-двойники: текст и изображение не различают, положение в файле тоже',
  twin_sheet: 'одинаковые по содержанию листы с разными номерами в штампе: номер листа не совпал ни с одним',
  block: 'перенос строк таблицы между листами — связь блока, а не пара 1:1',
  weak: 'отличительных признаков недостаточно',
  taken: 'содержание указывает на уже связанный лист',
  not_mutual: 'встречная проверка указывает на другой лист',
  below_pair: 'сходство ниже порога пары',
  package: 'разные комплекты: обозначения противоречат установленным парам',
  no_evidence: 'нет текста, изображение не различает',
  title_conflict: 'содержание указывает на лист с другим названием, а лист с тем же названием есть',
  title_only: 'совпадает только название листа, содержание не подтверждает',
  page_no_conflict: 'номер страницы отчёта не однозначен',
  permit: 'листы разных разрешений на внесение изменений или разрешение и обычный лист',
  candidates_left: 'в версии есть несвязанные страницы-кандидаты',
  no_candidates: 'сопоставление выполнено, кандидатов не осталось',
  marked_absent: 'отмечено вручную: этого листа в версии нет',
  edited: 'ячейку освободила ручная правка',
};

export const UNDESCRIBED_REASON = 'причина не описана';

export function cellReasonWords(reason: string | undefined): string {
  if (reason === undefined || reason === '') return '';
  return CELL_REASON_WORDS[reason] ?? UNDESCRIBED_REASON;
}

/** The status badge of a row once a transition was compared (`STATUS`, `version-comparison.js:9-16`). */
export const SHEET_STATUS_BADGES: Readonly<
  Record<ComparisonSheetStatus, { readonly label: string; readonly icon: string; readonly tone: string }>
> = {
  same: { label: 'Совпадает', icon: '✓', tone: 'ok' },
  same_zones_changed: { label: 'Совпадает, изменены служебные зоны', icon: '◐', tone: 'degraded' },
  different: { label: 'Есть отличия', icon: '●', tone: 'active' },
  needs_review: { label: 'Нужна проверка', icon: '⚠', tone: 'degraded' },
  added: { label: 'Лист добавлен', icon: '+', tone: 'inert' },
  removed: { label: 'Лист удалён', icon: '−', tone: 'inert' },
  unmatched: { label: 'Не сопоставлен', icon: '⁇', tone: 'degraded' },
};

export const MATRIX_STATE_LABELS: Readonly<Record<ComparisonMatrixState, string>> = {
  absent: 'Сопоставление листов ещё не собиралось',
  building: 'Идёт разбор версий и сопоставление листов',
  ready: 'Сопоставление актуально',
  stale: 'Сопоставление устарело',
  failed: 'Не удалось подготовить версии',
};

export const MATRIX_STALE_LABELS: Readonly<Record<ComparisonMatrixStaleReason, string>> = {
  order_changed: 'порядок версий изменился',
  profiles_changed: 'версии или правила разбора изменились',
  // `CMP-SEAL-C2`: the matching algorithm or its rule set is not the one the build was made with.
  algorithm_changed: 'алгоритм или правила сопоставления изменились',
};

export const EDIT_KIND_LABELS: Readonly<Record<ComparisonMatrixEditKind, string>> = {
  link: 'связь листов',
  unlink: 'отвязка листа в отдельную строку',
  mark_absent: 'отметка «листа в версии нет»',
  undo: 'отмена правки',
};

export const EDIT_STATUS_LABELS: Readonly<Record<ComparisonMatrixEditStatus, string>> = {
  applied: 'действует',
  undone: 'отменена',
  orphaned: 'больше не применяется: листов, о которых она, нет в текущем порядке',
};

export const EDIT_SOURCE_LABELS: Readonly<Record<ComparisonMatrixEditSource, string>> = {
  expert: 'эксперт',
  migrated_sheet_link: 'перенесена из подтверждённых пар прежнего экрана',
};

export const PAIR_STATE_LABELS = {
  queued: 'в очереди',
  computing: 'считается…',
  done: 'готово',
  failed: 'ошибка расчёта',
} as const;
