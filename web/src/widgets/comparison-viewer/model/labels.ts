/**
 * The words of the sheet viewer, in Russian (`CMP-VIEWER-01`, plan §1.1).
 *
 * Every label is the original's where it had one (`frontend/static/js/version-comparison.js:9-21`,
 * `version-comparison-viewer.js:8-23`), so an engineer who knows the original reads the same words. The contract's
 * enums are English identifiers; nothing here renders one.
 */

import type {
  ComparisonChannelState,
  ComparisonLayer,
  ComparisonNoteChange,
  ComparisonSheetStatus,
} from '@/shared/api';

/**
 * The two sheets of a pair, in the words «было» and «стало» that the matrix and the transitions use. The contract and the
 * engine call them A and B; the reader sees no letter. «Было» is the older sheet, «стало» the newer one.
 */
export const SIDE_WORDS = { a: 'Было', b: 'Стало' } as const;
export type Side = keyof typeof SIDE_WORDS;

/** The eight layers of the overlay, with the words of `ComparisonLayer`'s description. */
export const LAYER_LABELS: Readonly<Record<ComparisonLayer, string>> = {
  main: 'Основное',
  light_elements: 'Светлые элементы',
  color_change: 'Места, где изменился цвет',
  line_style: 'Оформление линий',
  moved: 'Перемещено (сдвиг — не изменение)',
  within_tolerance: 'В пределах допуска',
  noise: 'Шум',
  service_zones: 'Служебные зоны',
};

/** The layers in the order the viewer lists them. */
export const LAYER_ORDER: readonly ComparisonLayer[] = [
  'main',
  'light_elements',
  'color_change',
  'line_style',
  'moved',
  'within_tolerance',
  'noise',
  'service_zones',
];

/**
 * Which layers are drawn when the viewer opens: the original's `LAYERS` (`version-comparison-viewer.js:15-23`) —
 * «Основное», «Светлые элементы», «Места, где изменился цвет», «Оформление линий» and «Служебные зоны» on;
 * «Перемещено», «В пределах допуска» and «Шум» off.
 */
export const DEFAULT_LAYERS: readonly ComparisonLayer[] = [
  'main',
  'light_elements',
  'color_change',
  'line_style',
  'service_zones',
];

/** The eight channels (`version-comparison.js:19-21`). */
export const CHANNEL_LABELS: Readonly<Record<string, string>> = {
  geometry: 'графика',
  color: 'цвет и оформление линий',
  text: 'текст',
  text_coverage: 'читаемость надписей',
  zones: 'служебные зоны',
  annotations: 'PDF-пометки',
  warnings: 'предупреждения',
  spec_positions: 'позиции СО',
};

/** The order the strip lists the channels in. */
export const CHANNEL_ORDER: readonly string[] = [
  'geometry',
  'color',
  'text',
  'text_coverage',
  'zones',
  'annotations',
  'warnings',
  'spec_positions',
];

export const CHANNEL_STATE_WORDS: Readonly<Record<ComparisonChannelState, string>> = {
  checked: 'проверено',
  unchecked: 'не проверено',
  not_applicable: 'не применимо',
};

/** The sheet statuses (`version-comparison.js:9-16`). */
export const STATUS_LABELS: Readonly<Record<ComparisonSheetStatus, string>> = {
  same: 'Совпадает',
  same_zones_changed: 'Совпадает, изменены служебные зоны',
  different: 'Есть отличия',
  needs_review: 'Нужна проверка',
  added: 'Лист добавлен',
  removed: 'Лист удалён',
  unmatched: 'Не сопоставлен',
};

/** The region classes of a difference (`CLASS_LABELS`, `version-comparison-viewer.js:8-12`). */
export const REGION_CLASS_LABELS: Readonly<Record<string, string>> = {
  text: 'Текст',
  text_moved: 'Сдвиг надписи',
  graphic_added: 'Графика: добавлено (стало)',
  graphic_removed: 'Графика: удалено (было)',
  graphic_changed: 'Графика: изменено',
  color_change: 'Изменение цвета',
  light_fill: 'Светлая заливка / штриховка',
  line_style: 'Оформление линии: толщина, тон, наложение',
  block_moved: 'Блок перемещён',
  shifted: 'Сдвиг: тот же элемент на другом месте',
};

/** A class the engine added that this table does not know yet: said, not guessed. */
export const UNKNOWN_REGION_CLASS_LABEL = 'Другое отличие';

/** Classes that are a shift, not a change: hidden from the list by default (`SHIFT_CLASSES`, `engine.py:28`). */
export const SHIFT_CLASSES: readonly string[] = ['text_moved', 'block_moved', 'shifted'];

/** The class that is the look of a line, not its place or content: hidden from the list by default. */
export const STYLE_ONLY_CLASS = 'line_style';

export function regionClassLabel(regionClass: string): string {
  return REGION_CLASS_LABELS[regionClass] ?? UNKNOWN_REGION_CLASS_LABEL;
}

/**
 * The kinds of change in the service zones (`ComparisonServiceNote`), each with the grammatical gender its past
 * participle agrees with: «Штамп изменён», «Предупреждение удалено», «PDF-пометка добавлена».
 */
export type Gender = 'masculine' | 'feminine' | 'neuter';

