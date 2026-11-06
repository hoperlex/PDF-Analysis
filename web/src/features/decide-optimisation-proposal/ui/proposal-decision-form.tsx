'use client';

/**
 * The decision controls of one proposal (`W60-OPT-PROPOSALS-01`): «Принять», «Отклонить» and
 * «На доработку», with a comment that «На доработку» requires, and «Снять решение» (`UI-B-12`).
 *
 * Offered to an expert only (an administrator reads the decisions and does not make them,
 * `R-60`); the API checks again. A decision is appended, never changed: pressing a verdict
 * again adds a new event, and the proposal shows the latest. The button of the verdict that
 * is already current, with the same comment, is disabled — pressing it would only append a
 * duplicate. «Снять решение» appends a withdrawal, which takes the proposal back to «не решено»
 * and keeps the decision it withdrew in the history; it is offered only while a decision is in
 * force, and its comment is optional.
 */

import { useState } from 'react';

import type { OptimisationPassId, OptimisationProposal, ProposalVerdict } from '@/shared/api';
import type { FailureMessage } from '@/shared/api/failure-message';
import { ErrorState } from '@/shared/ui';
import { COMMENT_REQUIRED_TEXT, VERDICT_LABELS, decideFailureMessage } from '@/entities/optimisation-proposal';

import { useDecideOptimisationProposal } from '../model/use-decide-optimisation-proposal';

const VERDICTS: readonly ProposalVerdict[] = ['accept', 'reject', 'revise'];

/** Whether a decision is in force on the proposal: the latest event exists and is not a withdrawal. */
export function decisionInForce(current: OptimisationProposal['current_decision']): boolean {
  return current !== null && current.verdict !== 'revoke';
}

/** The comment as it is sent: trimmed, `null` when empty. */
export function normalisedComment(text: string): string | null {
  const trimmed = text.trim();
  return trimmed === '' ? null : trimmed;
}

export interface ProposalDecisionFormViewProps {
  readonly proposalId: string;
  readonly current: OptimisationProposal['current_decision'];
  readonly comment: string;
  readonly pending: boolean;
  readonly failure: FailureMessage | null;
  readonly onComment: (text: string) => void;
  readonly onDecide: (verdict: ProposalVerdict) => void;
}

/** The form from state already in hand. Rendered by the static harness in every branch. */
export function ProposalDecisionFormView({
  proposalId,
  current,
  comment,
  pending,
  failure,
  onComment,
  onDecide,
}: ProposalDecisionFormViewProps) {
  const sent = normalisedComment(comment);
  const reviseWithoutComment = sent === null;
  return (
    <div className="am-form" data-proposal-decision={proposalId}>
      <label htmlFor={`decision-comment-${proposalId}`}>Комментарий к решению</label>
      <textarea
        id={`decision-comment-${proposalId}`}
        rows={2}
        maxLength={2000}
        value={comment}
        onChange={(event) => onComment(event.target.value)}
      />
      <p className="am-form__hint">Для решения «На доработку» комментарий обязателен, для остальных — нет.</p>
      <div className="am-form__row">
        {VERDICTS.map((verdict) => {
          const repeats = current !== null && current.verdict === verdict && current.comment === sent;
          const blocked = verdict === 'revise' && reviseWithoutComment;
          return (
            <button
              key={verdict}
              type="button"
              className={verdict === 'accept' ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
              disabled={pending || repeats || blocked}
              aria-pressed={current !== null && current.verdict === verdict}
              onClick={() => onDecide(verdict)}
            >
              {VERDICT_LABELS[verdict]}
            </button>
          );
        })}
        {/* `UI-B-12`: appended like any decision; offered while one is in force. */}
        <button
          type="button"
          className="am-button am-button--quiet am-button--small"
          disabled={pending || !decisionInForce(current)}
          data-revoke-decision={proposalId}
          onClick={() => onDecide('revoke')}
        >
          {VERDICT_LABELS.revoke}
        </button>
      </div>
      {reviseWithoutComment ? (
        <p className="am-form__hint" data-revise-hint="">
          {COMMENT_REQUIRED_TEXT}
        </p>
      ) : null}
      {failure !== null ? (
        <ErrorState
          title="Решение по предложению не записано."
          detail={failure.detail}
          correlationId={failure.correlationId}
        />
      ) : null}
    </div>
  );
}

export interface ProposalDecisionFormProps {
  readonly passId: OptimisationPassId;
  readonly proposal: OptimisationProposal;
}

export function ProposalDecisionForm({ passId, proposal }: ProposalDecisionFormProps) {
  const [comment, setComment] = useState('');
  const mutation = useDecideOptimisationProposal();
  return (
    <ProposalDecisionFormView
      proposalId={proposal.optimisation_proposal_id}
      current={proposal.current_decision}
      comment={comment}
      pending={mutation.isPending}
      failure={
        mutation.error === null || mutation.error === undefined
          ? null
          : decideFailureMessage(mutation.error)
      }
      onComment={(text) => {
        mutation.reset();
        setComment(text);
      }}
      onDecide={(verdict) =>
        mutation.mutate(
          {
            passId,
            proposalId: proposal.optimisation_proposal_id,
            verdict,
            comment: normalisedComment(comment),
          },
          { onSuccess: () => setComment('') },
        )
      }
    />
  );
}
