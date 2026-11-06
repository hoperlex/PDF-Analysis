/**
 * The four steps of «Сравнение стадий» and how the keyboard moves between them (the WAI-ARIA tabs pattern with automatic activation, as
 * the tabs of «Сравнение версий» have it). Pure: the static render cannot fire a key event, and a table states the pattern.
 */

import { STAGE_TABS } from './address';
import type { StageTab } from './address';

export const STAGE_TAB_LABELS: Readonly<Record<StageTab, string>> = {
  documentation: '1. Загрузка документации',
  sheets: '2. Сопоставление листов',
  changes: '3. Изменения проекта',
  journal: '4. Отчёт',
};

/** The step a key press selects, or `null` when the key is not one the tabs answer. */
export function stageTabAfterKey(current: StageTab, key: string): StageTab | null {
  const at = STAGE_TABS.indexOf(current);
  const last = STAGE_TABS.length - 1;
  switch (key) {
    case 'ArrowRight': return STAGE_TABS[at === last ? 0 : at + 1] as StageTab;
    case 'ArrowLeft': return STAGE_TABS[at === 0 ? last : at - 1] as StageTab;
    case 'Home': return STAGE_TABS[0];
    case 'End': return STAGE_TABS[last] as StageTab;
    default: return null;
  }
}
