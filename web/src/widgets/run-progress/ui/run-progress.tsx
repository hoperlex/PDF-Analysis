'use client';

/**
 * Run progress.
 *
 * The one screen that polls, and it polls through `pollRunStatus` in `@/shared/api` —
 * the single loop, at the frozen 2 s / ×1.5 / 15 s schedule, with no deadline.
 *
 * What this widget is careful about:
 *
 *   **The state is the contract's word.** `RunStateBadge` renders `created`, `queued`,
 *   `running`, `validating`, `published`, `partial`, `failed` or `cancelled` and nothing
 *   else. There is no "in progress", no "done" and no "OK". `succeeded` is a stage
 *   status and appears only in the stage table below, where it is correct.
 *
 *   **`published` is the success terminal, and `partial` and `failed` borrow nothing
 *   from it.** A `partial` run states its recorded degradation set; a `failed` run states
 *   the catalog code it terminated with, and its interrupted reason when `OD-10`
 *   reconciled it.
 *
 *   **A recorded run never reads as a live one.** The provider mode sits on the badge and
 *   again as a sentence, and a reading that carries no recognised mode says `unknown` —
 *   never `live`.
 *
 *   **Motion stops when the run stops.** A terminal or reconciled reading shows no
 *   activity indicator, because there is no activity.
 *
 *   **The screen leads with what the run did, not with what the poller is doing.**
 *   `DEBT_REGISTER.md` `D-20` is open: `execute_run` is inline, so a run is already
 *   `published` when `startRun` answers and there is no observable `running` state to
 *   watch. Every real reading is therefore terminal, `isRunAnimating` is false, and the
 *   activity line reads "Not polling. This reading is final." That sentence is true, and
 *   it is the one thing on this screen a user cannot otherwise check, so it stays — but
 *   it sits below the result rather than above it. Leading a terminal run with a
 *   paragraph about polling puts machinery where the answer belongs.
 *
 *   **Two counts, never one.** Published findings are admitted evidence; diagnostic
 *   observations are what the run noticed and did not admit. They are rendered apart and
 *   never summed. The finding count stays inside `Outcome`, where it is scoped to the
 *   states that can have one — a `cancelled` run published nothing, and "Published
 *   findings: 0" would be a claim about a publication that never happened.
 *
 *   **A cost is never shown without the count it sums.** `D-15` is open: the total spans
 *   retry attempts. `runCost` returns `unreadable` rather than print a figure whose span
 *   the reader cannot see.
 */

import Link from 'next/link';

import type { RunStatus } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { ErrorState, LoadingState, NotApplicableState, RunStateBadge } from '@/shared/ui';
import {
  StageTable,
  badgeProviderMode,
  costBasisCaption,
  diagnosticObservationCount,
  elapsedMs,
  formatCostMicros,
  formatElapsed,
  interruptedReason,
  isRunAnimating,
  providerModeCaption,
  runCost,
  runHasPublishedResult,
  runOutcome,
  runProviderMode,
  stageRows,
  useRunStatus,
} from '@/entities/audit-run';

export interface RunProgressProps {
  readonly projectUid: string;
  readonly runId: string;
}

