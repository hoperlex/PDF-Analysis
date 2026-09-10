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
 */

import Link from 'next/link';

import type { RunStatus } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { ErrorState, LoadingState, NotApplicableState, RunStateBadge } from '@/shared/ui';
import {
  StageTable,
  badgeProviderMode,
  interruptedReason,
  isRunAnimating,
  providerModeCaption,
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

      <p data-run-activity={animating && polling ? 'polling' : 'stopped'}>
        {animating && polling
          ? 'Polling for the next reading. The interval backs off from 2 s to 15 s and has no deadline; it stops when the run reaches a terminal state.'
          : animating
            ? 'Polling has stopped while the run is still open. The reading below is the last one received, not a final one.'
            : 'Not polling. This reading is final.'}
      </p>

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
      </dl>

      <Outcome status={status} />

      {interrupted !== null && status.state !== 'failed' ? (
        <p data-interrupted-reason={interrupted}>
          This run carries an interrupted reason: {interrupted}.
        </p>
      ) : null}

      <h2>Stages</h2>
      <StageTable rows={stageRows(status)} />

      <h2>Review</h2>
      {runHasPublishedResult(status.state) ? (
        <p>
          <Link href={`/projects/${projectUid}/runs/${status.run_id}/review`}>
            Review findings
          </Link>{' '}
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
