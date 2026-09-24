/**
 * `/optimisation` — tuning models and stages, prepared and not built.
 *
 * `R-23`'s addendum rules optimisation wanted and the preparation allowed now.
 *
 * The promise is bounded by `docs/program/W43-PREP.md` note 2, and it names the two
 * things that are actually in the way rather than saying "not implemented":
 *
 *   - **nothing is settable.** `StartRunRequest` has exactly two properties —
 *     `version_uid` and `provider_mode` — under `additionalProperties: false`. A run's
 *     profile and prompt bundle are readable on `RunStatus` and are chosen by the
 *     deployment, not by a caller;
 *   - **there is no section to tune per.** No section field exists anywhere in the data;
 *     `D-56` measured that, `R-25` rules the dashboard's section structure rendered
 *     without counts for the same reason, and the project-sections screen already says
 *     plainly that sections are navigation.
 *
 * The screen deliberately does not say how many stages there are. One analysis stage
 * among four scheduled is a true sentence today and a false one the week a stage is
 * added, and `OPERATING_CONSTRAINTS.md` §4.7 is about exactly that kind of sentence
 * outliving what it describes. The count lives in `W43-PREP.md`, where a command sits
 * next to it.
 */

import { RoutePlaceholder } from '@/shared/ui';

export function OptimisationPage() {
  return (
    <RoutePlaceholder
      screen="Оптимизация"
      route="/optimisation"
      promise="Здесь будет настройка анализа: какие модели и стадии применяются к документу и к разделу. Пока запуск прогона принимает только версию документа и режим работы с провайдером, а раздел документа нигде не хранится, поэтому выбирать здесь нечего."
    />
  );
}
