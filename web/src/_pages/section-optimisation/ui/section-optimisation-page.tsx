'use client';

/**
 * `/section-optimisation` — «Оптимизация разделов» (`R-66`, group «Работа»;
 * `W63-SECTION-FORM7-01`).
 *
 * Graduated from the honest stub: `getSectionSpecification` answers, for a section, the
 * combined Form-7 specification of the current versions of every project whose document set an
 * expert confirmed in it — the nine columns of the form with the project, set, version, sheet
 * and page on every row, a project filter and a text search, and each row's match against its
 * own project's price list. It is a read view: replicating an accepted optimisation into other
 * projects is a later slice, and nothing here writes. The section code only filters; rows are
 * never merged across projects and the totals exist per project and per currency.
 *
 * Not `/optimisation`, which is the optimisation of one project and stays registered, outside
 * the menu, until it becomes a tab of the project screen.
 */

import { PageShell } from '@/shared/ui';
import { SectionSpecificationSection } from '@/widgets/section-specification';

export function SectionOptimisationPage() {
  return (
    <PageShell
      title="Оптимизация разделов"
      subtitle="Сводная спецификация раздела по текущим версиям комплектов всех проектов. Экран только показывает данные: переносить решения между проектами здесь пока нельзя."
    >
      <SectionSpecificationSection />
    </PageShell>
  );
}
