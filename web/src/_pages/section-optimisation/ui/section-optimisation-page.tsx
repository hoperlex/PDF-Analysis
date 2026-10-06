/**
 * `/section-optimisation` — optimisation across a documentation section, on its way (`R-66`,
 * group «Работа»).
 *
 * An honest stub in `R-23`'s sense: it says the section is coming, what will be in it and
 * when — the "when" named by an event in words, never by a number. The owner ruled the
 * event: **after all sections are implemented.** Only the АР section is analysed today
 * (`ANALYSED_SECTION_CODE` in `entities/project`).
 *
 * Not `/optimisation`, which is the optimisation of one project and stays registered,
 * outside the menu, until it becomes a tab of the project screen. This one works across all
 * the documents of one documentation section. The frozen contract has no operation for it —
 * `docs/program/W50-REGISTRY-01.md` records the measurement — so the screen shows no number.
 */

import { RoutePlaceholder } from '@/shared/ui';

export function SectionOptimisationPage() {
  return (
    <RoutePlaceholder
      screen="Оптимизация разделов"
      route="/section-optimisation"
      promise="Здесь будет оптимизация в пределах раздела проектной документации: сразу по всем документам одного раздела, а не по каждому документу отдельно. Экран появится после того, как в приложении будут реализованы все разделы."
    />
  );
}
