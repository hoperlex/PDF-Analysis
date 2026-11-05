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
 * **The project comes from the address, here, and nowhere else** (`UI-PARITY-01`, «Project
 * context»; the screen's registry class is `optional`). `?project=` is read with
 * `readProjectContext`, handed to the widget as a prop, and not kept: a reload, a pasted link and
 * Back/Forward all restore it from the address alone. No `?project=` is «Все проекты». The way
 * out of an unknown project is built here as well, with `switchProject(…, null)`, because only the
 * page knows the rest of the address that the link must keep.
 */

import { usePathname, useSearchParams } from 'next/navigation';

import { readProjectContext, switchProject } from '@/shared/lib';
import { PageShell } from '@/shared/ui';

import { LazyDashboard } from './lazy-dashboard';

/** This screen's registry address, the one `readProjectContext` classifies. */
const DASHBOARD_ADDRESS = '/dashboard';

/** What a render without a mounted router (a one-pass test render) reads as the query string. */
const NO_PARAMS = new URLSearchParams();

export function DashboardPage() {
  // `null` only where no router is mounted; the address is then no address and names no project.
  const pathname = usePathname();
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const { projectUid } = readProjectContext(pathname ?? '', searchParams);
  const withoutProject = switchProject(searchParams, null).toString();
  const allProjectsHref = withoutProject === '' ? DASHBOARD_ADDRESS : `${DASHBOARD_ADDRESS}?${withoutProject}`;

  return (
    <div data-dashboard-screen="true" data-dashboard-showcase="true">
      <PageShell
        title="Анализ по разделам"
        subtitle="Разделы, документы, находки и прогоны по текущим данным системы."
      >
        <LazyDashboard projectUid={projectUid} allProjectsHref={allProjectsHref} />
      </PageShell>
    </div>
  );
}
