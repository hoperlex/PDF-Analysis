'use client';

/**
 * The decision of one proposal (`W60-OPT-PROPOSALS-01`, `UIP-S09-03`): the entity's decision field -- ✓ green («Принять»), ✕ red
 * («Отклонить») and a one-line «Причина» -- and, beside ✕, the menu «⋯» with the two decisions the original has no button for:
 * «На доработку» and «Снять решение».
 *
 * Offered to an expert only (an administrator reads the decisions and does not make them, `R-60`); the API checks again. The field
 * is `DecisionReasonControl` of `entities/expert-decision`, the same one a finding's row and a record of the knowledge base carry; this
 * file draws no copy of it. A decision is appended, never changed (`Г9-B`): every press is one event at once and the text of the field
 * goes in it as its `comment`, so there is no draft and no «save all».
 *
 * **The reason.** ✓ and ✕ take it as it stands; it is optional. «На доработку» needs one: without it nothing is sent and the row says
 * «Для «На доработку» нужна причина» under the field. The field is emptied only when the server has written a press (`recordedKey`
 * changes, and a changed key mounts the field afresh); a refusal and a failure leave the text, so the next press can send it again.
 *
 * **What is not offered.** The field holds ✓ (✕) while that verdict is in force, as it does everywhere. «На доработку» is left out of the
 * menu while the same verdict stands with the same reason, because pressing it would only append a duplicate; «Снять решение» is in the
 * menu only while a decision is in force -- it appends a withdrawal, which takes the proposal back to «не решено» and keeps the decision
 * it withdrew in the history -- and its reason is optional too.
 *
 * **Why the view reads the text of the field itself.** The text of `DecisionReasonControl` is its own state: it hands it to ✓ and ✕ and
 * to nobody else, and a slot (`extra`) cannot ask for it. The menu's items need it, so the wrapper listens to the field's change events,
 * which bubble to it, and the container keeps the last text (`reason`). The container clears it when it remounts the field.
 */

import { useState } from 'react';

import type { OptimisationPassId, OptimisationProposal, ProposalVerdict, Verdict } from '@/shared/api';
import { Menu } from '@/shared/ui';
import type { MenuItem } from '@/shared/ui';
import { DecisionReasonControl } from '@/entities/expert-decision';
import type { DecisionNote } from '@/entities/expert-decision';
import { VERDICT_LABELS, decideFailureMessage } from '@/entities/optimisation-proposal';

import { useDecideOptimisationProposal } from '../model/use-decide-optimisation-proposal';

/** What the row says when «На доработку» is pressed with no reason in the field. Nothing is sent. */
export const REVISE_NEEDS_REASON_TEXT = 'Для «На доработку» нужна причина';

/** What the row says once the server has written the press. */
export const RECORDED_TEXT = 'Записано';

/** The name of the menu «⋯»: its trigger is a glyph, and a glyph is no name. */
export const MORE_DECISIONS_LABEL = 'Другие решения';

/** Whether a decision is in force on the proposal: the latest event exists and is not a withdrawal. */
export function decisionInForce(current: OptimisationProposal['current_decision']): boolean {
  return current !== null && current.verdict !== 'revoke';
}

/** The comment as it is sent: trimmed, `null` when empty. */
export function normalisedComment(text: string): string | null {
  const trimmed = text.trim();
  return trimmed === '' ? null : trimmed;
}

/**
 * The verdict the entity's field reads: ✓ or ✕ is in force when the proposal is accepted or rejected, and nothing else holds a
 * button -- not waiting, not sent back for revision, not withdrawn.
 */
function fieldVerdict(current: OptimisationProposal['current_decision']): Verdict {
  if (current === null) return 'pending';
  if (current.verdict === 'accept') return 'accepted';
  if (current.verdict === 'reject') return 'rejected';
  return 'pending';
}

/**
 * The items of «⋯», in the order the original's words suggest: the decision first, the withdrawal after it. `null` when there is
 * nothing to offer, which cannot happen (a «На доработку» that would repeat is a decision in force, and a decision in force can be
 * withdrawn) but is said rather than assumed.
 */
function moreDecisions(
  current: OptimisationProposal['current_decision'],
  reason: string,
  onDecide: (verdict: ProposalVerdict, reason: string) => void,
): readonly [MenuItem, ...MenuItem[]] | null {
  const items: MenuItem[] = [];
  const repeatsRevise = current !== null && current.verdict === 'revise' && current.comment === normalisedComment(reason);
  if (!repeatsRevise) {
    items.push({ kind: 'action', label: VERDICT_LABELS.revise, onChoose: () => onDecide('revise', reason) });
  }
  if (decisionInForce(current)) {
    items.push({ kind: 'action', label: VERDICT_LABELS.revoke, onChoose: () => onDecide('revoke', reason) });
  }
  const [first, ...rest] = items;
  return first === undefined ? null : [first, ...rest];
}

