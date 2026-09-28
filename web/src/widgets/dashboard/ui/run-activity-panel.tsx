/**
 * Panel 3 — run activity and spend.
 *
 * `W46-WIRE`, `F-3b`. Presentational: `Dashboard` reads `getDashboardSummary` once and
 * hands this panel its `run_activity` and whether any project exists at all.
 *
 * **`spend` is coded to the shape after `W46-SPEND`'s reseal, against today's client.**
 * The generated `RunActivity.spend` is still typed required today; after the reseal it is
 * optional, absent exactly when the deployment has made no provider call at all — the same
 * distinction `RunStatus.cost_micros` already draws for one run, lifted to the whole
 * deployment (`docs/program/reviews/W46-JUDGE-A.md` §3, finding F-1). Reading it into a
 * local value typed `RunActivitySpend | undefined` typechecks against both clients: a
 * required field is assignable to an optional one, and an optional field reads the same
 * way once it is. **Absent renders as an honest sentence that no provider call has been
 * made — never `0` labelled measured.**
 *
 * **No walk, so no scan bound to disclose.** The old panel read a bounded client-side
 * fan-out (`useRunActivityWalk`, deleted) and its sentence talked about *"прогонов
 * осмотрено"* over the page it had followed. The aggregate counts the whole deployment
 * server-side, so that sentence would now be false; this one just states the total.
 *
 * **Which of "no projects" and "no runs yet" this is** cannot come from `run_activity`
 * alone — it carries no per-project dimension by design (same report, §3: *"consistent
 * with its own argument; not held against it"*). `hasProjects`, computed from the other
 * half of the same one read (`documents_by_project.length > 0`), is what tells the two
 * apart.
 */

import { COST_BASIS_LABELS, EmptyState, STATE_LABELS } from '@/shared/ui';
import { formatCostMicros, costBasisCaption } from '@/entities/audit-run';
import type { RunActivity, RunActivitySpend } from '@/shared/api';
import { RUN_STATE_VALUES } from '@/shared/api';

export interface RunActivityPanelProps {
  readonly activity: RunActivity;
  /** From `documents_by_project.length > 0` — the same one read, its other half. */
  readonly hasProjects: boolean;
}

export function RunActivityPanel({ activity, hasProjects }: RunActivityPanelProps) {
  if (!hasProjects) {
    return (
      <EmptyState
        title="Проектов пока нет."
        detail="Прогонов показывать нечего, пока не появится хотя бы один проект."
      />
    );
  }

  const byState = new Map(activity.by_state.map((row) => [row.state, row.count]));
  const totalRuns = activity.by_state.reduce((sum, row) => sum + row.count, 0);

  if (totalRuns === 0) {
    return (
      <EmptyState
        title="Прогонов пока нет."
        detail="Среди проектов системы ни один прогон ещё не запускался."
      />
    );
  }

  // `run_activity.spend` after `W46-SPEND`'s reseal: absent, not `0`, when nothing has
  // called a provider. Typed `| undefined` explicitly so this typechecks whether the
  // generated field is required (today) or optional (after the reseal).
  const spend: RunActivitySpend | undefined = activity.spend;

  return (
    <div data-panel="run-activity-and-spend">
      <p>
        Прогонов: <strong>{totalRuns}</strong>.
      </p>

      <table>
        <caption>По состоянию</caption>
        <tbody>
          {RUN_STATE_VALUES.filter((state) => (byState.get(state) ?? 0) > 0).map((state) => (
            <tr key={state} data-run-state={state}>
              <th scope="row">{STATE_LABELS[state]}</th>
              <td>{byState.get(state) ?? 0}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p>
        {spend !== undefined ? (
          <>
            Расход по всем прогонам: <strong>{formatCostMicros(spend.cost_micros)}</strong> ·
            вызовов модели: {spend.model_call_count} ·{' '}
            <span data-cost-basis={spend.cost_basis}>{COST_BASIS_LABELS[spend.cost_basis]}</span>.
          </>
        ) : (
          'Ни один прогон ещё не обращался к провайдеру — оценивать расход пока нечего.'
        )}
      </p>
      {spend !== undefined ? (
        <p className="am-state__correlation">{costBasisCaption(spend.cost_basis)}</p>
      ) : null}
    </div>
  );
}
