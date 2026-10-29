/**
 * The words of the AI layer of «Сравнение версий» (wave C2): the state of a job and why it paused, the eleven states of a sheet's
 * description, the tiers of a value, the states of a specification comparison and of a report, the launch queue, and the
 * decisions the AI check of doubtful pairs reached.
 *
 * The contract sends codes; these tables are the only place that turns them into Russian, and every one is a `Record` over the
 * generated union, so a member the contract adds is a type error here and not a code on a screen. The original's own words are
 * kept where it has them (`version-comparison.js:870-878` `SPEC_STATE`, `SPEC_PHASE`, `UNIT_MARK`, `UNIT_STATE`;
 * `version-comparison-projects.js:355-357` `QSTATE`, `QITEM`; `validate.py:257-262` `STATE_LABELS`).
 *
 * **Every AI text is model output that an engineer has not confirmed** (`AGENTS.md` section 4; plan §3 `R-146ba` kept this label):
 * {@link UNCONFIRMED_LABEL} is the label, {@link RECORDED_LABEL} the one a recorded (test) answer carries instead of the pretence
 * of a model's description.
 */

import type {
  ComparisonAiCeiling,
  ComparisonAiCertainty,
  ComparisonAiConfidence,
  ComparisonAiExcludeReason,
  ComparisonAiJob,
  ComparisonAiJobState,
  ComparisonAiMethod,
  ComparisonAiPairDecision,
  ComparisonAiPairQuestionKind,
  ComparisonAiPauseReason,
  ComparisonAiSheetState,
  ComparisonAiSide,
  ComparisonAiTier,
  ComparisonLaunchEntryState,
  ComparisonLaunchQueueState,
  ComparisonReportKind,
  ComparisonReportSource,
  ComparisonReportStage,
  ComparisonReportState,
  ComparisonReportUnitMark,
  ComparisonReviewSheetKind,
  ComparisonSpecChangeKind,
  ComparisonSpecMethod,
  ComparisonSpecPhase,
  ComparisonSpecState,
} from '@/shared/api';

/** The label on every AI text (plan §1.1: «Every AI text carries the unconfirmed-by-an-engineer label»). */
export const UNCONFIRMED_LABEL = 'не подтверждено инженером';

/** The sentence under an AI text: what it is and what it is not (the original's `:561`, with the label this plan keeps). */
export const AI_TEXT_NOTE =
  'Текст составлен ИИ по изображению и тексту листа и инженером не подтверждён. Он не заменяет решение эксперта и не меняет результат сравнения листов.';

/** What a recorded (test) answer says of itself (our counterpart of «ТЕСТОВЫЙ ОТВЕТ подменного исполнителя», `sheet-changes.js:12`). */
export const RECORDED_LABEL = 'тестовый ответ';
export const RECORDED_NOTE =
  'Это тестовый ответ: он взят из записи, сделанной для проверки программы (режим подключения «запись»). Модель его не писала; не показывайте его как описание изменений.';

/** A job or a report whose route works in recorded mode answered from a recording (`ProviderMode`, `AI-JOBS-01` fact 5). */
export function isRecordedRoute(job: { readonly estimate: { readonly route: { readonly provider_mode: string } } } | undefined): boolean {
  return job?.estimate.route.provider_mode === 'recorded';
}

export const AI_METHOD_LABELS: Readonly<Record<ComparisonAiMethod, string>> = {
  pair_check: 'ИИ-проверка сомнительных пар',
  sheet_changes: 'ИИ-описание изменений',
  spec: 'Сравнение полных спецификаций',
  report: 'PDF-отчёт',
};

export const AI_JOB_STATE_LABELS: Readonly<Record<ComparisonAiJobState, string>> = {
  queued: 'в очереди',
  running: 'идёт',
  paused: 'пауза',
  completed: 'готово',
  failed: 'ошибка',
  cancelled: 'отменено',
};

/** A completed job with failed units is the original's «частично» (`ComparisonAiJobState`). */
export const AI_JOB_PARTIAL_LABEL = 'готово, есть ошибки';

export function aiJobStateLabel(job: Pick<ComparisonAiJob, 'state' | 'counts'>): string {
  return job.state === 'completed' && job.counts.failed > 0 ? AI_JOB_PARTIAL_LABEL : AI_JOB_STATE_LABELS[job.state];
}