export interface ProposalDecisionFormViewProps {
  readonly proposalId: string;
  readonly current: OptimisationProposal['current_decision'];
  /** The text of the field as the container last read it (see the file's note); `''` before anything is typed. */
  readonly reason: string;
  /** The press on its way, if any. ✓ and ✕ show it; a revision or a withdrawal holds the whole control. */
  readonly sending: ProposalVerdict | null;
  /** The line under the field: «Записано», the refusal before sending or the server's reason. */
  readonly note: DecisionNote | null;
  /** Changes when a press has been written: the field is emptied then and only then. Absent until the first write. */
  readonly recordedKey?: string | undefined;
  /** The field's text changed. */
  readonly onReason: (text: string) => void;
  /** A press. The reason is the field's text, untrimmed: the container normalises it. */
  readonly onDecide: (verdict: ProposalVerdict, reason: string) => void;
}

/** The field and its menu from state already in hand. Rendered by the static harness in every branch. */
export function ProposalDecisionFormView({
  proposalId,
  current,
  reason,
  sending,
  note,
  recordedKey,
  onReason,
  onDecide,
}: ProposalDecisionFormViewProps) {
  const items = moreDecisions(current, reason, onDecide);
  const held = sending === 'revise' || sending === 'revoke';
  return (
    <div
      data-proposal-decision={proposalId}
      aria-busy={sending === null ? undefined : true}
      inert={held ? true : undefined}
      onChange={(event) => {
        // The field's own change events bubble here (the harness has no propagation, so a test calls this handler itself).
        const value = (event.target as { value?: unknown }).value;
        if (typeof value === 'string') onReason(value);
      }}
    >
      <DecisionReasonControl
        key={recordedKey ?? ''}
        verdict={fieldVerdict(current)}
        sending={sending === 'accept' || sending === 'reject' ? sending : null}
        note={note}
        onAccept={(text) => onDecide('accept', text)}
        onReject={(text) => onDecide('reject', text)}
        extra={
          items === null ? undefined : (
            <Menu label={MORE_DECISIONS_LABEL} trigger={<span aria-hidden="true">⋯</span>} items={items} />
          )
        }
      />
    </div>
  );
}

export interface ProposalDecisionFormProps {
  readonly passId: OptimisationPassId;
  readonly proposal: OptimisationProposal;
}

export function ProposalDecisionForm({ passId, proposal }: ProposalDecisionFormProps) {
  const mutation = useDecideOptimisationProposal();
  const [reason, setReason] = useState('');
  const [refused, setRefused] = useState(false);
  const [recordedKey, setRecordedKey] = useState<string | undefined>(undefined);

  let note: DecisionNote | null = null;
  if (refused) note = { tone: 'fail', text: REVISE_NEEDS_REASON_TEXT };
  else if (mutation.error !== null && mutation.error !== undefined) {
    note = { tone: 'fail', text: `Решение не записано. ${decideFailureMessage(mutation.error).detail}` };
  } else if (mutation.isSuccess) note = { tone: 'ok', text: RECORDED_TEXT };

  return (
    <ProposalDecisionFormView
      proposalId={proposal.optimisation_proposal_id}
      current={proposal.current_decision}
      reason={reason}
      sending={mutation.isPending ? (mutation.variables?.verdict ?? null) : null}
      note={note}
      recordedKey={recordedKey}
      onReason={(text) => {
        setReason(text);
        setRefused(false);
        // Writing again is the end of what the last press said, but not while it is on its way: a reset then would drop the
        // answer of a press that has not come back, and the field would not be emptied when it does.
        if (!mutation.isPending) mutation.reset();
      }}
      onDecide={(verdict, text) => {
        const comment = normalisedComment(text);
        if (verdict === 'revise' && comment === null) {
          setRefused(true);
          return;
        }
        setRefused(false);
        mutation.mutate(
          { passId, proposalId: proposal.optimisation_proposal_id, verdict, comment },
          {
            onSuccess: (answer) => {
              setRecordedKey(answer.decision.proposal_decision_id);
              setReason('');
            },
          },
        );
      }}
    />
  );
}
