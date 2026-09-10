/**
 * Which finding is open, and which of its pages.
 *
 * Kept as one value rather than two pieces of state, because the page number is only
 * meaningful against the finding it belongs to. Two independent `useState`s produce the
 * bug where selecting a finding whose evidence is on page 3 leaves the viewer showing
 * page 11 from the previous finding — the viewer would then be displaying a page this
 * finding never cited, which is precisely what the declared-page restriction exists to
 * prevent.
 *
 * Pure, so the rule is testable without rendering anything.
 */

export interface ReviewSelection {
  readonly findingUid: string;
  /** Null means "the finding's first declared page", resolved by the viewer. */
  readonly page: number | null;
}

/** Selecting a finding always clears the page: a page belongs to one finding. */
export function selectFinding(findingUid: string): ReviewSelection {
  return { findingUid, page: null };
}

/** Changing the page keeps the finding. Only the viewer's own page buttons call this. */
export function selectPage(current: ReviewSelection | null, page: number): ReviewSelection | null {
  if (current === null) return null;
  return { findingUid: current.findingUid, page };
}

/**
 * The finding actually shown: the selected one when it is still in the list, otherwise the
 * first one.
 *
 * The containment check matters after a refetch. If the list changes under a selection —
 * a filter applied, a page of results replaced — a selection pointing at a finding that is
 * no longer there would leave the panels showing a finding the list does not offer.
 */
export function resolveSelection(
  selection: ReviewSelection | null,
  findingUids: readonly string[],
): ReviewSelection | null {
  if (findingUids.length === 0) return null;
  if (selection !== null && findingUids.includes(selection.findingUid)) return selection;
  return selectFinding(findingUids[0] as string);
}