export const AI_PAUSE_REASON_LABELS: Readonly<Record<ComparisonAiPauseReason, string>> = {
  user: 'остановлено по вашей просьбе',
  quota: 'лимит исчерпан: подписки или дневной потолок установки (50 долл.)',
  auth: 'исполнитель отказал в доступе',
  overrun: 'расход превысил оценку в 1,2 раза или потолок одного задания (10 долл.)',
  route_changed: 'назначение или ревизия подключения изменились после подтверждения',
  module_off: 'модуль «Сравнение версий» выключен',
};

/** After these two reasons a resume is a new spend and carries a new consent (`ResumeComparisonAiJobRequest`). */
export function pauseNeedsConsent(reason: ComparisonAiPauseReason | undefined): boolean {
  return reason === 'overrun' || reason === 'route_changed';
}

export const AI_PAUSE_ADVICE: Readonly<Record<ComparisonAiPauseReason, string>> = {
  user: '',
  quota: 'Подождите, пока обновится лимит подписки или наступит следующий день (потолок дня), и продолжите.',
  auth: 'Проверьте подключение исполнителя в разделе «Подключения», затем продолжайте.',
  overrun: 'Фактический расход превысил подтверждённую оценку больше чем в 1,2 раза либо потолок одного задания. Продолжить можно только с новой оценкой и новым подтверждением.',
  route_changed: 'Назначение или ревизия подключения изменились: прежнее подтверждение к ним не относится. Продолжить можно только с новой оценкой и новым подтверждением.',
  module_off: 'Включите модуль, затем продолжайте.',
};

/** The eleven states of «Изменения в листе» (`validate.py:257-262`; the contract's description of `ComparisonAiSheetState`). */
export const AI_SHEET_STATE_LABELS: Readonly<Record<ComparisonAiSheetState, string>> = {
  not_processed: 'Не обработано',
  queued: 'В очереди',
  running: 'В обработке',
  done: 'Готово',
  needs_clarification: 'Требуется уточнение',
  partial: 'Частично',
  no_construction_changes: 'Строительных изменений не выявлено',
  stale: 'Описание устарело',
  failed: 'Ошибка',
  cancelled: 'Отменено',
  engine_same: 'По данным сравнения изменений нет',
};

/** The state badge's tone for a sheet description (`.am-badge--<tone>`). */
export const AI_SHEET_STATE_TONES: Readonly<Record<ComparisonAiSheetState, 'ok' | 'degraded' | 'active' | 'inert' | 'failed' | 'pending'>> = {
  not_processed: 'pending',
  queued: 'active',
  running: 'active',
  done: 'ok',
  needs_clarification: 'degraded',
  partial: 'degraded',
  no_construction_changes: 'ok',
  stale: 'degraded',
  failed: 'failed',
  cancelled: 'inert',
  engine_same: 'inert',
};

/** A state in which a description exists to read (the rest have none or are being made). */
export function descriptionHasContent(state: ComparisonAiSheetState): boolean {
  return state === 'done' || state === 'needs_clarification' || state === 'partial' || state === 'no_construction_changes' || state === 'stale';
}

export const AI_TIER_LABELS: Readonly<Record<ComparisonAiTier, string>> = {
  from_text: 'по тексту листа',
  from_image: 'с изображения',
  unverified: 'не подтверждено',
};

export const AI_TIER_TITLES: Readonly<Record<ComparisonAiTier, string>> = {
  from_text: 'Значение найдено в текстовом слое своего листа.',
  from_image: 'Значение прочитано с изображения, в текстовом слое PDF его нет.',
  unverified: 'Значение не найдено ни в тексте своего листа, ни на указанном изображении.',
};

export const AI_CERTAINTY_LABELS: Readonly<Record<ComparisonAiCertainty, string>> = {
  confirmed: 'определено',
  unclear: 'неясно',
};

export const AI_CONFIDENCE_LABELS: Readonly<Record<ComparisonAiConfidence, string>> = {
  high: 'высокая',
  medium: 'средняя',
  low: 'низкая',
};

export const AI_SIDE_WORDS: Readonly<Record<ComparisonAiSide, string>> = {
  a: 'было',
  b: 'стало',
};

export const AI_CEILING_LABELS: Readonly<Record<ComparisonAiCeiling, string>> = {
  job: 'потолок одного задания (10 долл.)',
  day: 'потолок дня для установки (50 долл.)',
};

