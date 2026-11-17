/**
 * The advanced page of «Диспетчер» (`HOSTS-WEB-01`, plan 2026-11-09 §7.5), `/workers/advanced`, for an administrator.
 *
 * It keeps what the screen had before it became two tabs, folded: «Подключения», «Группы», «Правила», «Назначения»,
 * «Процессы» (with the working switch of intake), the analysis presets moved here, and «Модели по этапам» with the switch
 * «Модели по этапам: включены», its journal and the revisions. It is still needed for the comparisons until `HOSTS-CMP-01`
 * and for the SSH connection «kzSonnet».
 *
 * An old address keeps working: `/workers?tab=connections` and its kin are sent here by the route (`legacyAdvancedTab`).
 */

export const ADVANCED_SECTIONS = ['connections', 'groups', 'rules', 'routes', 'processes', 'presets', 'layout', 'precedents'] as const;

export type AdvancedSection = (typeof ADVANCED_SECTIONS)[number];

export const ADVANCED_SECTION_LABELS: Readonly<Record<AdvancedSection, string>> = {
  connections: 'Подключения',
  groups: 'Группы',
  rules: 'Правила',
  routes: 'Назначения',
  processes: 'Процессы',
  presets: 'Пресеты анализа',
  layout: 'Модели по этапам',
  precedents: 'Прецеденты и векторы',
};

/** The address of the page, as the screen registry has it. */
export const WORKERS_ADVANCED_ADDRESS = '/workers/advanced';

/** The quiet link on «Диспетчер», for an administrator. */
export const ADVANCED_LINK_LABEL = 'Расширенные ▸';
export const BACK_LINK_LABEL = '◂ Диспетчер';

export function isAdvancedSection(value: unknown): value is AdvancedSection {
  return typeof value === 'string' && (ADVANCED_SECTIONS as readonly string[]).includes(value);
}

/**
 * The section an old tab of «Диспетчер» is now: the five tabs that moved keep their name (`?tab=routes`). «Обзор», «Серверы»,
 * «Задачи» and «Модели по этапам» are tabs of the screen itself (`./tabs.ts`) and have none.
 */
export function legacyAdvancedTab(tab: string | undefined): AdvancedSection | null {
  return tab !== undefined && isAdvancedSection(tab) && tab !== 'presets' && tab !== 'layout' && tab !== 'precedents' ? tab : null;
}
