/**
 * Panel 3 — run activity and spend.
 *
 * `W46-WIRE`, `F-3b`. Presentational: `Dashboard` reads `getDashboardSummary` once and
 * hands this panel its `run_activity` and whether any project exists at all.
 *
 * **`spend` is coded to the shape after `W46-SPEND`'s reseal.** The generated
 * `RunActivity.spend` is optional, absent exactly when the deployment has made no
 * provider call at all — the same distinction `RunStatus.cost_micros` already draws for
 * one run, lifted to the whole deployment (`docs/program/reviews/W46-JUDGE-A.md` §3,
 * finding F-1). **Absent renders as an honest sentence that no provider call has been
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
 *
 * **An omitted or unrecognised state row is a fault, never a hidden zero.**
 * `summarizeRunStateBreakdown` only returns a breakdown over the whole closed vocabulary —
 * all eight `RunState` members, each once. A response carrying only some of them used to
 * render the ones it had and drop the rest with no signal — not a false number, a hidden
 * true one, indistinguishable on screen from "the rest are genuinely zero". A response
 * carrying a state this module does not recognise used to vanish the same way. Both are
 * now the same fault, shown as `dashboard-failure.ts`'s shape rather than as a partial
 * table (`docs/program/reviews/W46-JUDGE-X.md` §`X2-a`).
 */

import { COST_BASIS_LABELS, ErrorState, EmptyState, STATE_LABELS } from '@/shared/ui';
import { formatCostMicros, costBasisCaption } from '@/entities/audit-run';
import type { RunActivity, RunActivitySpend } from '@/shared/api';
import { COST_BASIS_VALUES, RUN_STATE_VALUES } from '@/shared/api';

import { incompleteBreakdownFailure } from '../model/dashboard-failure';
import { summarizeRunStateBreakdown } from '../model/run-state-breakdown';

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

  const breakdown = summarizeRunStateBreakdown(activity.by_state);

  if (!breakdown.ok) {
    const failure = incompleteBreakdownFailure('Разбивка по состояниям прогонов пришла неполной.');
    return (
      <div data-panel="run-activity-and-spend" data-panel-fault={failure.kind}>
        <ErrorState title={failure.title} detail={failure.detail} />
      </div>
    );
  }

  if (breakdown.totalRuns === 0) {
    return (
      <EmptyState
        title="Прогонов пока нет."
        detail="Среди проектов системы ни один прогон ещё не запускался."
      />
    );
  }

  // `run_activity.spend` after `W46-SPEND`'s reseal: absent, not `0`, when nothing has
  // called a provider.
  const spend: RunActivitySpend | undefined = activity.spend;

  if (
    spend !== undefined &&
    !(COST_BASIS_VALUES as readonly unknown[]).includes(spend.cost_basis)
  ) {
    const failure = incompleteBreakdownFailure('Основание стоимости не распознано.');
    return (
      <div data-panel="run-activity-and-spend" data-panel-fault={failure.kind}>
        <ErrorState title={failure.title} detail={failure.detail} />
      </div>
    );
  }

  return (
    <div data-panel="run-activity-and-spend">
      <p>
        Прогонов: <strong>{breakdown.totalRuns}</strong>.
      </p>

      <table>
        <caption>По состоянию</caption>
        <tbody>
          {RUN_STATE_VALUES.filter((state) => breakdown.byState[state] > 0).map((state) => (
            <tr key={state} data-run-state={state}>
              <th scope="row">{STATE_LABELS[state]}</th>
              <td>{breakdown.byState[state]}</td>
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
