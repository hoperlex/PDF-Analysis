import { routes } from '@/shared/lib';
import { REGISTRATIONS_REQUESTS_SCREEN } from '@/entities/registration-request';

/**
 * The three parts of the administration area, as the original's «Пользователи» page has them as tabs (`UI-A-90`): «Заявки (N)»,
 * «Пользователи» and «Журнал». Here each is its own screen, so the tabs are links, and a screen says which of the three it is.
 * The order is the original's: requests first, because a waiting request is the thing an administrator comes to do.
 */
export const ADMIN_AREAS = ['registrations', 'users', 'events'] as const;

export type AdminArea = (typeof ADMIN_AREAS)[number];

export const ADMIN_AREA_LABELS: Readonly<Record<AdminArea, string>> = {
  registrations: 'Заявки',
  users: 'Пользователи',
  events: 'Журнал входов',
};

export function adminAreaHref(area: AdminArea): string {
  switch (area) {
    case 'registrations': return REGISTRATIONS_REQUESTS_SCREEN;
    case 'users': return routes.users();
    case 'events': return routes.authEvents();
  }
}
