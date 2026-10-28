/**
 * «Текст: N изменений» with the numbers that changed marked (`CMP-VIEWER-01`).
 *
 * A text change carries `numbers`: the numeric values that changed inside it, each as `before` and `after`. The viewer
 * shows «было → стало» and marks those values so that a changed dimension or quantity is not lost in a sentence. The
 * marks are found in the text itself (a value is marked wherever it stands as a whole number token), never invented:
 * a value that is not in the text is not marked.
 */

import type { ComparisonNumberChange } from '@/shared/api';

export interface TextPart {
  readonly text: string;
  readonly marked: boolean;
}

const NUMBER_TOKEN = /\d+(?:[.,]\d+)*/gu;

/**
 * `text` split into parts, the occurrences of `values` marked. An occurrence is marked only as a whole number token
 * (`12` is not marked inside `112`, nor inside `12.5` unless `12.5` is itself the value).
 */
export function markNumbers(text: string, values: readonly string[]): TextPart[] {
  const wanted = new Set(values.map((value) => value.trim()).filter((value) => value !== ''));
  if (wanted.size === 0) return [{ text, marked: false }];
  const parts: TextPart[] = [];
  let last = 0;
  for (const match of text.matchAll(NUMBER_TOKEN)) {
    const start = match.index ?? 0;
    if (!wanted.has(match[0])) continue;
    if (start > last) parts.push({ text: text.slice(last, start), marked: false });
    parts.push({ text: match[0], marked: true });
    last = start + match[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last), marked: false });
  return parts.length === 0 ? [{ text, marked: false }] : parts;
}

export function beforeValues(numbers: readonly ComparisonNumberChange[] | undefined): string[] {
  return (numbers ?? []).map((change) => change.before);
}

export function afterValues(numbers: readonly ComparisonNumberChange[] | undefined): string[] {
  return (numbers ?? []).map((change) => change.after);
}
