/**
 * The tabs of «Исполнители» (`EXEC-HTTP-01`, widened by `EXEC2-WEB-GROUPS-01` and `UI-PARITY` UI-B-63), and how the keyboard
 * moves between them.
 *
 * Pure, as `_pages/blocks/model/tabs.ts` is: the static render this suite has cannot fire a key
 * event, and the WAI-ARIA tabs pattern (automatic activation) is small enough to state as a
 * table.
 *
 *   ArrowRight / ArrowLeft  the next / previous tab, wrapping at either end;
 *   Home / End              the first / last tab;
 *   anything else           no change (the key is left to the browser).
 */

/**
 * `EXEC2-WEB-GROUPS-01` adds «Группы» and «Правила» between «Процессы» and «Назначения». «Назначения» stays
 * last: it is the legacy Primary/Standby routing, the live editor while the routing mode is `legacy`
 * and the history of the routes once rules are in force (ADR-0026 decision 17).
 *
 * `UI-PARITY` UI-B-63: «Обзор» is the first tab, as the first tab of the original's dispatcher. It holds the
 * tiles and the queue line that sat over «Процессы», and links to the tab or the screen each one summarises.
 */
export const WORKERS_TABS = ['overview', 'connections', 'processes', 'groups', 'rules', 'routes'] as const;

export type WorkersTab = (typeof WORKERS_TABS)[number];

/**
 * The tab the screen opens on when the address names none: «Обзор», as the original's dispatcher opens on its overview
 * (`UI-PARITY` UI-B-63). It was «Процессы», the worker list the screen had always shown, until the second UX pass of
 * 2026-11-07; the list is one click away (`?tab=processes`), and a link that wants it names it. A redirect from the key
 * form names «Подключения» itself, and a link to the overview needs no `?tab=`.
 */
export const DEFAULT_WORKERS_TAB: WorkersTab = 'overview';

export const WORKERS_TAB_LABELS: Readonly<Record<WorkersTab, string>> = {
  overview: 'Обзор',
  connections: 'Подключения',
  processes: 'Процессы',
  groups: 'Группы',
  rules: 'Правила',
  routes: 'Назначения',
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
