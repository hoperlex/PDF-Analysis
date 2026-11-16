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
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { PageShell } from '@/shared/ui';
import { routes } from '@/shared/lib';

/** Where the retired address sends the browser. */
export const OPTIMISATION_MOVED_TO = routes.projects();

export function OptimisationPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace(OPTIMISATION_MOVED_TO);
  }, [router]);

  return (
    <PageShell title="Оптимизация" subtitle="Раздел перенесён в объект">
      <div className="am-state am-state--neutral" role="status" data-optimisation-moved="">
        <p className="am-state__title">Оптимизация теперь на вкладке объекта.</p>
        <div className="am-state__detail">
          Откройте объект и перейдите на вкладку «Оптимизация»: там прайс-лист объекта, вендор-листы
          по разделам и предложения по более дешёвым аналогам с решениями экспертов. Открываю
          список объектов.
        </div>
        <div className="am-state__action">
          <Link href={OPTIMISATION_MOVED_TO}>Перейти к объектам</Link>
        </div>
      </div>
    </PageShell>
  );
}
