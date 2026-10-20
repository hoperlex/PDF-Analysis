'use client';

/**
 * «Перенести решение» on one comparison row (`W59-DECISION-CARRYOVER-01`).
 *
 * The row is a «Без изменений» proposal whose older finding carries an expert decision and
 * whose newer finding has none. Pressing the button opens a confirmation that shows exactly
 * what would be carried — the older decision with its author, time, severity and comment —
 * and the finding of the newer version that would receive it. Only «Подтвердить перенос»
 * sends the command; «Отмена» closes the confirmation and nothing is written. The server
 * recomputes the comparison when the confirmation arrives and appends one decision on the
 * newer finding, authored by the confirming expert; the older finding and its decisions are
 * never touched.
 *
 * `CarryOverDecisionView` is the whole markup, driven by props, so every state can be rendered
 * by the static harness; `CarryOverDecision` adds the state and the command.
 */

import { useState } from 'react';

import type { CarryOverDecisionResponse, CarryoverCandidate, FindingRef } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import type { CarryoverFailure } from '@/entities/document-version';
import { carryoverFailure } from '@/entities/document-version';
import { CATEGORY_LABELS, VERDICT_LABELS } from '@/entities/expert-decision';
import { SEVERITY_LABELS } from '@/entities/finding';

import type { CarryOverDecisionCommand } from '../model/use-carry-over-decision';
import { useCarryOverDecision } from '../model/use-carry-over-decision';

export interface CarryOverDecisionViewProps {
  readonly candidate: CarryoverCandidate;
  readonly target: FindingRef;
  readonly confirming: boolean;
  readonly pending: boolean;
  readonly result: CarryOverDecisionResponse | null;
  readonly failure: CarryoverFailure | null;
  readonly onOpen: () => void;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

function SourceDecision({ candidate }: { readonly candidate: CarryoverCandidate }) {
  const decision = candidate.source_decision;
  return (
    <p data-carryover-source-decision={decision.decision_id}>
      Решение по замечанию более ранней версии: <strong>{VERDICT_LABELS[decision.verdict]}</strong>
      {decision.severity === null ? null : <> · значимость: {SEVERITY_LABELS[decision.severity]}</>} ·{' '}
      {decision.author_label}, {formatInstant(decision.recorded_at)}.
      {decision.comment === null ? null : <> Комментарий: «{decision.comment}».</>}
    </p>
  );
}

export function CarryOverDecisionView({
  candidate,
  target,
  confirming,
  pending,
  result,
  failure,
  onOpen,
  onConfirm,
  onCancel,
}: CarryOverDecisionViewProps) {
  if (result !== null) {
    return (
      <p
        className="am-note"
        role="status"
        data-carryover-state={result.replayed ? 'replayed' : 'carried'}
        data-carried-decision={result.event.decision_id}
      >
        {result.replayed
          ? 'Это решение уже было перенесено ранее; повторный перенос ничего не изменил.'
          : `Решение перенесено: замечание более поздней версии — ${VERDICT_LABELS[result.current_verdict]}.`}
      </p>
    );
  }
  if (!confirming) {
    return (
      <div data-carryover-state="offered">
        <p className="am-note">
          В более ранней версии: {VERDICT_LABELS[candidate.source_decision.verdict]}.
        </p>
        <button type="button" className="am-button am-button--small" onClick={onOpen}>
          Перенести решение
        </button>
        {failure === null ? null : (
          <p className="am-decision__refusal" role="alert" data-carryover-failure={failure.kind}>
            {failure.detail}
            {failure.correlationId === null ? null : <> Код обращения: <code>{failure.correlationId}</code>.</>}
          </p>
        )}
      </div>
    );
  }
  return (
    <div role="group" aria-label="Подтверждение переноса решения" data-carryover-state="confirming">
      <SourceDecision candidate={candidate} />
      <p data-carryover-target={target.finding_uid}>
        Получит решение замечание более поздней версии: {CATEGORY_LABELS[target.category]} —{' '}
        {target.finding_text} ({target.page_numbers.map((page) => `лист ${page}`).join(', ')}).
      </p>
      <p className="am-note">
        Будет добавлено новое решение от вашего имени с отметкой, из какой версии и какого решения
        оно перенесено. Решение по более ранней версии не изменится.
      </p>
      <button type="button" className="am-button am-button--small" disabled={pending} onClick={onConfirm}>
        {pending ? 'Переносим…' : 'Подтвердить перенос'}
      </button>{' '}
      <button
        type="button"
        className="am-button am-button--small am-button--quiet"
        disabled={pending}
        onClick={onCancel}
      >
        Отмена
      </button>
    </div>
  );
}

export interface CarryOverDecisionProps {
  readonly command: CarryOverDecisionCommand;
  readonly target: FindingRef;
}

export function CarryOverDecision({ command, target }: CarryOverDecisionProps) {
  const [confirming, setConfirming] = useState(false);
  const mutation = useCarryOverDecision();
  return (
    <CarryOverDecisionView
      candidate={command.candidate}
      target={target}
      confirming={confirming}
      pending={mutation.isPending}
      result={mutation.data ?? null}
      failure={mutation.isError ? carryoverFailure(mutation.error) : null}
      onOpen={() => {
        mutation.reset();
        setConfirming(true);
      }}
      onConfirm={() => {
        if (mutation.isPending) return;
        mutation.mutate(command, { onSettled: () => setConfirming(false) });
      }}
      onCancel={() => setConfirming(false)}
    />
  );
}
