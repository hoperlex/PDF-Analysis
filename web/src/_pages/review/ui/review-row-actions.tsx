'use client';

/**
 * ✓/✕ of one finding's row on «Разбор» (`R-151n`), connected.
 *
 * One `useRecordVerdict` per row, so each row keeps its own intent key and its own outcome. The press is the
 * panel's own command: the same observation, the same severity rule. The model's proposed severity is not a
 * decision (AGENTS §4), so ✓ on a finding whose severity the expert has not chosen is refused before anything is
 * sent, with the panel's sentence, and the finding opens in the panel where the severity is chosen.
 */

import type { Finding, FindingObservationId, FindingUid, RunId } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { useRecordVerdict, verdictRefusalMessage } from '@/features/record-verdict';
import type { RowNote } from '@/widgets/finding-list';
import { FindingRowActions } from '@/widgets/finding-list';

export interface ReviewRowActionsProps {
  readonly finding: Finding;
  readonly runId: RunId;
  /** Opens the finding in the decision panel. */
  readonly onOpen: (findingUid: string) => void;
}

/** Whether ✓ needs a severity the expert has not chosen yet. */
export function acceptNeedsSeverity(finding: Finding): boolean {
  return finding.observation.proposed_severity !== undefined && finding.decided_severity === undefined;
}

export function ReviewRowActions({ finding, runId, onOpen }: ReviewRowActionsProps) {
  const verdict = useRecordVerdict({ findingUid: finding.finding_uid as FindingUid, runId });
  const observationId = finding.observation.finding_observation_id as FindingObservationId;

  let note: RowNote | null = null;
  if (verdict.refusal !== null) note = { tone: 'fail', text: verdictRefusalMessage(verdict.refusal) };
  else if (verdict.error !== null && verdict.error !== undefined) note = { tone: 'fail', text: failureMessage(verdict.error).detail };
  else if (verdict.result !== null) note = { tone: 'ok', text: 'Записано' };

  return (
    <FindingRowActions
      verdict={verdict.result?.current_verdict ?? finding.current_verdict}
      sending={verdict.pendingIntent}
      note={note}
      onAccept={() => {
        verdict.record('accept', observationId, {
          proposed: finding.observation.proposed_severity,
          decided: finding.decided_severity,
        });
        if (acceptNeedsSeverity(finding)) onOpen(finding.finding_uid);
      }}
      onReject={() => {
        verdict.record('reject', observationId);
      }}
    />
  );
}
