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
 * A stated anchor that disagrees with the string beside it would be worse than no anchor
 * at all, so the panel checks rather than asserts, and it states the character range only
 * when this is false (`R-43`, `anchorRangeLabel`).
 */
export function anchorMatchesQuotation(evidence: Evidence): boolean {
  return evidence.char_end - evidence.char_start === quotationCodePointLength(evidence);
}

/**
 * The page of the anchor, formatted for display. Never parsed back and never used to slice
 * anything.
 *
 * **Page only, by owner ruling `R-43`.** The caption under a quotation names the page and
 * nothing else. The character range does not appear next to the quotation: `D-50` measured
 * that `char_start`/`char_end` are true only in the coordinate system of the extractor that
 * produced them (a second extractor puts the same string at a different index, and the drift
 * grows at every page boundary), and that system is named nowhere a reader can see. A number
 * like that invites a check that fails for the wrong reason, and an expert who tries it
 * concludes that the tool is lying rather than that two coordinate systems differ. The
 * offsets stay in the data and keep working at the binding seam; only the screen loses them.
 */
export function anchorLabel(evidence: Evidence): string {
  return `стр. ${evidence.page_number}`;
}

/**
 * The character range of the anchor, formatted for the discrepancy alert and for nowhere
 * else. Never parsed back and never used to slice anything.
 *
 * **Why the range survives at all.** `anchorMatchesQuotation` renders an alert when the
 * declared span disagrees with the string beside it, and an alert about numbers the
 * reviewer cannot see is not actionable. So the range appears exactly when it is evidence
 * of a discrepancy, and the alert is the only caller.
 *
 * **The label states its own convention, because the numbers are not the ones a reader
 * assumes.** `char_start`/`char_end` index the *document-global* prepared text layer — the
 * frozen `Evidence` schema says so in as many words, and `model/pages` repeats it. The
 * caption this replaces once read `page 2, chars 712-746`, and next to the words "page 2"
 * that range reads as an offset into page 2 (`D-25`, found by `W21-CERT` driving criterion
 * 5; the anchor is the live one, `run_01M2TB4QP6B784MQ7NN1TFFP79`, first quotation, read
 * back from `GET /v1/runs/{run_id}/findings` by `W22-WEB`). `W21-CERT` measured page 2 of
 * that document at 539 characters, a backend figure this session did not re-measure; what
 * matters needs no re-measuring: **712 is past the end of a 539-character page**, so an
 * expert counting 712 characters into that page finds nothing and concludes the tool is
 * fabricating a quotation it had exactly right.
 *
 * **Why the global range is kept rather than converted.** A page-local offset is
 * `char_start` minus the page's own start in the prepared text layer, and the browser holds
 * neither the layer nor that start. `Evidence` carries `page_number`, the two global offsets
 * and the quote, and nothing else. A client-side conversion would have to re-derive the
 * layer, which is the one thing `P3-WEB-02` forbids and `model/pages` refuses by design.
 *
 * `of the whole document, not of page N` is self-describing: a reader acts on it correctly
 * without being told anywhere else which convention it uses, and the page is named a second
 * time so the negation cannot be misread as referring to some other page.
 */
export function anchorRangeLabel(evidence: Evidence): string {
  return (
    `символы ${evidence.char_start}–${evidence.char_end} ` +
    `по всему документу, а не по странице ${evidence.page_number}`
  );
}
