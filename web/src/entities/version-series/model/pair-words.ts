/**
 * What a sheet pair of a transition says beside its status: why it needs a review, the declared changes of its permit, and how a
 * split sheet is covered (`CMP-SERIES-01` sections 3 and 4; the original's `status.py` reasons, `permit.py` states, `parts.py`).
 *
 * The contract carries the reasons as codes (`^[A-Z][A-Z0-9_]{2,63}$`), the permit as four states and the parts as a role and a
 * percentage. The words are the client's. A reason this table does not know is «причина не описана», its code stays in a `data-`
 * attribute and is never printed. This is the one complete table: the eight forcing reasons of the engine, the series'
 * (`SPLIT_SHEET`, `TABLE_GROUP`, `AI_MATCH`) and the unchecked channels. `widgets/comparison-viewer` says its reasons with
 * {@link pairReasonWords} too, instead of a table of its own.
 */

import type { ComparisonPartRole, ComparisonPartsCoverage, ComparisonPermitState } from '@/shared/api';

import { UNDESCRIBED_REASON } from './matrix-words';

/** The eight channels of the engine, in the original's words (`CHANNEL_LABELS`, `version-comparison.js:19-21`). */
export const CHANNEL_WORDS: Readonly<Record<string, string>> = {
  geometry: 'графика',
  color: 'цвет и оформление линий',
  text: 'текст',
  text_coverage: 'читаемость надписей',
  zones: 'служебные зоны',
  annotations: 'PDF-пометки',
  warnings: 'предупреждения',
  spec_positions: 'позиции СО',
};

export const PAIR_REASON_WORDS: Readonly<Record<string, string>> = {
  MATCH_LOW_CONFIDENCE: 'листы сопоставлены с низкой уверенностью',
  MATCH_AMBIGUOUS: 'сопоставление неоднозначно',
  ALIGNMENT_UNRELIABLE: 'совмещение листов ненадёжно',
  DUPLICATE_SHEET: 'лист повторяется в комплекте',
  RENDER_FAILED: 'лист не удалось отрисовать',
  NO_TEXT_LAYER: 'нет текстового слоя',
  STAMP_NOT_RECOGNIZED: 'штамп не распознан',
  SPEC_NOT_PARSED: 'спецификация не разобрана',
  SPLIT_SHEET: 'лист разделён между версиями: проверьте части',
  TABLE_GROUP: 'лист из группы листов таблицы',
  AI_MATCH: 'пара опирается на связь, предложенную ИИ',
};

const UNCHECKED = /^UNCHECKED_CHANNEL_([A-Z_]+)$/;

/** One reason in words. `UNCHECKED_CHANNEL_<CHANNEL>` is the series' form of the engine's «канал не проверен». */
export function pairReasonWords(code: string): string {
  const known = PAIR_REASON_WORDS[code];
  if (known !== undefined) return known;
  const channel = UNCHECKED.exec(code)?.[1]?.toLowerCase();
  if (channel !== undefined) {
    const word = CHANNEL_WORDS[channel];
    if (word !== undefined) return `не проверено: ${word}`;
  }
  return UNDESCRIBED_REASON;
}

/** «Заявлено проектировщиком в разрешении» and how each declared change fared (plan §1.1). */
export const PERMIT_STATE_LABELS: Readonly<Record<ComparisonPermitState, string>> = {
  declared_and_found: 'заявлено и найдено',
  declared_no_diff: 'заявлено, различий не найдено',
  diff_not_declared: 'найдено, но не заявлено',
  needs_review: 'нужна проверка',
};

export const PERMIT_HEADING = 'Заявлено проектировщиком в разрешении';

export const PART_ROLE_LABELS: Readonly<Record<ComparisonPartRole, string>> = {
  whole: 'лист целиком',
  part: 'часть листа',
};

function percent(value: number): string {
  return `${Math.round(value * 10) / 10} %`.replace('.', ',');
}

/** «часть листа · части вместе покрывают 61,5 % прежнего листа». */
export function partsLine(parts: ComparisonPartsCoverage): string {
  const role = PART_ROLE_LABELS[parts.role];
  return parts.role === 'part'
    ? `${role} · части вместе покрывают ${percent(parts.covered_percent)} прежнего листа`
    : `${role} · покрытие ${percent(parts.covered_percent)}`;
}
