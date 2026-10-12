/**
 * What the «Нормы» screens say about a snapshot, a document and a search hit
 * (`W55A-WEB-NORMS`). Contract values keep their home in `data-*` attributes; these are the
 * Russian words a reader sees.
 */

import type {
  NormBuildState, NormDocument, NormFragment, NormSnapshot, NormSnapshotPage, NormSourceAttribution,
  NormTextReliability,
} from '@/shared/api';
import { NORM_DOCUMENT_ID_PATTERN } from '@/shared/api';

const BUILD_STATE_LABELS: Readonly<Record<NormBuildState, string>> = {
  complete: 'построен полностью',
  incomplete: 'построен не полностью',
  absent: 'не построен',
};

/** The snapshot's search index (`bge-m3-dense-v1`, D-127), in words. */
export function buildStateLabel(state: NormBuildState): string {
  return BUILD_STATE_LABELS[state] ?? 'состояние вне набора, известного этому приложению';
}

const ATTRIBUTION_LABELS: Readonly<Record<NormSourceAttribution, string>> = {
  consultant_plus: 'КонсультантПлюс',
  unattributed: 'не указан',
};

/** `NORM-Q04`: where a norm document's text came from. Carried on every hit and document. */
export function attributionLabel(attribution: NormSourceAttribution): string {
  return `Источник текста: ${ATTRIBUTION_LABELS[attribution] ?? 'вне набора, известного этому приложению'}`;
}

/** Whether a paragraph's recognised text is to be marked (F-4). */
export function isUnreliable(reliability: NormTextReliability): boolean {
  return reliability !== 'reliable';
}

/** «п. 7.1.4», or nothing for a paragraph that carries no clause number. */
export function clauseLabel(clauseNumber: string | null): string | null {
  return clauseNumber === null ? null : `п. ${clauseNumber}`;
}

/** The anchored contract pattern for a norm document identity. */
const NORM_DOCUMENT_ID = new RegExp(NORM_DOCUMENT_ID_PATTERN);

export function looksLikeNormDocumentId(value: unknown): value is string {
  return typeof value === 'string' && NORM_DOCUMENT_ID.test(value);
}

/**
 * The PDF page an address asks for: a positive integer written in plain digits, or `null`
 * when the address names none. `undefined` when the value is present and is not a page —
 * the route answers that with a 404 rather than opening some other page.
 */
export function pageFromAddress(value: unknown): number | null | undefined {
  if (value === undefined) return null;
  if (typeof value !== 'string' || !/^[1-9][0-9]{0,5}$/.test(value)) return undefined;
  return Number(value);
}

/**
 * Whether the document view reads the PDF: a page was asked for, a confirmed binding serves
 * the document (`content_available`), and the page exists in it. Anything else is said in
 * words by the panel and costs no read.
 */
export function wantsNormPdf(document: NormDocument, page: number | null): page is number {
  return page !== null && document.content_available && page <= document.pdf_page_count;
}

/**
 * Which snapshot is current, as far as one read of the list can tell.
 *
 *   `current`  the list carries the snapshot marked current;
 *   `none`     the whole list was read and none is current — the state before any
 *              administrator designates one, in which search refuses (R-113);
 *   `beyond`   none is current on this page and more pages exist, so the current one, if
 *              any, was not read. Said as such, never guessed.
 */
export type CurrentSnapshotReading =
  | { readonly kind: 'current'; readonly snapshot: NormSnapshot }
  | { readonly kind: 'none' }
  | { readonly kind: 'beyond' };

export function currentSnapshotOf(page: NormSnapshotPage): CurrentSnapshotReading {
  const snapshot = page.items.find((item) => item.current);
  if (snapshot !== undefined) return { kind: 'current', snapshot };
  return page.page.next_cursor === null ? { kind: 'none' } : { kind: 'beyond' };
}

/** One run of a fragment: plain text, or a span the search matched. */
export interface FragmentPart {
  readonly text: string;
  readonly hit: boolean;
}

/**
 * `NORM-Q01`: the fragment's plain text, cut at its matched spans.
 *
 * The offsets are character offsets, so the text is indexed by code point rather than by
 * UTF-16 unit (a character outside the Basic Multilingual Plane would otherwise shift every
 * span after it). The text itself is never changed: a span that falls outside the text, is
 * empty or overlaps the one before it is not marked, and the characters it names are shown
 * unmarked — the reader loses an emphasis, never a word.
 */
export function fragmentParts(fragment: NormFragment): readonly FragmentPart[] {
  const characters = Array.from(fragment.text);
  const spans = [...fragment.highlights]
    .filter((span) =>
      Number.isInteger(span.char_start) && Number.isInteger(span.char_end) &&
      span.char_start >= 0 && span.char_end <= characters.length && span.char_start < span.char_end)
    .sort((a, b) => a.char_start - b.char_start);
  const parts: FragmentPart[] = [];
  let at = 0;
  for (const span of spans) {
    if (span.char_start < at) continue;
    if (span.char_start > at) parts.push({ text: characters.slice(at, span.char_start).join(''), hit: false });
    parts.push({ text: characters.slice(span.char_start, span.char_end).join(''), hit: true });
    at = span.char_end;
  }
  if (at < characters.length) parts.push({ text: characters.slice(at).join(''), hit: false });
  return parts;
}
