'use client';

/**
 * «Удалённый агент» on a connection's card (`EXEC2-WEB-WIZARD-01`, ADR-0026 decisions 4, 5, 8 and 9):
 * one lifecycle for both install paths, read from the connection's detail.
 *
 *     регистрация → агент в сети → клиент установлен → вход действителен → [отметка] → проба → готово
 *
 * A row says what is true now and, where somebody has to act, offers the action beside it: a new
 * command when the registration is waiting, expired or replaced; the guidance for a missing client or
 * a client that is not signed in, with «Проверить снова»; the administrator's mark with the `R-149b`
 * note; the old token's revocation after a move; and «Перенести на другой сервер». The model probe is
 * run by the card's own «Проверить», which this panel does not duplicate.
 *
 * **The four statuses are four rows** — installed, login valid, authorised for this integration,
 * probe passed — and none is derived from another (`lifecycle.ts`). The mark is the administrator's,
 * not a gate of «готово».
 *
 * The panel draws nothing for a connection that is not an agent connection (a `pull` connection meant
 * for a Claude Code session has the token panel and nothing else) and nothing while the detail is
 * still being read. While something moves — a grant waiting to be used, an agent that just registered
 * — it asks for the detail again every few seconds (`useAgentStatusPoll`) and stops by itself.
 */

import { useQueryClient } from '@tanstack/react-query';

import type { ExecutorConnection, ExecutorConnectionDetail } from '@/shared/api';
import { queryKeys } from '@/shared/api';

import { agentIsMoving, agentLifecycle, isAgentConnection } from '../model/lifecycle';
import { useAgentStatusPoll } from '../model/use-agent-polls';
import {
  COMMAND_GET_LABEL,
  COMMAND_NEW_LABEL,
  LIFECYCLE_INDEPENDENT_NOTE,
  LIFECYCLE_TITLE,
  MOVE_PENDING_NOTE,
  STEP_LABELS,
} from '../model/words';
import { CliList, LoginGuidance, MissingCliGuidance, StepRow } from './agent-steps';
import { EnrollmentCommandControl } from './enrollment-command';
import { IntegrationMark } from './integration-mark';
import { MoveAgentControl, SupersededTokens } from './move-agent';
import styles from './connect-remote-agent.module.css';

export interface AgentLifecyclePanelProps {
  readonly connection: ExecutorConnection;
  /** The connection's detail; absent while it is read or when the read failed. */
  readonly detail: ExecutorConnectionDetail | undefined;
  /** An administrator: the actions are drawn. The server still checks every write. */
  readonly canManage: boolean;
  /** The instant «в сети» is judged against; the page's clock, injectable for a test. */
  readonly nowMs?: number | undefined;
}

export function AgentLifecyclePanel({ connection, detail, canManage, nowMs }: AgentLifecyclePanelProps) {
  const client = useQueryClient();
  const now = nowMs ?? Date.now();
  const agent = detail !== undefined && isAgentConnection(connection, detail);
  useAgentStatusPoll(connection.connection_id, agent && agentIsMoving(detail, now));

  if (detail === undefined || !agent) return null;

  const lifecycle = agentLifecycle(connection, detail, now);
  const archived = connection.archived_at !== undefined;
  const admin = canManage && !archived;
  const registration = lifecycle.steps.registration.reason;
  const needsCommand = registration !== 'registered';
  const login = lifecycle.steps.login;
  const recheck = () => { void client.invalidateQueries({ queryKey: queryKeys.execution.all() }); };

  return (
    <section
      className="am-section"
      aria-label={LIFECYCLE_TITLE}
      data-agent-lifecycle={connection.connection_id}
      data-agent-ready={lifecycle.ready ? 'yes' : 'no'}
    >
      <h3>{LIFECYCLE_TITLE}</h3>
      <p>
        <span className={`am-badge am-badge--${lifecycle.ready ? 'ok' : 'pending'}`} data-agent-ready-badge>
          {lifecycle.ready ? STEP_LABELS.ready : 'Не готово к работе'}
        </span>
      </p>
      <p className="am-form__hint">{LIFECYCLE_INDEPENDENT_NOTE}</p>
      {lifecycle.pendingEnrollment !== null && lifecycle.token !== null ? (
        <p className="am-note" role="status" data-agent-move-pending>{MOVE_PENDING_NOTE}</p>
      ) : null}

      <ol className={styles.steps} aria-label="Путь агента">
        <StepRow lifecycle={lifecycle} id="registration">
          {admin && needsCommand ? (
            <EnrollmentCommandControl
              resolveConnection={async () => connection.connection_id}
              startLabel={registration === 'not_started' ? COMMAND_GET_LABEL : COMMAND_NEW_LABEL}
            />
          ) : null}
        </StepRow>
        <StepRow lifecycle={lifecycle} id="online" />
        <StepRow lifecycle={lifecycle} id="installed">
          <CliList clis={lifecycle.clis} mode="installed" />
          {admin && lifecycle.steps.installed.reason === 'missing' ? <MissingCliGuidance onRecheck={recheck} /> : null}
        </StepRow>
        <StepRow lifecycle={lifecycle} id="login">
          <CliList clis={lifecycle.clis} mode="login" />
          {admin && login.reason !== 'valid' && login.reason !== 'no_client' ? (
            <LoginGuidance clis={lifecycle.clis} onRecheck={recheck} />
          ) : null}
        </StepRow>
        <StepRow lifecycle={lifecycle} id="authorised">
          <IntegrationMark connection={connection} canManage={admin} />
        </StepRow>
        <StepRow lifecycle={lifecycle} id="probe" />
        <StepRow lifecycle={lifecycle} id="ready" />
      </ol>

      {admin && lifecycle.supersededTokens.length > 0 ? (
        <SupersededTokens connection={connection} tokens={lifecycle.supersededTokens} />
      ) : null}
      {admin && registration === 'registered' ? (
        <div className={styles.actions}>
          <MoveAgentControl connection={connection} />
        </div>
      ) : null}
    </section>
  );
}
