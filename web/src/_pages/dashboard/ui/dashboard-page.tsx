'use client';

/**
 * `/dashboard` — `R-44`, `R-18` applied at screen scope: real numbers where the surface
 * already carries them, honest structure where it does not.
 *
 * Composition only: the shell from `shared/ui`, the four panels from `widgets/dashboard`.
 */

import { PageShell } from '@/shared/ui';
import { Dashboard } from '@/widgets/dashboard';

export function DashboardPage() {
  return (
    <PageShell
      title="Дашборд"
      subtitle="Четыре панели. Три читают то, что уже отдаёт контракт; разбивка по разделам показывает только структуру — операции, которая считала бы находки по разделу, в этом контракте пока нет."
    >
      <Dashboard />
    </PageShell>
  );
}
