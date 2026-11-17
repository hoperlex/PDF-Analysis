/**
 * The tabs of «Диспетчер» (`HOSTS-WEB-01`, plan 2026-11-09 §7.1; four since `UIP-S15-06`), and how the keyboard moves between them.
 *
 * Pure, as `_pages/blocks/model/tabs.ts` is: the static render this suite has cannot fire a key event, and the WAI-ARIA tabs
 * pattern (automatic activation) is small enough to state as a table.
 *
 *   ArrowRight / ArrowLeft  the next / previous tab, wrapping at either end;
 *   Home / End              the first / last tab;
 *   anything else           no change (the key is left to the browser).
 *
 * Four tabs, «Обзор · Серверы · Задачи · Модели по этапам»: the strip of five numbers with the servers in a short form, the servers
 * as cards, the queue's jobs in three groups, and the model of each stage. The six tabs the screen had (`EXEC-HTTP-01`,
 * `EXEC2-WEB-GROUPS-01`, `UI-PARITY` UI-B-63) moved to the administrator's separate page, `/workers/advanced` (`./advanced.ts`).
 * There is no «Диагностика» and no «Лимиты»: the stand has no data for them (`Г12-B`). The address keeps the tab:
 * `?tab=overview|servers|tasks|models`, and a value that is none of them opens the tab the screen opens on.
 */

export const WORKERS_TABS = ['overview', 'servers', 'tasks', 'models'] as const;

export type WorkersTab = (typeof WORKERS_TABS)[number];

/** The tab the screen opens on when the address names none. */
export const DEFAULT_WORKERS_TAB: WorkersTab = 'overview';

export const WORKERS_TAB_LABELS: Readonly<Record<WorkersTab, string>> = {
  overview: 'Обзор',
  servers: 'Серверы',
  tasks: 'Задачи',
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
