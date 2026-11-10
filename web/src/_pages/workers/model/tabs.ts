/**
 * The tabs of «Исполнители» (`HOSTS-WEB-01`, plan 2026-11-09 §7.1), and how the keyboard moves between them.
 *
 * Pure, as `_pages/blocks/model/tabs.ts` is: the static render this suite has cannot fire a key event, and the WAI-ARIA tabs
 * pattern (automatic activation) is small enough to state as a table.
 *
 *   ArrowRight / ArrowLeft  the next / previous tab, wrapping at either end;
 *   Home / End              the first / last tab;
 *   anything else           no change (the key is left to the browser).
 *
 * Two tabs, «Серверы» and «Модели по этапам». The six tabs the screen had (`EXEC-HTTP-01`, `EXEC2-WEB-GROUPS-01`, `UI-PARITY`
 * UI-B-63) moved to the administrator's separate page, `/workers/advanced` (`./advanced.ts`); the overview of UI-B-63 is the
 * summary line of «Серверы».
 */

export const WORKERS_TABS = ['servers', 'models'] as const;

export type WorkersTab = (typeof WORKERS_TABS)[number];

/** The tab the screen opens on when the address names none. */
export const DEFAULT_WORKERS_TAB: WorkersTab = 'servers';

export const WORKERS_TAB_LABELS: Readonly<Record<WorkersTab, string>> = {
  servers: 'Серверы',
  models: 'Модели по этапам',
};

/** The `tab` query parameter, which a reload keeps and a link can carry. */
export const WORKERS_TAB_PARAM = 'tab';

export function isWorkersTab(value: unknown): value is WorkersTab {
  return typeof value === 'string' && (WORKERS_TABS as readonly string[]).includes(value);
}

/** The tab a key press selects, or `null` when the key is not one the tabs answer. */
export function tabAfterKey(current: WorkersTab, key: string): WorkersTab | null {
  const at = WORKERS_TABS.indexOf(current);
  const last = WORKERS_TABS.length - 1;
  switch (key) {
    case 'ArrowRight':
      return WORKERS_TABS[at === last ? 0 : at + 1] as WorkersTab;
    case 'ArrowLeft':
      return WORKERS_TABS[at === 0 ? last : at - 1] as WorkersTab;
    case 'Home':
      return WORKERS_TABS[0];
    case 'End':
      return WORKERS_TABS[last] as WorkersTab;
    default:
      return null;
  }
}
