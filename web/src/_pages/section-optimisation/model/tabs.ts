/**
 * The tabs of «Оптимизация разделов» (`UI-B-22`, `UI-B-27`): the specification, and the accepted optimisations.
 *
 * Each tab carries its number, as the original's «Форма 7 · Спецификация N» and «Принято N»: the server's own figure for
 * the section and project chosen -- `SectionSpecification.row_count` and `AcceptedOptimisationProposalPage.total` -- read
 * without opening the tab, and never a count of the rows held. A tab whose figure is not in hand (still being read, refused,
 * or a specification the server stopped at a bound) carries no number rather than a guess.
 */

export const SECTION_OPTIMISATION_TABS = ['specification', 'accepted'] as const;
export type SectionOptimisationTab = (typeof SECTION_OPTIMISATION_TABS)[number];

export const SECTION_OPTIMISATION_TAB_LABELS: Readonly<Record<SectionOptimisationTab, string>> = {
  specification: 'Спецификация',
  accepted: 'Принято',
};

/** The figure each tab shows; `null` while it is not known. */
export type SectionOptimisationTabCounts = Readonly<Record<SectionOptimisationTab, number | null>>;

/** The tab's text: its label, and the server's number when there is one. */
export function sectionOptimisationTabText(tab: SectionOptimisationTab, counts: SectionOptimisationTabCounts): string {
  const count = counts[tab];
  const label = tab === 'specification' ? `Форма 7 · ${SECTION_OPTIMISATION_TAB_LABELS[tab]}` : SECTION_OPTIMISATION_TAB_LABELS[tab];
  return count === null ? label : `${label} ${count}`;
}
