/**
 * The words of «Модели по этапам» (`HOSTS-WEB-01`, ADR-0028, plan 2026-11-09 §4 and §7.4).
 *
 * Every table is a `Record` over the contract's own value set, so a value the contract adds is a type error here until it has a
 * Russian sentence. The contract value stays in a `data-` attribute; the screen says it in Russian.
 */

import type { ComparisonLayoutKind, ModelEffort, StageCellRole, StageModelKit, StageRowKey } from '@/shared/api';

export const STAGE_MODELS_TITLE = 'Модели по этапам';

/**
 * The six rows, in the order the original lists them. «Критик» and «Уточнение» belong to the extended review of the third
 * version, and «Комплексная сверка» to both extended versions; the table lists all six whatever the run is.
 */
export const STAGE_ROW_LABELS: Readonly<Record<StageRowKey, string>> = {
  text: 'Анализ текста',
  blocks: 'Анализ блоков',
  cross_check: 'Комплексная сверка',
  norms: 'Нормы',
  review: 'Критик',
  correction: 'Уточнение',
};

/** The part a cell plays in its row; `main` is the single answer and is not named. */
export const STAGE_ROLE_LABELS: Readonly<Record<StageCellRole, string>> = {
  main: '',
  leg1: 'первая ветка',
  leg2: 'вторая ветка',
  judge: 'судья',
};

/** The sets, as the original names them; «Свой набор» is any edit of one. */
export const STAGE_KIT_LABELS: Readonly<Record<StageModelKit, string>> = {
  claude_only: 'Только Claude',
  codex_only: 'Только Codex',
  custom: 'Свой набор',
};

/** The effort a model is asked for. The contract offers three: nothing above `high`, and no `low` for Opus. */
export const STAGE_EFFORT_LABELS: Readonly<Record<ModelEffort, string>> = {
  low: 'низкое',
  medium: 'среднее',
  high: 'высокое',
};

/**
 * The four kinds of work of the comparison of versions that call a model (`HOSTS-CMP-01`, web part `CMP-WEB-01`), in the order the
 * server lists them. The contract value stays in `data-comparison-kind`; the screen says it in Russian.
 */
export const COMPARISON_KIND_LABELS: Readonly<Record<ComparisonLayoutKind, string>> = {
  comparison_pair_check: 'Пары листов',
  comparison_sheet_changes: 'Изменения листов',
  comparison_spec: 'Спецификация',
  comparison_report: 'Отчёт',
};

export const COMPARISON_GROUP_TITLE = 'Сравнение версий';
export const COMPARISON_KIND_HEADER = 'Вид работы';
/** Said when a «Свой набор» revision holds no model for the comparison: it is refused, never served by a model nobody chose. */
export const COMPARISON_NONE_NOTE = 'Сравнения версий не запустятся, пока модели не выбраны.';
export const COMPARISON_NOT_CHOSEN = 'не выбрана';
export const COMPARISON_NO_EFFORT = '—';
export const COMPARISON_PARTIAL_PROBLEM = 'Для сравнения версий выберите модель во всех четырёх строках или ни в одной.';
export const COMPARISON_PAIR_PROBLEM = 'Для одной из строк сравнения версий выбрано сочетание модели и усилия, которого нет в каталоге.';

export const NO_LAYOUT = 'Набор моделей ещё не задан.';
export const NO_LAYOUT_ADMIN = 'Набор моделей ещё не задан. Нажмите «Изменить», чтобы выбрать модели по этапам.';
export const NOT_ON_SERVERS = '⚠ нет на серверах';
export const NOT_ON_SERVERS_HINT = 'Ни один включённый сервер сейчас не может ответить этой моделью.';

export const LAYOUT_OFF_NOTE =
  'Набор не применяется: он выключен, прогоны идут по прежним правилам. Включает его администратор в «Расширенных».';
export const LAYOUT_ON_NOTE = 'Набор применяется к прогонам, которые начинаются сейчас.';

export const EDIT_LABEL = 'Изменить';
export const SAVE_LABEL = 'Сохранить набор';
export const CANCEL_LABEL = 'Отменить';
export const KIT_LEGEND = 'Набор';
export const ROW_MODEL_LABEL = 'Модель';
export const ROW_EFFORT_LABEL = 'Усилие';
/** The blocks row is one of three schemes, chosen whole (`HOSTS-ENSEMBLE-01`); its legs and judge are never edited one by one. */
export const BLOCKS_SCHEME_LABEL = 'Схема';
export const BLOCKS_SCHEME_UNLISTED = 'не из списка';
export const BLOCKS_SCHEME_PROBLEM = 'Для блоков выберите одну из схем: другого сочетания моделей сервер не примет.';
export const NO_AVAILABLE_MODELS =
  'Выбирать пока не из чего: ни одна модель каталога не доступна на серверах. Подключите сервер на вкладке «Серверы».';

export const SWITCH_LABEL = 'Модели по этапам: включены';
export const SWITCH_HINT =
  'Включённый набор применяется к прогонам, которые начинаются после этого; начатые доходят по старому. Пока он выключен, прогоны идут по прежним правилам.';
export const SWITCH_NEEDS_REVISION = 'Включить нельзя: набор моделей ещё не сохранён.';
export const JOURNAL_TITLE = 'Журнал переключателя';
export const JOURNAL_EMPTY = 'Переключатель ещё не менялся.';
export const HISTORY_TITLE = 'Прежние версии набора';
export const HISTORY_EMPTY = 'Прежних версий нет.';
