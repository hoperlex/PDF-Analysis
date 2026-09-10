/**
 * The quotation, exactly as the server sent it.
 *
 * This module exists to be the one obvious place a well-meaning change would put
 * trimming, whitespace collapsing, ellipsis truncation, quote-character substitution or
 * Unicode normalization — and to refuse. `P02_SEAMS.md` §5.1 grounds a quotation by
 * slicing the prepared text layer and requiring it to **equal the quote exactly** after
 * the one declared normalization the backend already applied. A second normalization in
 * the browser breaks the only property the evidence viewer exists to demonstrate: that
 * this string is present, verbatim, at that anchor.
 *
 * `P3-WEB-02` says the same thing as a non-goal — no client-side re-extraction or
 * normalization of the quotation — and its required test asserts the rendered quotation is
 * byte-identical to the API string.
 *
 * Rendering is `{evidence.quote}` in JSX, which escapes markup and alters nothing else.
 * The helpers below describe a quotation without touching it.
 */

import type { Evidence } from '@/shared/api';

/** The quotation string, unmodified. Identity by construction, not by convention. */
export function quotationText(evidence: Evidence): string {
  return evidence.quote;
}

/**
 * Length in Unicode code points, matching how `char_start`/`char_end` are counted.
 *
 * `String.prototype.length` counts UTF-16 code units, so a quotation containing an
 * astral-plane character would disagree with the contract's own arithmetic. The spread
 * form iterates code points. This is presentation only — nothing re-derives an anchor.
 */
export function quotationCodePointLength(evidence: Evidence): number {
  return [...evidence.quote].length;
}

/**
 * True when the declared span length matches the quotation's own length.
 *
 * `span_length_mismatch` is one of the five `ungrounded_reason` values, so the backend has
 * already refused any item where this is false — a published finding cannot carry one.
 * The viewer states the anchor to the reviewer, and a stated anchor that disagrees with
 * the string beside it would be worse than no anchor at all, so the panel checks rather
 * than asserts.
 */
export function anchorMatchesQuotation(evidence: Evidence): boolean {
  return evidence.char_end - evidence.char_start === quotationCodePointLength(evidence);
}

/** The anchor, formatted for display. Never parsed back and never used to slice anything. */
export function anchorLabel(evidence: Evidence): string {
  return `page ${evidence.page_number}, chars ${evidence.char_start}–${evidence.char_end}`;
}
