/**
 * The pages an observation actually declares, and nothing else.
 *
 * The evidence viewer navigates within this set. It is not "page 1 to the document's page
 * count": the reviewer is judging a specific quotation on a specific page, and offering
 * them the other twenty-eight pages of the PDF invites them to decide against text the
 * finding never cited. `P3-WEB-02` states it as a deliverable — page navigation limited to
 * the observation's declared pages.
 *
 * Nothing here re-derives a page from a character offset. `char_start`/`char_end` index the
 * document-global prepared text layer (`P02_SEAMS.md` §4) and only the backend holds that
 * layer; the page number is server-supplied and is used as given.
 */

import type { Evidence, FindingObservation, ProviderMode } from '@/shared/api';

/**
 * The distinct pages this observation cites, ascending.
 *
 * Sorted numerically and de-duplicated: three quotations on page 7 are one page to
 * navigate to, and `Array.prototype.sort` without a comparator would order 10 before 7.
 */
export function declaredPages(observation: FindingObservation): readonly number[] {
  const seen = new Set<number>();
  for (const item of observation.evidence) seen.add(item.page_number);
  return [...seen].sort((left, right) => left - right);
}

/** The page the viewer opens on: the first page this observation cites. */
export function firstDeclaredPage(observation: FindingObservation): number | null {
  const pages = declaredPages(observation);
  return pages.length === 0 ? null : (pages[0] as number);
}

/** True when `page` is one the observation cites. The viewer refuses to open any other. */
export function isDeclaredPage(observation: FindingObservation, page: number): boolean {
  return declaredPages(observation).includes(page);
}

/**
 * The evidence items on one page, in the contract's `evidence_ordinal` order.
 *
 * Ordinal, not array position: the ordinal is the server's stable ordering of quotations
 * within an observation and is what the CSV's row order follows.
 */
export function evidenceOnPage(
  observation: FindingObservation,
  page: number,
): readonly Evidence[] {
  return observation.evidence
    .filter((item) => item.page_number === page)
    .sort((left, right) => left.evidence_ordinal - right.evidence_ordinal);
}

/** Every quotation, ordered as the CSV orders them: by page, then by ordinal. */
export function orderedEvidence(observation: FindingObservation): readonly Evidence[] {
  return [...observation.evidence].sort(
    (left, right) =>
      left.page_number - right.page_number || left.evidence_ordinal - right.evidence_ordinal,
  );
}

/**
 * The provider mode that produced this observation.
 *
 * Read from the observation's own provenance rather than from the run: a PC-01 acceptance
 * criterion is that a recorded run is never presentable as a live one, and the evidence in
 * front of the reviewer carries its own answer to that question.
 */
export function observationProviderMode(observation: FindingObservation): ProviderMode {
  return observation.provenance.provider_mode;
}
