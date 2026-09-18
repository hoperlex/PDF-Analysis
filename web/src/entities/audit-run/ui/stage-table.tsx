/**
 * Per-stage rows for a run.
 *
 * Uses `StageStatusBadge`, whose value set is `succeeded`, `partial`, `failed`,
 * `skipped` — the `StageResult` vocabulary. This is the one place `succeeded` is a legal
 * word in this slice, and it is legal here precisely because a stage is not a run.
 *
 * A stage the run has not reported yet renders as "not started" rather than as a missing
 * row: an absent row reads as "there is nothing to say about this stage", which is a
 * different claim from "this stage has not run".
 *
 * **Why there is a Took column.** `formatInstant` prints to the second. PC-01's stages
 * finish in tens of milliseconds, so Started and Finished are the same string on a real
 * run and the pair carries no information at all. The elapsed column is what makes the
 * two columns a measurement rather than a decoration.
 */

import type { StageStatus } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { elapsedMs, formatElapsed } from '../model/run-presentation';
import { StageStatusBadge } from '@/shared/ui';

import type { StageRow } from '../model/run-presentation';

export interface StageTableProps {
  readonly rows: readonly StageRow[];
}

function StatusCell({
  status,
  errorCode,
}: {
  readonly status: StageStatus | null;
  readonly errorCode: string | null;
}) {
  if (status === null) {
    return <em data-stage-status="not-reported">not started</em>;
  }
  return <StageStatusBadge status={status} errorCode={errorCode} />;
}

export function StageTable({ rows }: StageTableProps) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', padding: '0.35rem 0.75rem 0.35rem 0' }}>Stage</th>
            <th style={{ textAlign: 'left', padding: '0.35rem 0.75rem 0.35rem 0' }}>Status</th>
            <th style={{ textAlign: 'left', padding: '0.35rem 0.75rem 0.35rem 0' }}>Started</th>
            <th style={{ textAlign: 'left', padding: '0.35rem 0.75rem 0.35rem 0' }}>Finished</th>
            <th style={{ textAlign: 'left', padding: '0.35rem 0.75rem 0.35rem 0' }}>Took</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.stageId} data-stage-id={row.stageId}>
              <td style={{ padding: '0.35rem 0.75rem 0.35rem 0' }}>
                <code>{row.stageId}</code>
                {row.expected ? null : <em> (not scheduled by PC-01)</em>}
              </td>
              <td style={{ padding: '0.35rem 0.75rem 0.35rem 0' }}>
                <StatusCell status={row.status} errorCode={row.errorCode} />
              </td>
              <td style={{ padding: '0.35rem 0.75rem 0.35rem 0' }}>
                {formatInstant(row.startedAt)}
              </td>
              <td style={{ padding: '0.35rem 0.75rem 0.35rem 0' }}>
                {formatInstant(row.finishedAt)}
              </td>
              <td
                style={{ padding: '0.35rem 0.75rem 0.35rem 0' }}
                data-stage-elapsed={elapsedMs(row.startedAt, row.finishedAt) ?? 'unknown'}
              >
                {formatElapsed(elapsedMs(row.startedAt, row.finishedAt))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
