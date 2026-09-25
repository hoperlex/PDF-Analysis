/**
 * Panel 4 — per-section breakdown.
 *
 * `D1`: the only one of the four panels that needs `W46-SEAL`'s new aggregate read, and
 * `web/src/shared/api/generated/**` — the one place that operation could be called from —
 * is that stream's own hotspot, forbidden here. **This panel is not driven against real
 * data.** It shows the fourteen sections `D-56` measured, as structure, and says once why
 * there are no numbers next to them.
 *
 * `R-39` permits the reason in the words of the subject, and holds the line at operation
 * ids, field names and transport: the sentence below says a section is not counted
 * because nothing in this deployment checks or stores which section a document belongs
 * to — which is true today independently of `W46-SEAL` — and names no endpoint.
 *
 * `R-25`/`D-56`: this reuses `PROJECT_SECTIONS`, the one list of the fourteen the project
 * screen already carries, in its existing order, rather than declaring a second one. The
 * project screen's own header is where that order is argued; nothing here re-derives it.
 */

import { NotApplicableState } from '@/shared/ui';
import { ANALYSED_SECTION_CODE, PROJECT_SECTIONS, projectSectionTitle } from '@/entities/project';

export function SectionsPanel() {
  return (
    <div data-panel="per-section-breakdown">
      <NotApplicableState
        title="Разбивка находок по разделам здесь не считается."
        detail={
          <p>
            Раздел документа нигде в системе не хранится и не проверяется, поэтому находки
            нельзя посчитать по разделам. Ниже — сами четырнадцать разделов, без чисел: это
            структура, а не пустой отчёт.
          </p>
        }
      />
      <ul data-section-count={PROJECT_SECTIONS.length}>
        {PROJECT_SECTIONS.map((section) => (
          <li key={section.code} data-section={section.code} data-analysed={section.analysed}>
            {projectSectionTitle(section)}
            {section.code === ANALYSED_SECTION_CODE ? ' — единственный анализируемый раздел' : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}
