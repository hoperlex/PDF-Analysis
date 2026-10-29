/**
 * The side panel «Изменения в листе» as a reader sees it (`version-comparison-sheet-changes.js`, plan §1.1): the change lines
 * «Было» → «стало», the text «Скопировать» puts on the clipboard, and the evidence the panel hands to the viewer's banner
 * («Из ИИ-описания: …», «доказательство N из M», «Обзор всех / Один фрагмент», `version-comparison-viewer.js:36-52`).
 *
 * **Every line here is model output that an engineer has not confirmed.** Nothing in this file turns an AI value into a fact:
 * a value whose tier is `unverified` keeps its mark «не подтверждено», one read `from_image` says so, and the copied text ends
 * with the label. The raw comparison of the pair is never rewritten by the description (`AGENTS.md` section 4).
 */

import type { ComparisonAiChange, ComparisonAiSide, ComparisonBox, ComparisonSheetDescription } from '@/shared/api';

import { UNCONFIRMED_LABEL } from './ai-words';

/** «Было: «КЛ-3»» or «Не было»; the original's `quote` (`:210`). */
function quote(value: string | undefined): string {
  return value === undefined || value === '' ? '—' : `«${value}»`;
}

export function wasText(change: Pick<ComparisonAiChange, 'was'>): string {
  return change.was === undefined || change.was === '' ? 'Не было' : `Было: ${quote(change.was)}`;
}

export function nowText(change: Pick<ComparisonAiChange, 'now'>): string {
  return change.now === undefined || change.now === '' ? 'Не стало' : `Стало: ${quote(change.now)}`;
}

/** «Было: «…» → Стало: «…»» — the first line of a change (`leads`, `:179-207`). */
export function leadLine(change: Pick<ComparisonAiChange, 'was' | 'now'>): string {
  return `${wasText(change)} → ${nowText(change)}`;
}

export interface Evidence {
  readonly id: string;
  readonly label: string;
  readonly side: ComparisonAiSide;
  readonly box: ComparisonBox;
}

/**
 * The evidence of a description: every change that names a place on a drawing, in the order the panel lists them. «Показать на
 * чертеже» of a change focuses its own place; «Обзор всех» shows them together.
 */
export function evidenceOf(description: Pick<ComparisonSheetDescription, 'changes'>): readonly Evidence[] {
  return (description.changes ?? []).flatMap((change) =>
    change.box === undefined ? [] : [{ id: change.change_id, label: change.object_name, side: change.side ?? 'b', box: change.box }],
  );
}

export function focusIndexOf(evidence: readonly Evidence[], changeId: string): number {
  return evidence.findIndex((item) => item.id === changeId);
}

/** «доказательство N из M» for the banner. */
export function evidenceCounter(index: number, total: number): string {
  return `доказательство ${index + 1} из ${total}`;
}

export function stepIndex(index: number, direction: -1 | 1, total: number): number {
  return total === 0 ? 0 : (index + direction + total) % total;
}

/** The text «Скопировать» puts on the clipboard: the changes, the open questions, and the label (`copyText`, `:130-150`). */
export function copyText(title: string, description: ComparisonSheetDescription): string {
  const lines = [title];
  (description.changes ?? []).forEach((change, index) => {
    const place = change.place === undefined || change.place === '' ? '' : ` (${change.place})`;
    lines.push(`${index + 1}. ${leadLine(change)}. ${change.object_name}${place}`);
    if (change.limitation !== undefined && change.limitation !== '') lines.push(`   Неясно: ${change.limitation}`);
  });
  (description.unresolved ?? []).forEach((item) => lines.push(`Требует уточнения: ${item.question}`));
  lines.push('', `Описание составлено ИИ и ${UNCONFIRMED_LABEL}.`);
  return lines.join('\n');
}
