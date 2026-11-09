/**
 * The two tabs of the run screen and how the keyboard moves between them (`RUN-SCREEN-01a`).
 *
 * Pure, so the keyboard contract is a function a test calls: the static render this suite has cannot fire a key event, and the
 * WAI-ARIA tabs pattern with automatic activation is small enough to state as a table, as `_pages/blocks/model/tabs.ts` does:
 *
 *   ArrowRight / ArrowLeft  the next / previous tab, wrapping at either end;
 *   Home / End              the first / last tab;
 *   anything else           no change (the key is left to the browser).
 */

export const RUN_TABS = ['overview', 'journal'] as const;

export type RunTab = (typeof RUN_TABS)[number];

export const RUN_TAB_LABELS: Readonly<Record<RunTab, string>> = {
  overview: 'Обзор',
  journal: 'Журнал',
};

/** The tab a key press selects among the tabs shown, or `null` when the key is not one the tabs answer. */
export function tabAfterKey(tabs: readonly RunTab[], current: RunTab, key: string): RunTab | null {
  const at = tabs.indexOf(current);
  if (at < 0 || tabs.length === 0) return null;
  const last = tabs.length - 1;
  switch (key) {
    case 'ArrowRight':
      return tabs[at === last ? 0 : at + 1] as RunTab;
    case 'ArrowLeft':
      return tabs[at === 0 ? last : at - 1] as RunTab;
    case 'Home':
      return tabs[0] as RunTab;
    case 'End':
      return tabs[last] as RunTab;
    default:
      return null;
  }
}