/** Why the program left an engine pointer out of the description («Не включено в сводку»). */
export const AI_EXCLUDE_REASON_LABELS: Readonly<Record<ComparisonAiExcludeReason, string>> = {
  service: 'служебная зона',
  formatting: 'только оформление',
  label_move: 'сдвиг надписи',
  revision_mark: 'отметка о выпуске',
  duplicate: 'повтор другого пункта',
  not_construction: 'не строительное изменение',
};

export const REVIEW_SHEET_KIND_LABELS: Readonly<Record<ComparisonReviewSheetKind, string>> = {
  to_check: 'Проверить',
  added: 'Лист добавлен',
  removed: 'Лист удалён',
};

export const REVIEW_SHEET_KIND_TITLES: Readonly<Record<ComparisonReviewSheetKind, string>> = {
  to_check: 'ИИ изменений не нашёл, но сравнение оставило пометки (например, пара листов сопоставлена неуверенно): посмотрите лист сами.',
  added: 'Пары в соседней версии нет: лист описан сам по себе.',
  removed: 'Пары в соседней версии нет: лист описан сам по себе.',
};

// ------------------------------------------------------------------------------ the doubtful pairs

export const PAIR_QUESTION_KIND_LABELS: Readonly<Record<ComparisonAiPairQuestionKind, string>> = {
  no_pair: 'у листа нет пары, в ячейке есть кандидаты',
  medium_pair: 'пара алгоритма с невысокой уверенностью',
};

/**
 * What the check of doubtful pairs made of one answer (`ComparisonAiPairDecision`), for a reader. `link_accepted` is the only
 * decision that shapes the matrix; the `hint_*` ones are shown and change nothing; a manual edit wins over every one of them.
 */
export const PAIR_DECISION_LABELS: Readonly<Record<ComparisonAiPairDecision, string>> = {
  link_accepted: 'ИИ поставил пару: ответ уверенный и подтверждён встречной проверкой',
  hint_table: 'подсказка: лист из таблицы нескольких листов, пару ставит только алгоритм',
  hint_confidence: 'подсказка: ИИ не уверен, пара не поставлена',
  hint_taken: 'подсказка: этот лист уже в паре по алгоритму',
  hint_shared: 'подсказка: два листа выбрали один и тот же, пара не поставлена',
  hint_reverse: 'подсказка: встречная проверка не подтвердила, пара не поставлена',
  none: 'ИИ: ни один кандидат не подходит',
  answer_mismatch: 'ответ отброшен: номер и страница в нём не совпали',
  failed: 'ИИ не дал пригодного ответа',
  medium_confirm: 'ИИ подтвердил пару алгоритма',
  medium_weak: 'ИИ подтвердил пару алгоритма, но неуверенно',
  medium_other: 'ИИ называет другой лист: пара алгоритма под сомнением',
  medium_none: 'ИИ считает, что ни один лист не подходит: пара алгоритма под сомнением',
};

// ------------------------------------------------------------------------------ specifications

export const SPEC_METHOD_LABELS: Readonly<Record<ComparisonSpecMethod, string>> = {
  whole: 'полное сравнение',
  sheet_ai: 'листовой ИИ',
};

export const SPEC_METHOD_TITLES: Readonly<Record<ComparisonSpecMethod, string>> = {
  whole: 'Спецификация каждой версии прочитана целиком, затем две сравнены независимо от порядка строк.',
  sheet_ai: 'Листы спецификации этого перехода описывает «ИИ-описание изменений» как обычные листы.',
};

export const SPEC_STATE_LABELS: Readonly<Record<ComparisonSpecState, string>> = {
  not_applicable: 'в переходе нет спецификации',
  not_started: 'не запускалось',
  running: 'идёт',
  paused: 'пауза',
  completed: 'готово',
  incomplete: 'неполно',
  failed: 'ошибка',
  cancelled: 'прервано — можно продолжить',
};

export const SPEC_PHASE_LABELS: Readonly<Record<ComparisonSpecPhase, string>> = {
  preparing: 'подготовка',
  comparing: 'сравнение',
  done: 'готово',
};

export const SPEC_CHANGE_KIND_LABELS: Readonly<Record<ComparisonSpecChangeKind, string>> = {
  changed: 'изменено',
  added: '+добавлено',
  removed: '−удалено',
  unclear: '?неясно',
  renumbered: 'переномеровано',
  moved: 'перенесено (не изменение)',
};

