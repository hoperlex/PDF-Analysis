'use client';

/**
 * One group on «Группы» (`EXEC2-WEB-GROUPS-01`, ADR-0026 decisions 10 and 14): its current
 * revision, the capacity derived from the database now, and — member by member — whether dispatch
 * would choose it now and, if not, why.
 *
 * The capacity is read for every group that is not archived and is stored nowhere. As on a
 * connection's card, no sentence says a place is «свободно»: a unit held by work whose remote
 * outcome is unresolved is counted as in use. A member that is not eligible is named with the first
 * applicable reason, in the contract's order; none is invented when the server gave none.
 *
 * An administrator is offered a new revision (`GroupForm`) and the archive (`ArchiveGroupControl`),
 * which refuses itself while a rule still names the group. Both are hidden for an archived group:
 * it takes no revision, rule or run, and the work already admitted on it finishes.
 */

import type { ExecutorConnection, ExecutorGroup, ExecutorPinnedModel } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { BILLING_LABELS, KIND_LABELS, WORK_KIND_LABELS } from '@/entities/executor-connection';
import type { MemberCandidate } from '@/entities/executor-group';
import {
  groupCapacitySentence,
  groupFailure,
  memberOccupancySentence,
  memberStatusSentence,
  useExecutorGroupCapacity,
} from '@/entities/executor-group';
import { ArchiveGroupControl, GroupForm } from '@/features/manage-executor-group';
import { LoadingState } from '@/shared/ui';

import styles from './executor-groups.module.css';

export interface GroupCardProps {
  readonly group: ExecutorGroup;
  readonly connections: readonly ExecutorConnection[];
  readonly candidates: readonly MemberCandidate[];
  readonly pinnedModels: readonly ExecutorPinnedModel[];
  /** An administrator: the controls are drawn. The server still checks every write. */
  readonly canManage: boolean;
}

function connectionName(connections: readonly ExecutorConnection[], id: string): string {
  return connections.find((item) => item.connection_id === id)?.display_name ?? 'подключение не найдено';
}

/** « (HTTP API)» after a member's name, or nothing when the connection is not in the list. */
function kindSentence(connections: readonly ExecutorConnection[], id: string): string {
  const kind = connections.find((item) => item.connection_id === id)?.kind;
  return kind === undefined ? '' : ` (${KIND_LABELS[kind]})`;
}

export function GroupCard({ group, connections, candidates, pinnedModels, canManage }: GroupCardProps) {
  const archived = group.archived_at !== undefined;
  const revision = group.current_revision;
  const capacity = useExecutorGroupCapacity(group.group_id, !archived);
  const statuses = new Map((capacity.data?.members ?? []).map((status) => [status.connection_id, status] as const));
  const total = capacity.data === undefined ? null : groupCapacitySentence(capacity.data);

  return (
    <li className={`am-state ${styles.card}`} data-group-state={archived ? 'archived' : 'active'}>
      <p className="am-state__title">
        <strong data-group-name>{group.display_name}</strong> · {archived ? 'в архиве' : 'действует'} · версия{' '}
        {revision.revision_no}
      </p>
      <div className={`am-state__detail ${styles.detail}`}>
        <p data-group-model>
          Модель «{revision.pin_id}», имя на шлюзе «{revision.gateway_model}». {BILLING_LABELS[revision.billing]}
          {revision.billing === 'metered'
            ? `: вход ${revision.input_per_mtok_usd}, выход ${revision.output_per_mtok_usd} долларов США за миллион токенов.`
            : '.'}
        </p>
        {group.routed_work_kinds.length === 0 ? null : (
          <p data-group-routed>
            Правила направляют на группу:{' '}
            {group.routed_work_kinds.map((kind) => `«${WORK_KIND_LABELS[kind]}»`).join(', ')}.
          </p>
        )}

        {archived ? null : capacity.isPending ? (
          <LoadingState what="занятость группы" />
        ) : capacity.isError ? (
          <p role="status" data-group-capacity-failure>
            Занятость группы не прочитана. {groupFailure(capacity.error, false).detail}
          </p>
        ) : total === null ? null : (
          <p data-group-capacity={capacity.data?.used}>{total}</p>
        )}

        <ul className={styles.members} aria-label={`Состав группы «${group.display_name}»`} data-group-members>
          {revision.members.map((member) => {
            const status = statuses.get(member.connection_id);
            const occupancy = status === undefined ? null : memberOccupancySentence(status);
            return (
              <li key={member.connection_id} className={styles.member} data-group-member={member.connection_id}>
                <strong>{connectionName(connections, member.connection_id)}</strong>
                {kindSentence(connections, member.connection_id)}
                {status === undefined ? null : (
                  <span data-group-member-eligible={status.eligible ? 'yes' : 'no'}>
                    {' '}— {memberStatusSentence(status)}
                    {occupancy === null ? '' : `. ${occupancy}`}
                  </span>
                )}
              </li>
            );
          })}
        </ul>

        <p className={`am-form__hint ${styles.created}`}>
          Создана <time dateTime={group.created_at}>{formatInstant(group.created_at)}</time>
          {archived && group.archived_at !== undefined
            ? <>, убрана в архив <time dateTime={group.archived_at}>{formatInstant(group.archived_at)}</time></>
            : <>, версия сохранена <time dateTime={revision.created_at}>{formatInstant(revision.created_at)}</time></>}
          , автор <code>{revision.created_by}</code>
        </p>

        {canManage && !archived ? (
          <div className={styles.actions}>
            <details data-group-revise className={styles.revise}>
              <summary>Новая версия</summary>
              <GroupForm group={group} candidates={candidates} pinnedModels={pinnedModels} />
            </details>
            <ArchiveGroupControl group={group} />
          </div>
        ) : null}
      </div>
    </li>
  );
}
