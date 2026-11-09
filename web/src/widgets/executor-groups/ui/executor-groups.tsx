'use client';

/**
 * «Группы» (`EXEC2-WEB-GROUPS-01`, ADR-0026 decisions 10, 14 and 19): the homogeneous groups of
 * interchangeable executors that rules and run starts can name, with their capacity and the
 * eligibility of each member.
 *
 * Any role reads the list (`listExecutorGroups` is open to every role); only an administrator is
 * shown the controls, and the server checks every write. A group is **homogeneous**: every member
 * pins the same model, names it the same on the gateway and shares the billing, so a group can
 * stand in for any of its connections. A change is a new revision of the group; work already
 * admitted on an earlier revision finishes on it.
 *
 * **The `R-149a` notice is drawn for every role and whether or not the list is empty.** The stand
 * does not check whether a connection may receive client documents (`D-291`), so groups, like
 * capacity above one, are for test data. It qualifies what the list lets an administrator set.
 *
 * The groups an archive retired are listed apart, and an archived group is never offered for a rule
 * or a start. The connections are read here only to name members and to offer the picker; their
 * settings are read for the live ones, because a member is a connection **and the revision of it**.
 */

import type { Role } from '@/shared/api';
import { canExecute, executionFailure } from '@/entities/execution';
import {
  CLIENT_DOCUMENTS_NOTICE,
  useExecutorConnectionDetails,
  useExecutorConnections,
} from '@/entities/executor-connection';
import {
  GROUP_BINDING_SENTENCE,
  STRATEGY_SENTENCE,
  groupFailure,
  memberCandidates,
  useExecutorGroups,
} from '@/entities/executor-group';
import { GroupForm } from '@/features/manage-executor-group';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import { GroupCard } from './group-card';
import styles from './executor-groups.module.css';

export interface ExecutorGroupsProps {
  readonly roles: readonly Role[];
}

export function ExecutorGroups({ roles }: ExecutorGroupsProps) {
  const groups = useExecutorGroups();
  const list = useExecutorConnections();
  const connections = list.data?.items ?? [];
  const settings = useExecutorConnectionDetails(
    connections.filter((item) => item.archived_at === undefined).map((item) => item.connection_id),
  );
  const canManage = canExecute(roles, 'connections');

  if (groups.isPending) return <LoadingState what="группы" />;
  if (groups.isError) {
    const failure = groupFailure(groups.error, false);
    return (
      <div data-executor-groups-read-failure={failure.kind}>
        <ErrorState
          title="Группы не прочитаны"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={() => void groups.refetch()}
        />
      </div>
    );
  }

  const candidates = memberCandidates(connections, settings.details);
  const pinnedModels = list.data?.pinned_models ?? [];
  const active = groups.data.items.filter((group) => group.archived_at === undefined);
  const archived = groups.data.items.filter((group) => group.archived_at !== undefined);
  // The connection list is what names the members; when it cannot be read the groups are still shown.
  const connectionsFailure = list.isError ? executionFailure(list.error, false) : null;
  // Until the connections are read the picker would offer nothing, and say so wrongly: no controls yet.
  const controls = canManage && connectionsFailure === null && !list.isPending;

  return (
    <div className={styles.panel} data-executor-groups>
      <p className="am-note" data-executor-groups-notice="client-documents">{CLIENT_DOCUMENTS_NOTICE}</p>
      <details className={styles.about} data-executor-groups-notice="binding">
        <summary>Как работа попадает в группу</summary>
        <p className="am-note">{GROUP_BINDING_SENTENCE} {STRATEGY_SENTENCE}</p>
      </details>
      {connectionsFailure === null ? null : (
        <p className="am-note" role="status" data-executor-groups-connections-failure>
          Подключения не прочитаны, поэтому состав групп назван неполно, а форма группы недоступна. {connectionsFailure.detail}
        </p>
      )}

      {active.length === 0 ? (
        <EmptyState
          title="Групп нет"
          detail={canManage
            ? 'Создайте первую группу ниже: модель и подключения, которые её обслуживают.'
            : 'Администратор ещё не создал ни одной группы.'}
        />
      ) : (
        <ol aria-label="Группы" className={styles.list} data-executor-group-list>
          {active.map((group) => (
            <GroupCard
              key={group.group_id}
              group={group}
              connections={connections}
              candidates={candidates}
              pinnedModels={pinnedModels}
              canManage={controls}
            />
          ))}
        </ol>
      )}

      {archived.length === 0 ? null : (
        <details data-executor-group-archive>
          <summary>Архив групп ({archived.length})</summary>
          <ol aria-label="Группы в архиве" className={styles.list}>
            {archived.map((group) => (
              <GroupCard
                key={group.group_id}
                group={group}
                connections={connections}
                candidates={candidates}
                pinnedModels={pinnedModels}
                canManage={false}
              />
            ))}
          </ol>
        </details>
      )}

      {controls ? (
        <details className="am-section" open={active.length === 0} data-executor-group-create>
          <summary>Создать группу</summary>
          <GroupForm candidates={candidates} pinnedModels={pinnedModels} />
        </details>
      ) : null}
      {canManage && list.isPending ? <LoadingState what="подключения" /> : null}
    </div>
  );
}