/** The nine fields of a position (GOST 21.110; the contract's `ComparisonSpecFieldChange.field`, an open word). */
export const SPEC_FIELD_LABELS: Readonly<Record<string, string>> = {
  pos: 'позиция',
  name: 'наименование',
  mark: 'марка',
  code: 'код',
  supplier: 'поставщик',
  unit: 'единица',
  quantity: 'количество',
  mass: 'масса',
  note: 'примечание',
};

export function specFieldLabel(field: string): string {
  return SPEC_FIELD_LABELS[field] ?? 'другое поле';
}

/** Reasons a specification comparison is incomplete or failed (engine-style codes, `ComparisonSpecification.reason`). */
export const SPEC_REASON_WORDS: Readonly<Record<string, string>> = {
  coverage_incomplete: 'модель разметила не весь текст спецификации',
  quote_not_found: 'цитата модели не найдена в тексте листа',
  value_not_found: 'значение модели не найдено в тексте листа',
  rows_unresolved: 'часть строк не удалось разобрать',
  side_unreadable: 'одну из спецификаций не удалось прочитать целиком',
  model_failed: 'модель не дала пригодного ответа',
};

export const SPEC_REASON_UNDESCRIBED = 'причина не описана';

export function specReasonWords(reason: string | undefined): string {
  if (reason === undefined || reason === '') return '';
  return SPEC_REASON_WORDS[reason] ?? SPEC_REASON_UNDESCRIBED;
}

// ------------------------------------------------------------------------------ the report

export const REPORT_KIND_LABELS: Readonly<Record<ComparisonReportKind, string>> = {
  client: 'Отчёт для заказчика · Изменения проектных решений',
  analytic: 'Аналитический отчёт',
};

export const REPORT_KIND_TITLES: Readonly<Record<ComparisonReportKind, string>> = {
  client:
    'Одно обращение к ИИ на переход по фактам сводки; программа отбрасывает каждый пункт, число, марка или направление которого факты не подтверждают; одна хронологическая таблица.',
  analytic: 'Аналитик, проверяющий и составитель: подробнее, для внутренней работы.',
};

export const REPORT_SOURCE_LABELS: Readonly<Record<ComparisonReportSource, string>> = {
  series_summary: 'сводка проекта',
  uploaded_md: 'загрузить MD-файл',
};

export const REPORT_STATE_LABELS: Readonly<Record<ComparisonReportState, string>> = {
  draft: 'черновик: оценка готова, ничего не отправлено',
  queued: 'в очереди',
  running: 'идёт',
  paused: 'пауза',
  completed: 'готово',
  partial: 'неполный результат',
  failed: 'ошибка',
  cancelled: 'отменено',
};

export const REPORT_STAGE_LABELS: Readonly<Record<ComparisonReportStage, string>> = {
  intake: 'файл принят, подготовка',
  transition_analysis: 'анализ переходов',
  verification: 'проверка выводов',
  composition: 'составление отчёта',
  client_writing: 'написание текста для заказчика',
  pdf_writing: 'формирование PDF',
};

export const UNIT_MARKS: Readonly<Record<ComparisonReportUnitMark, { readonly mark: string; readonly word: string }>> = {
  done: { mark: '✓', word: 'готово' },
  running: { mark: '⟳', word: 'идёт' },
  failed: { mark: '✗', word: 'брак' },
  pending: { mark: '·', word: 'ждёт' },
};

export const REPORT_ARTIFACT_LABELS = {
  report_pdf: 'PDF',
  source_md: 'исходный MD',
} as const;

// ------------------------------------------------------------------------------ the launch queue

export const LAUNCH_QUEUE_STATE_LABELS: Readonly<Record<ComparisonLaunchQueueState, string>> = {
  running: 'идёт',
  paused: 'на паузе',
  failed: 'ошибка — процесс остановлен',
  done: 'выполнена',
  idle: 'пусто',
};

export const LAUNCH_ENTRY_STATE_LABELS: Readonly<Record<ComparisonLaunchEntryState, string>> = {
  waiting: 'ждёт',
  running: 'идёт',
  needs_consent: 'ждёт подтверждения',
  done: 'готово',
  skipped: 'пропуск',
  failed: 'ошибка',
};