function Outcome({ status }: { readonly status: RunStatus }) {
  const outcome = runOutcome(status);

  switch (outcome.kind) {
    case 'in_flight':
      return (
        <p data-run-outcome="in_flight">
          The run is in <code>{outcome.state}</code>. No result has been published yet, and
          none is implied.
        </p>
      );
    case 'published':
      return (
        <div data-run-outcome="published">
          <p>
            The run reached its success terminal, <code>published</code>.
          </p>
          <p>
            Published findings:{' '}
            {outcome.findingCount === null ? <em>not reported</em> : outcome.findingCount}
          </p>
        </div>
      );
    case 'partial':
      return (
        <div data-run-outcome="partial">
          <p>
            The run terminated <code>partial</code>. It published a result with a recorded
            degradation; it did not complete every stage, and it is not a{' '}
            <code>published</code> run.
          </p>
          {outcome.degradation.length === 0 ? (
            <p>
              <em>The reading carries no degradation set.</em>
            </p>
          ) : (
            <>
              <p>Missing or degraded stages:</p>
              <ul>
                {outcome.degradation.map((stageId) => (
                  <li key={stageId} data-degraded-stage={stageId}>
                    <code>{stageId}</code>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      );
    case 'failed':
      return (
        <div data-run-outcome="failed">
          <p>
            The run terminated <code>failed</code>. Nothing was published.
          </p>
          <p>
            Terminal reason:{' '}
            {outcome.terminalReason === null ? (
              <em>not reported</em>
            ) : (
              <code data-terminal-reason={outcome.terminalReason}>{outcome.terminalReason}</code>
            )}
          </p>
          {outcome.interrupted === null ? null : (
            <p data-interrupted-reason={outcome.interrupted}>
              This run was interrupted and reconciled: {outcome.interrupted}. It is not
              still running.
            </p>
          )}
        </div>
      );
    case 'cancelled':
      return (
        <p data-run-outcome="cancelled">
          The run terminated <code>cancelled</code>. Nothing was published.
        </p>
      );
  }
}

/**
 * What the run recorded and what it spent.
 *
 * Two counts that are never added together and a cost that is never invented.
 */
function Recorded({ status }: { readonly status: RunStatus }) {
  const diagnostics = diagnosticObservationCount(status);
  const cost = runCost(status);

  return (
    <>
      <h2>Diagnostic observations</h2>
      <p>
        Recorded:{' '}
        {diagnostics === null ? (
          <em data-diagnostic-observation-count="not-reported">not reported</em>
        ) : (
          <strong data-diagnostic-observation-count={diagnostics}>{diagnostics}</strong>
        )}
      </p>
      <p>
        A diagnostic observation is something the run noticed and did not admit as
        evidence. It is not a finding, it is not counted as one, and the two totals are
        never added together.
      </p>

      <h2>Cost</h2>
      {cost.kind === 'absent' ? (
        <p data-run-cost="absent">
          This run made no provider call, so it has no cost to report. That is not a cost
          of zero — nothing was spent here because nothing was called, and the two are
          different claims.
        </p>
      ) : cost.kind === 'unreadable' ? (
        <p data-run-cost="unreadable">
          This reading&apos;s cost cannot be read: {cost.why}. No figure is shown, because
          a total whose span the reader cannot see is not one they can act on.
        </p>
      ) : (
        <div data-run-cost="reported">
          <dl>
            <dt>Spent</dt>
            <dd data-cost-micros={cost.micros}>
              <strong>{formatCostMicros(cost.micros)}</strong> provider currency units{' '}
              <span>
                (<code>{cost.micros}</code> millionths, the integer the run stored)
              </span>
            </dd>
            <dt>Provider calls this total sums</dt>
            <dd data-model-call-count={cost.callCount}>{cost.callCount}</dd>
            <dt>Basis</dt>
            <dd data-cost-basis={cost.basis ?? 'unstated'}>
              <code>{cost.basis ?? 'unstated'}</code>
            </dd>
          </dl>
          <p>{costBasisCaption(cost.basis)}</p>
          <p>
            The total sums every provider call this run made, retries included. The call
            count is printed beside it so a run that answered first time can be told from
            one that was retried.
          </p>
          {cost.micros === 0 ? (
            <p data-run-cost-zero="reported">
              This run called the provider{' '}
              {cost.callCount === 1 ? 'once' : `${cost.callCount} times`} and was charged
              nothing. This is a reported zero, not an absent cost.
            </p>
          ) : null}
        </div>
      )}
    </>
  );
}

export function RunProgress({ projectUid, runId }: RunProgressProps) {
  const { status, failure, polling, retry } = useRunStatus(runId);

  if (status === null && failure !== null) {
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-run-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable ? { onRetry: retry, retryLabel: 'Try again' } : {})}
      />
    );
  }

  if (status === null) return <LoadingState what="the run" />;

  const mode = runProviderMode(status);
  const animating = isRunAnimating(status);
  const interrupted = interruptedReason(status);

  return (
    <div data-run-id={status.run_id}>
      <p style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <RunStateBadge state={status.state} providerMode={badgeProviderMode(mode)} />
        <span data-provider-mode={mode}>
          provider mode: <strong>{mode}</strong>
        </span>
      </p>
      <p>{providerModeCaption(mode)}</p>

      <dl>
        <dt>Run</dt>
        <dd>
          <code>{status.run_id}</code>
        </dd>
        <dt>Version</dt>
        <dd>
          <code>{status.version_uid}</code>
        </dd>
        <dt>Created</dt>
        <dd>{formatInstant(status.created_at)}</dd>
        <dt>Terminal at</dt>
        <dd>{formatInstant(status.terminal_at)}</dd>
        <dt>Took</dt>
        <dd data-run-elapsed={elapsedMs(status.created_at, status.terminal_at) ?? 'unknown'}>
          {formatElapsed(elapsedMs(status.created_at, status.terminal_at))}
        </dd>
      </dl>

      <p>
        <Link href={routes.version(status.project_uid, status.version_uid)}>
          The version this run read
        </Link>{' '}
        — <code>{status.version_uid}</code>. A run never changes the version it read, and
        that version&apos;s other runs are listed there.
      </p>

      <Outcome status={status} />

      {interrupted !== null && status.state !== 'failed' ? (
        <p data-interrupted-reason={interrupted}>
          This run carries an interrupted reason: {interrupted}.
        </p>
      ) : null}

      <Recorded status={status} />

      <h2>Stages</h2>
      <StageTable rows={stageRows(status)} />

      <h2>Review</h2>
      {runHasPublishedResult(status.state) ? (
        <p>
          <Link href={routes.review(projectUid, status.run_id)}>Review findings</Link>{' '}
          — this run&apos;s provider mode is <strong>{mode}</strong>.
        </p>
      ) : (
        <NotApplicableState
          title="There is nothing to review."
          detail={
            <p>
              A run has findings only once its terminal publishes a result —{' '}
              <code>published</code> or <code>partial</code>. This run is{' '}
              <code>{status.state}</code>.
            </p>
          }
        />
      )}

      <h2>Is this reading final?</h2>
      <p data-run-activity={animating && polling ? 'polling' : 'stopped'}>
        {animating && polling
          ? 'Polling for the next reading. The interval backs off from 2 s to 15 s and has no deadline; it stops when the run reaches a terminal state.'
          : animating
            ? 'Polling has stopped while the run is still open. The reading above is the last one received, not a final one.'
            : 'Not polling. This reading is final.'}
      </p>

      {failure !== null ? (
        <ErrorState
          title={failure.title}
          detail={
            <span data-run-failure={failure.kind}>
              {failure.detail} The reading above is the last one received.
            </span>
          }
          correlationId={failure.correlationId}
          {...(failure.retryable ? { onRetry: retry, retryLabel: 'Try again' } : {})}
        />
      ) : null}
    </div>
  );
}
