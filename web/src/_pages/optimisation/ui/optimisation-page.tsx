'use client';

/**
 * `/optimisation` — the retired tuning stub, now a pointer to where project optimisation is.
 *
 * `R-66` kept this address registered and reachable, out of the menu, until project
 * optimisation became a project tab (`ROADMAP-TO-BETA.md` §10.1 A-6). `W60-OPT-PROPOSALS-01`
 * completes that tab — price lists and vendor lists (`W60-PRICE-LIST-01`) and the proposals
 * with the experts' decisions — so this address no longer has a screen of its own: it sends
 * the browser to the projects list, where each project's «Оптимизация» tab is, and says so
 * while it does. A bookmark keeps working; nothing is promised that is not already there.
 *
 * The redirect is the screen's only behaviour. It is made on the client, after the route's
 * guard has let the session in, so a guest still goes to sign in first and comes back here.
 *
 * **It follows the object** (`UIP-G-06`; the registry class is `optional`). With an object — `?project=<uid>`, or, where the
 * address is silent, the one the account chose last — the redirect leads to that object's own «Оптимизация» tab; with none
 * (`?project=all`, no last object, or an account answer that failed) to the list. While the account's answer is on its way the
 * redirect waits: leaving at once would leave without knowing where to.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { PageShell } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { useCurrentProject } from '@/entities/project';

/** Where the retired address sends the browser when no object is known: the list of objects. */
export const OPTIMISATION_MOVED_TO = routes.projects();

/** This screen's registry address, the one the registry classifies; it stands in for the address outside the app router. */
const OPTIMISATION_ADDRESS = '/optimisation';

/** Where the retired address sends the browser for `projectUid` (`null`: no object): the object's tab, or the list. */
export function optimisationTarget(projectUid: string | null): string {
  return projectUid === null ? OPTIMISATION_MOVED_TO : routes.projectOptimisation(projectUid);
}

export function OptimisationPage() {
  const router = useRouter();
  const { projectUid, pending } = useCurrentProject(OPTIMISATION_ADDRESS);
  const target = optimisationTarget(projectUid);
  useEffect(() => {
    if (!pending) router.replace(target);
  }, [router, target, pending]);

  return (
    <PageShell title="Оптимизация" subtitle="Раздел перенесён в объект">
      <div className="am-state am-state--neutral" role="status" data-optimisation-moved="">
        <p className="am-state__title">Оптимизация теперь на вкладке объекта.</p>
        <div className="am-state__detail">
          Откройте объект и перейдите на вкладку «Оптимизация»: там прайс-лист объекта, вендор-листы
          по разделам и предложения по более дешёвым аналогам с решениями экспертов.{' '}
          {projectUid === null ? 'Открываю список объектов.' : 'Открываю вкладку «Оптимизация» объекта.'}
        </div>
        <div className="am-state__action">
          <Link href={target}>{projectUid === null ? 'Перейти к объектам' : 'Перейти к объекту'}</Link>
        </div>
      </div>
    </PageShell>
  );
}
