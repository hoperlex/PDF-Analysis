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
 */

import { PageShell } from '@/shared/ui';

import { LazyDashboard } from './lazy-dashboard';

export function DashboardPage() {
  return (
    <PageShell
      title="Дашборд"
      subtitle="Четыре панели одного общего чтения по всей системе: документы по проектам, находки по вердикту, прогоны и расход, и документы по разделам."
    >
      <LazyDashboard />
    </PageShell>
  );
}
