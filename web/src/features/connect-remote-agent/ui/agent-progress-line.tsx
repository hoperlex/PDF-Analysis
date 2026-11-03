'use client';

/**
 * One line of progress under the wizard's command or install session (`EXEC2-WEB-WIZARD-01`): the
 * first step of the agent's lifecycle that is not done yet, in words, read from the connection's
 * detail and re-read while it moves (`useAgentStatusPoll`).
 *
 * The full lifecycle with its actions is the panel on the connection's card (`AgentLifecyclePanel`);
 * the wizard shows only this line, so the same actions are not offered twice on one page.
 */

import { useExecutorConnectionDetail } from '@/entities/executor-connection';
import type { ExecutorConnectionId } from '@/shared/api';

import { agentIsMoving, agentLifecycle, currentStep } from '../model/lifecycle';
import { stepSentence } from '../model/step-sentences';
import { useAgentStatusPoll } from '../model/use-agent-polls';
import { STEP_LABELS, STEP_STATE_LABELS } from '../model/words';

export interface AgentProgressLineProps {
  readonly connectionId: ExecutorConnectionId;
  /** The clock of the page, injectable for a test. */
  readonly nowMs?: number | undefined;
}

const TONE = { done: 'ok', waiting: 'pending', attention: 'failed', inert: 'inert' } as const;

export function AgentProgressLine({ connectionId, nowMs }: AgentProgressLineProps) {
  const read = useExecutorConnectionDetail(connectionId);
  const now = nowMs ?? Date.now();
  const detail = read.data;
  useAgentStatusPoll(connectionId, detail !== undefined && agentIsMoving(detail, now));

  if (detail === undefined) {
    return <p className="am-form__hint" role="status" data-agent-progress="reading">Состояние агента читается…</p>;
  }
  const lifecycle = agentLifecycle(detail.connection, detail, now);
  const step = currentStep(lifecycle);
  return (
    <p role="status" data-agent-progress={step.id} data-agent-progress-state={step.state}>
      <span className={`am-badge am-badge--${TONE[step.state]}`}>{STEP_STATE_LABELS[step.state]}</span>{' '}
      <strong>{STEP_LABELS[step.id]}.</strong> {stepSentence(lifecycle, step.id)}
    </p>
  );
}
