/**
 * The two tabs of «Сравнение версий» (plan §1.1), and how the keyboard moves between them.
 *
 * Pure, as the tabs of «Блоки» and «Исполнители» are: the static render cannot fire a key event, and the WAI-ARIA tabs
 * pattern (automatic activation) is small enough to state as a table. «Сравнение листов» is open to a reader only once a
 * document set has been chosen on «Проекты и этапы», as the original's second tab is (`version-comparison.js:85-88`).
 */

export const COMPARE_TABS = ['projects', 'sheets'] as const;

export type CompareTab = (typeof COMPARE_TABS)[number];

export const COMPARE_TAB_LABELS: Readonly<Record<CompareTab, string>> = {
  projects: 'Проекты и этапы',
  sheets: 'Сравнение листов',
};

export const COMPARE_TAB_HINTS: Readonly<Record<CompareTab, string>> = {
  projects: 'Все комплекты проекта и этапы их проверки одной таблицей.',
  sheets: 'Матрица листов открытого комплекта: какой лист какой версии соответствует какому.',
};

export function isCompareTab(value: unknown): value is CompareTab {
  return typeof value === 'string' && (COMPARE_TABS as readonly string[]).includes(value);
}

/** The tab a key press selects, or `null` when the key is not one the tabs answer. */
export function tabAfterKey(current: CompareTab, key: string): CompareTab | null {
  const at = COMPARE_TABS.indexOf(current);
  const last = COMPARE_TABS.length - 1;
  switch (key) {
    case 'ArrowRight':
      return COMPARE_TABS[at === last ? 0 : at + 1] as CompareTab;
    case 'ArrowLeft':
      return COMPARE_TABS[at === 0 ? last : at - 1] as CompareTab;
    case 'Home':
      return COMPARE_TABS[0];
    case 'End':
      return COMPARE_TABS[last] as CompareTab;
    default:
      return null;
  }
}
