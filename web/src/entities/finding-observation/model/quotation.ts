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

/**
 * The anchor, formatted for display. Never parsed back and never used to slice anything.
 *
 * **The caption states its own convention, because the numbers are not the ones a reader
 * assumes.** `char_start`/`char_end` index the *document-global* prepared text layer — the
 * frozen `Evidence` schema says so in as many words, and `model/pages` repeats it. The
 * previous caption read `page 2, chars 707-746`, and next to the words "page 2" that range
 * reads as an offset into page 2. `D-25` was found by `W21-CERT` on a real document whose
 * page 2 holds 539 characters: the quotation actually sits at page-local 198-237, so an
 * expert checking the citation by hand counts 707 characters into a 539-character page,
 * finds nothing, and concludes the tool is fabricating a quotation it had exactly right.
 * **The data was correct and the caption was wrong, which is the worse half** — a wrong
 * number invites a re-check, a wrong convention invites a wrong conclusion.
 *
 * **Why the global range is kept rather than converted or dropped.** Converting is not
 * available here: a page-local offset is `char_start` minus the page's own start in the
 * prepared text layer, and the browser holds neither the layer nor that start. `Evidence`
 * carries `page_number`, the two global offsets and the quote, and nothing else; the page
 * pane is the PDF's own bytes, not the extracted text. A client-side conversion would have
 * to re-derive the layer, which is the one thing `P3-WEB-02` forbids and `model/pages`
 * refuses by design. Dropping the range instead would take a fact off the screen that the
 * viewer needs: `anchorMatchesQuotation` renders an alert when the declared span disagrees
 * with the string beside it, and an alert about numbers the reviewer cannot see is not
 * actionable.
 *
 * So the range stays and the caption says what it is. `of the whole document, not of page
 * N` is self-describing: a reader acts on it correctly without being told anywhere else
 * which convention it uses, and the page is named a second time so the negation cannot be
 * misread as referring to some other page.
 */
export function anchorLabel(evidence: Evidence): string {
  return (
    `page ${evidence.page_number}, ` +
    `characters ${evidence.char_start}–${evidence.char_end} ` +
    `of the whole document, not of page ${evidence.page_number}`
  );
}
