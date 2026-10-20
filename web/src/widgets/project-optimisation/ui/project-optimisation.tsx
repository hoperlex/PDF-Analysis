'use client';

/**
 * The project's «Оптимизация» tab (`W60-PRICE-LIST-01`): the stored inputs of project
 * optimisation — the project's price list and the vendor lists per section.
 *
 * This slice stores and shows prices; it proposes nothing and totals nothing. A money figure
 * on this screen is always one position of an uploaded price list, in the currency that price
 * list stated.
 */

import type { ProjectUid, Role } from '@/shared/api';

import { PriceListPanel } from './price-list-panel';
import { VendorListsPanel } from './vendor-lists-panel';

export interface ProjectOptimisationProps {
  readonly projectUid: ProjectUid;
  /** The session's roles, as the route's guard read them. */
  readonly roles: readonly Role[];
}

export function ProjectOptimisation({ projectUid, roles }: ProjectOptimisationProps) {
  return (
    <div data-project-optimisation={projectUid}>
      <section className="am-section">
        <h2>Прайс-листы проекта</h2>
        <p className="am-note">
          Цены для оптимизации берутся только из загруженного прайс-листа: каждая загрузка —
          новая редакция, последняя действует, прежние остаются доступными.
        </p>
        <PriceListPanel projectUid={projectUid} canUpload={roles.includes('expert')} />
      </section>
      <section className="am-section">
        <h2>Вендор-листы по разделам</h2>
        <p className="am-note">
          Для каждого раздела действует список проекта, если эксперт его задал, иначе общий
          список администратора.
        </p>
        <VendorListsPanel projectUid={projectUid} roles={roles} />
      </section>
    </div>
  );
}
