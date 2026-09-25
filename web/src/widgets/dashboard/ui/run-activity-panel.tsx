'use client';

/**
 * Panel 3 — run activity and spend.
 *
 * `D1`: `listRuns` and `RunStatus`'s cost fields exist today; there is no global runs
 * listing, so this panel walks `useRunActivityWalk` — one page of projects, one page of
 * each project's documents, one page of each of those versions' runs — rather than
 * inventing a second aggregate operation. See that hook's own header for the bound and
 * why it is disclosed rather than hidden.
 *
 * **No invented numbers, the money case specifically.** `entities/audit-run`'s `runCost`
 * already treats "made no provider call" and "spent exactly zero" as different facts, and
 * `summarizeRunActivity` sums only the runs that reported a cost — a run with no call is
 * counted in `runsWithAbsentCost`, never folded into the sum as `0`.
 */

import { COST_BASIS_LABELS, EmptyState, ErrorState, LoadingState, STATE_LABELS } from '@/shared/ui';
import { classifyListingFailure } from '@/shared/lib';
import { formatCostMicros, costBasisCaption } from '@/entities/audit-run';
import type { RunState } from '@/shared/api';

import { useRunActivityWalk } from '../api/use-run-activity-walk';
import { summarizeRunActivity } from '../model/run-activity';

/** Every state worth a row, in the contract's own declared order. */
const STATE_ROWS: readonly RunState[] = [
  'created',
  'queued',
  'running',
  'validating',
  'published',
  'partial',
  'failed',
  'cancelled',
];

export function RunActivityPanel() {
  const walk = useRunActivityWalk();

  if (walk.isPending) return <LoadingState what="прогоны и расход" />;

  if (walk.isError) {
    const failure = classifyListingFailure(walk.error, {
      collection: 'прогоны и расход',
      parent: 'project',
    });
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable ? { onRetry: () => walk.refetch(), retryLabel: 'Повторить' } : {})}
      />
    );
  }

  if (walk.scannedProjectCount === 0) {
    return (
      <EmptyState
        title="Проектов пока нет."
        detail="Прогонов показывать нечего, пока не появится хотя бы один проект."
      />
    );
  }

  if (walk.runs.length === 0) {
    return (
      <EmptyState
        title="Прогонов пока нет."
        detail="Среди осмотренных проектов и версий ни один прогон ещё не запускался."
      />
    );
  }

  const summary = summarizeRunActivity(walk.runs);
  const scopeNote =
    walk.moreProjects || walk.moreDocuments || walk.moreRuns
      ? 'Осмотрен не весь охват: у проектов, документов или версий были дальнейшие ' +
        'страницы, которые этот просчёт не прошёл. Число ниже — по тому, что осмотрено, ' +
        'а не по всей системе.'
      : null;

  return (
    <div data-panel="run-activity-and-spend">
      <p>
        Прогонов: <strong>{summary.runCount}</strong> · проектов осмотрено:{' '}
        {walk.scannedProjectCount} · версий осмотрено: {walk.scannedVersionCount}.
      </p>
      {scopeNote !== null ? <p className="am-state__correlation">{scopeNote}</p> : null}

      <table>
        <caption>По состоянию</caption>
        <tbody>
          {STATE_ROWS.filter((state) => summary.byState[state] > 0).map((state) => (
            <tr key={state} data-run-state={state}>
              <th scope="row">{STATE_LABELS[state]}</th>
              <td>{summary.byState[state]}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p>
        {summary.runsWithReportedCost > 0 ? (
          <>
            Расход по прогонам, сообщившим стоимость ({summary.runsWithReportedCost} из{' '}
            {summary.runCount}): <strong>{formatCostMicros(summary.reportedCostMicros)}</strong> ·
            вызовов модели: {summary.modelCallCount}
            {summary.costBasis !== null ? (
              <>
                {' '}
                ·{' '}
                <span data-cost-basis={summary.costBasis}>
                  {COST_BASIS_LABELS[summary.costBasis]}
                </span>
              </>
            ) : null}
            .
          </>
        ) : (
          'Ни один осмотренный прогон не сообщил стоимости.'
        )}
      </p>
      {summary.costBasis !== null ? (
        <p className="am-state__correlation">{costBasisCaption(summary.costBasis)}</p>
      ) : null}
      {summary.runsWithAbsentCost > 0 ? (
        <p className="am-state__correlation">
          {summary.runsWithAbsentCost} из {summary.runCount} прогонов не делали ни одного
          обращения к провайдеру — это другой факт, чем нулевой расход, и в сумму выше не
          входит.
        </p>
      ) : null}
    </div>
  );
}
