/**
 * `/workers` — distributed executors, and the one of the four that gets no promise.
 *
 * `R-23`'s addendum rules all four sections wanted. It also states, in the same ruling,
 * that *"Workers are excluded outright by `PROTOTYPE_PROFILE.md` §7"* — and §7.2's
 * **Deferred** list names both *"remote/distributed workers"* and the whole
 * *"automatic retry/skip/resume policy, Job/Attempt lease, heartbeat, fencing and
 * outbox"* framework around them.
 *
 * Wanted eventually and deferred now are not in tension; what they forbid is a screen
 * that reads as *coming soon*. `R-18` says a stub may not claim something false about
 * the system, and the default placeholder wording claims exactly that: `«Раздел пока
 * недоступен»` and `«Этот раздел ещё не готов»` both carry a *yet*. So this screen is
 * the reason `RoutePlaceholder` grew `unavailability` and `headline`, and it is the only
 * caller in the tree that passes them.
 *
 * `docs/program/W43-PREP.md` note 4 is the measurement behind the text: there is no
 * worker, job, attempt or lease table among the schema's sixteen, and `runs/executor.py`
 * runs the stages in order, in process. The stage registry's `remote_eligible` scope is
 * on paper and says of itself that it is *"a target statement, never a legacy parity
 * claim"*, so the screen does not cite it as evidence that workers are on their way.
 *
 * No date, and no count.
 */

import { RoutePlaceholder } from '@/shared/ui';

export function WorkersPage() {
  return (
    <RoutePlaceholder
      screen="Исполнители"
      route="/workers"
      unavailability="Раздела нет в альфе"
      headline="Распределённых исполнителей в альфе нет."
      promise="Прогон выполняет один последовательный исполнитель внутри самого приложения. Распределённые исполнители и связанный с ними учёт задач и попыток вынесены за границы альфы, поэтому здесь ничего не появится, пока это решение не изменится."
    />
  );
}
