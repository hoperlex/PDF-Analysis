'use client';

/**
 * «Перенести решения из V#» beside the proposals' exports on the document's «Оптимизация» tab (`UI-B-14`,
 * `carryOverProposalDecisions`).
 *
 * A new version of a document set gets a new pass with no decisions. The original lets an expert carry the decisions of
 * the previous version over (its «↩ Перенесено из V2»). Ours offers one button for each earlier version that has a pass of
 * this set; pressing it first says what will happen — the decisions in force of that pass, matched to this pass's
 * proposals by content, only where exactly one proposal has that content and nobody has decided it yet — and asks the
 * expert to confirm, because every carried decision is recorded under the expert's name. The answer is a short report in
 * which every source decision is counted once: carried, left as decided, doubtful (several identical proposals) or without
 * a counterpart. Nothing here guesses: what the server could not match is not carried.
 */

import { useState } from 'react';

import type { OptimisationPass, ProposalDecisionCarryoverReport } from '@/shared/api';
import {
  carryOverFailureMessage,
  carrySources,
  decidedCount,
  describeCarryover,
} from '@/entities/optimisation-proposal';
import type { CarrySource } from '@/entities/optimisation-proposal';

import { useCarryOverProposalDecisions } from '../model/use-carry-over-proposal-decisions';
import styles from './carry-over-proposal-decisions.module.css';

export interface CarryOverProposalDecisionsViewProps {
  /** The earlier versions that have a pass to carry from, newest first; none, nothing is rendered. */
  readonly sources: readonly CarrySource[];
  /** The source the expert pressed and has not yet confirmed; `null` when no confirmation is open. */
  readonly confirming: CarrySource | null;
  readonly pending: boolean;
  readonly report: ProposalDecisionCarryoverReport | null;
  readonly failure: string | null;
  readonly onAsk: (source: CarrySource) => void;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

/** What the confirmation says of the pass the decisions come from: how many are in force there. */
export function describeSourceDecisions(pass: OptimisationPass): string {
  const counts = pass.decision_counts;
  return `принято — ${counts.accept}, отклонено — ${counts.reject}, на доработку — ${counts.revise}`;
}

/** The control from state already in hand; rendered by the static harness in every branch. */
export function CarryOverProposalDecisionsView({
  sources,
  confirming,
  pending,
  report,
  failure,
  onAsk,
  onConfirm,
  onCancel,
}: CarryOverProposalDecisionsViewProps) {
  if (sources.length === 0) return null;
  return (
    <div className={styles.control} data-proposal-decision-carryover="">
      <div className={styles.sources}>
        {sources.map((source) => (
          <button
            key={source.pass.optimisation_pass_id}
            type="button"
            className="am-button am-button--quiet"
            disabled={pending || confirming !== null}
            data-carryover-source={source.versionOrdinal}
            onClick={() => onAsk(source)}
          >
            Перенести решения из V{source.versionOrdinal}
          </button>
        ))}
      </div>
      {confirming === null ? null : (
        <div className={styles.confirm} role="group" aria-label="Подтверждение переноса решений" data-carryover-confirm="">
          {decidedCount(confirming.pass) === 0 ? (
            <p>В V{confirming.versionOrdinal} нет решений для переноса ({describeSourceDecisions(confirming.pass)}).</p>
          ) : (
            <p>
              Решения V{confirming.versionOrdinal} ({describeSourceDecisions(confirming.pass)}) будут записаны от вашего
              имени в предложения этого прохода, которые совпадают с ними по содержанию — строке спецификации, позициям
              прайс-листа и обеим ценам — и по которым ещё ничего не решено. Если подходящих предложений несколько, ничего
              не переносится.
            </p>
          )}
          <div className={styles.actions}>
            <button type="button" className="am-button" disabled={pending} onClick={onConfirm}>
              {pending ? 'Переношу решения…' : `Перенести из V${confirming.versionOrdinal}`}
            </button>
            <button type="button" className="am-button am-button--quiet" disabled={pending} onClick={onCancel}>
              Отмена
            </button>
          </div>
        </div>
      )}
      {report === null ? null : (
        <ul className={styles.report} data-carryover-carried={report.carried} aria-label="Итог переноса решений">
          {describeCarryover(report).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
      {failure === null ? null : (
        <p className={styles.error} role="alert">
          {failure}
        </p>
      )}
    </div>
  );
}

export interface CarryOverProposalDecisionsProps {
  /** The pass the decisions are carried into: the open one. */
  readonly pass: OptimisationPass;
  /** The set's passes, newest first (`listOptimisationPasses`). */
  readonly passes: readonly OptimisationPass[];
}

/** The connected control: offers the earlier versions, asks for confirmation, sends one keyed request. */
export function CarryOverProposalDecisions({ pass, passes }: CarryOverProposalDecisionsProps) {
  const carry = useCarryOverProposalDecisions();
  const [confirming, setConfirming] = useState<CarrySource | null>(null);
  return (
    <CarryOverProposalDecisionsView
      sources={carrySources(passes, pass)}
      confirming={confirming}
      pending={carry.isPending}
      report={carry.data ?? null}
      failure={carry.error === null ? null : carryOverFailureMessage(carry.error).detail}
      onAsk={(source) => {
        carry.reset();
        setConfirming(source);
      }}
      onConfirm={() => {
        if (confirming === null) return;
        carry.mutate(
          { passId: pass.optimisation_pass_id, sourcePassId: confirming.pass.optimisation_pass_id },
          { onSettled: () => setConfirming(null) },
        );
      }}
      onCancel={() => setConfirming(null)}
    />
  );
}
