'use client';

/**
 * The decision field of one finding on «Разбор» (`R-151n`, `UIP-S06-02`), connected: ✓, ✕ and «Причина».
 *
 * One `useRecordVerdict` per row, so each row keeps its own intent key and its own outcome. The press is the
 * panel's own command: the same observation, the same severity rule, and the text of the field goes in the same
 * event as its `comment`. The model's proposed severity is not a decision (AGENTS §4), so ✓ on a finding whose
 * severity the expert has not chosen is refused before anything is sent, with the panel's sentence, and the finding
 * opens in the panel where the severity is chosen; the text stays in the field.
 *
 * This row owns the field's emptying: it empties it when, and only when, the server has written a press (a new event
 * in the answer). A refusal before sending and a failure leave the text, so pressing again sends the same intent and
 * reuses its key. The same component stands in the table's «Решение» column, in a list row and in the full-screen
 * view's side column, each with its own row state.
 */

import { useState } from 'react';

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

  // The field is emptied by mounting it afresh under a new key, and the key is the id of the event the server last
  // wrote for this row. It is kept here, not read from `verdict.result`, because a result goes back to nothing while
  // the next press is out: a key read from it would empty the text on every press, including one that then fails.
  const writtenId = verdict.result?.event.decision_id ?? null;
  const [recordedId, setRecordedId] = useState<string | null>(null);
  if (writtenId !== null && writtenId !== recordedId) setRecordedId(writtenId);
  const recordedKey = writtenId ?? recordedId ?? undefined;

  let note: RowNote | null = null;
  if (verdict.refusal !== null) note = { tone: 'fail', text: verdictRefusalMessage(verdict.refusal) };
  else if (verdict.error !== null && verdict.error !== undefined) note = { tone: 'fail', text: failureMessage(verdict.error).detail };
  else if (verdict.result !== null) note = { tone: 'ok', text: 'Записано' };

  return (
    <FindingRowActions
      verdict={verdict.result?.current_verdict ?? finding.current_verdict}
      sending={verdict.pendingIntent}
      note={note}
      recordedKey={recordedKey}
      onAccept={(reason) => {
        verdict.record(
          'accept',
          observationId,
          { proposed: finding.observation.proposed_severity, decided: finding.decided_severity },
          reason,
        );
        if (acceptNeedsSeverity(finding)) onOpen(finding.finding_uid);
      }}
      onReject={(reason) => {
        verdict.record('reject', observationId, undefined, reason);
      }}
    />
  );
}
