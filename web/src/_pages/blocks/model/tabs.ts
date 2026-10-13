/**
 * The two views of a chosen version on «Блоки», and how the keyboard moves between them.
 *
 * Pure, so the keyboard contract is a function a test calls rather than a behaviour only a
 * browser can show: the static render this suite has cannot fire a key event, and the
 * WAI-ARIA tabs pattern (automatic activation) is small enough to state as a table.
 *
 *   ArrowRight / ArrowLeft  the next / previous tab, wrapping at either end;
 *   Home / End              the first / last tab;
 *   anything else           no change (the key is left to the browser).
 */

export const BLOCK_TABS = ['portal', 'lines'] as const;

export type BlockTab = (typeof BLOCK_TABS)[number];

/** The view a reader lands on once a version is chosen, and again after choosing another. */
export const DEFAULT_BLOCK_TAB: BlockTab = 'portal';

export const BLOCK_TAB_LABELS: Readonly<Record<BlockTab, string>> = {
  portal: 'Блоки портала',
  lines: 'Строки текста',
};

/** The tab a key press selects, or `null` when the key is not one the tabs answer. */
export function tabAfterKey(current: BlockTab, key: string): BlockTab | null {
  const at = BLOCK_TABS.indexOf(current);
  const last = BLOCK_TABS.length - 1;
  switch (key) {
    case 'ArrowRight':
      return BLOCK_TABS[at === last ? 0 : at + 1] as BlockTab;
    case 'ArrowLeft':
      return BLOCK_TABS[at === 0 ? last : at - 1] as BlockTab;
    case 'Home':
      return BLOCK_TABS[0];
    case 'End':
      return BLOCK_TABS[last] as BlockTab;
    default:
      return null;
  }
}
