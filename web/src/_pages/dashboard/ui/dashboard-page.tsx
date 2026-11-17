'use client';

/**
 * `/dashboard` — `R-44`, `R-18` applied at screen scope: real numbers where the surface
 * already carries them, honest structure where it does not.
 *
 * Composition only: the shell from `shared/ui`, the four panels from `widgets/dashboard`,
 * reached through the lazy wrapper beside this file (`W50-LAZY-01`).
 *
 * **The subtitle below is rewritten, `W46-WIRE`, `F-3`.** It used to say three of the four
 * panels read what was already available and the fourth had nothing to read — true while
 * this screen's own worktree held it, false the moment the merge landed the aggregate this
 * wave wires in: all four panels read the one aggregate now, sections included. The old
 * wording also named the two words `R-39`/`D-109` ask this screen to avoid; the rewrite
 * says what the screen shows instead of what feeds it.
 *
 * **The object comes from the address, and where it is silent, from the account** (`UI-PARITY-01`,
 * «Project context», `UIP-G-06`; the screen's registry class is `optional`). `useCurrentProject` reads
 * `?project=<uid>` first, then the explicit `?project=all`, then the object the account chose last
 * (`getMe`); it is handed to the widget as a prop and not kept: a reload, a pasted link and
 * Back/Forward restore it from the address and the account alone. No object anywhere is «Все объекты».
 * The way out of an unknown object is built here as well, with `switchProject(…, null)` (`?project=all`,
 * not the absence of the parameter, which would bring the same object back), because only the page
 * knows the rest of the address that the link must keep.
 */

import { useSearchParams } from 'next/navigation';

import { switchProject } from '@/shared/lib';
import { PageShell } from '@/shared/ui';
import { useCurrentProject } from '@/entities/project';

import { LazyDashboard } from './lazy-dashboard';

/** This screen's registry address, the one the registry classifies. */
const DASHBOARD_ADDRESS = '/dashboard';

/** What a render without a mounted router (a one-pass test render) reads as the query string. */
const NO_PARAMS = new URLSearchParams();

export function DashboardPage() {
  // Outside the app router there is no address; `DASHBOARD_ADDRESS` stands in for the screen's own.
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const { projectUid } = useCurrentProject(DASHBOARD_ADDRESS);
  const allProjects = switchProject(searchParams, null, projectUid).toString();
  const allProjectsHref = `${DASHBOARD_ADDRESS}?${allProjects}`;

  return (
    <div data-dashboard-screen="true" data-dashboard-showcase="true">
      <PageShell
        title="Анализ по разделам"
        subtitle="Разделы, документы, замечания и прогоны по текущим данным системы."
      >
        <LazyDashboard projectUid={projectUid} allProjectsHref={allProjectsHref} />
      </PageShell>
    </div>
  );
}