export const NOTE_KINDS: Readonly<Record<string, { readonly label: string; readonly gender: Gender }>> = {
  stamp: { label: 'Штамп', gender: 'masculine' },
  warning: { label: 'Предупреждение', gender: 'neuter' },
  qr: { label: 'Матричный код', gender: 'masculine' },
  field: { label: 'Поле', gender: 'neuter' },
  annotation: { label: 'PDF-пометка', gender: 'feminine' },
};
export const UNKNOWN_NOTE_KIND = { label: 'Служебная пометка', gender: 'feminine' } as const;

const NOTE_CHANGES: Readonly<Record<ComparisonNoteChange, Readonly<Record<Gender, string>>>> = {
  added: { masculine: 'добавлен', feminine: 'добавлена', neuter: 'добавлено' },
  removed: { masculine: 'удалён', feminine: 'удалена', neuter: 'удалено' },
  changed: { masculine: 'изменён', feminine: 'изменена', neuter: 'изменено' },
};

/** «Предупреждение удалено», «PDF-пометка добавлена»: the kind and what happened to it, in agreement. */
export function noteTitle(kind: string, change: ComparisonNoteChange): string {
  const known = NOTE_KINDS[kind] ?? UNKNOWN_NOTE_KIND;
  return `${known.label} ${NOTE_CHANGES[change][known.gender]}`;
}

/** The kinds of change in a text fragment. */
export const TEXT_KIND_LABELS: Readonly<Record<string, string>> = {
  replaced: 'Изменён',
  added: 'Добавлен',
  removed: 'Удалён',
  moved: 'Сдвинут',
};
export const UNKNOWN_TEXT_KIND_LABEL = 'Изменение текста';

export const WARNING_NOTE = 'Исчезновение предупреждения не подтверждает согласования.';
export const SCAN_NOTE = 'изображение без текста: надписи не читаются и сравниваются только как картинка';
export const SPLIT_PART_NOTE = 'Новый лист — часть прежнего листа';
export const SPLIT_WHOLE_NOTE = 'Новый лист — весь прежний лист, составленный из частей';

/**
 * Where a service note happened (`ComparisonServiceNote.zone`) and what it is about (`field`), in words. The contract keeps
 * them free text of at most 64 characters; these are the values the engine writes today (`engine/child/job.py`,
 * `annotations.py`). A value this table does not know is said as «другая зона» / «другое поле», never printed.
 */
export const ZONE_WORDS: Readonly<Record<string, string>> = {
  stamp: 'штамп',
  release_stamp: 'отметка о выпуске',
  qr: 'матричный код',
  annotations: 'PDF-пометки',
  margin: 'поля листа',
};
export const UNKNOWN_ZONE_WORD = 'другая зона';

const STAMP_FIELD_WORDS: Readonly<Record<string, string>> = {
  designation: 'обозначение',
  sheet_title: 'название листа',
  sheet_number: 'номер листа',
  revision_number: 'номер последнего изменения',
  release_date: 'дата выпуска',
  images: 'подписи (изображения в штампе)',
};
const RELEASE_FIELD_WORDS: Readonly<Record<string, string>> = { date: 'дата', text: 'текст отметки' };
const QR_FIELD_WORDS: Readonly<Record<string, string>> = { qr: 'содержимое кода' };
/** The subtype of a PDF annotation is its field (`/Highlight`, `/FreeText`, …). */
const ANNOTATION_FIELD_WORDS: Readonly<Record<string, string>> = {
  Text: 'заметка',
  FreeText: 'текст на листе',
  Highlight: 'выделение',
  Underline: 'подчёркивание',
  StrikeOut: 'зачёркивание',
  Squiggly: 'волнистая линия',
  Stamp: 'штамп-пометка',
  Square: 'прямоугольник',
  Circle: 'окружность',
  Line: 'линия',
  Polygon: 'многоугольник',
  PolyLine: 'ломаная линия',
  Ink: 'рисунок от руки',
  Caret: 'вставка',
  Link: 'ссылка',
  FileAttachment: 'вложенный файл',
  Popup: 'всплывающее окно',
  Redact: 'редактирование',
};
export const UNKNOWN_FIELD_WORD = 'другое поле';

const FIELD_WORDS_BY_ZONE: Readonly<Record<string, Readonly<Record<string, string>>>> = {
  stamp: STAMP_FIELD_WORDS,
  release_stamp: RELEASE_FIELD_WORDS,
  qr: QR_FIELD_WORDS,
  annotations: ANNOTATION_FIELD_WORDS,
};

export function zoneWords(zone: string): string {
  return ZONE_WORDS[zone] ?? UNKNOWN_ZONE_WORD;
}

/** The field is named within its zone: `date` of the release mark is not the stamp's date. */
export function fieldWords(zone: string | undefined, field: string): string {
  const own = zone === undefined ? undefined : FIELD_WORDS_BY_ZONE[zone]?.[field];
  return own ?? STAMP_FIELD_WORDS[field] ?? UNKNOWN_FIELD_WORD;
}

/**
 * «Алгоритм» of «Как сравнивалось»: the engine's version string is machine text (`cmp-engine/1`), so the reader is given its
 * number («версия 1») and the string itself stays in a `data-` attribute for whoever has to quote it.
 */
export function algorithmWords(version: string): string {
  const number = /(\d+(?:\.\d+)*)$/.exec(version)?.[1];
  return number === undefined ? 'версия не указана' : `версия ${number}`;
}
