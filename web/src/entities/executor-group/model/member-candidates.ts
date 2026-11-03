/**
 * The members a group can be made of, and the check of a draft before the server refuses it
 * (`EXEC2-WEB-GROUPS-01`, ADR-0026 decision 10).
 *
 * **A group is homogeneous.** Every member names a connection and the **revision** of it the
 * group snapshots; that revision must pin exactly the group's `pin_id` and `gateway_model`, be of a
 * served kind, and share the group's `billing`. The server refuses a mix with a typed
 * `validation_failed` (`member_pin_mismatch`, `member_model_mismatch`, `member_billing_mismatch`,
 * `member_kind_not_served`) or a `conflict` (`connection_archived`). This module states the same
 * rule over what the screen has already read, so the form can flag a mismatch beside the member and
 * keep the button disabled, instead of sending a request it knows will be refused. The server still
 * decides: the check is a courtesy, not an authority.
 *
 * The picker offers each connection with its **current** revision, because that is the revision
 * the server snapshots from the screen's point of view. Readiness (a finished `ok` probe on the
 * current key) is shown beside a member and does not block it: a group may be saved ahead of the
 * probe that makes a member eligible, and the group's capacity view says who would be chosen now.
 */

import type {
  CreateExecutorGroupRequest,
  ExecutorBilling,
  ExecutorConnection,
  ExecutorConnectionDetail,
  ExecutorConnectionId,
  ExecutorGroupMember,
  ExecutorGroupRevision,
  ExecutorKind,
  ExecutorRevisionId,
  ReviseExecutorGroupRequest,
} from '@/shared/api';
import {
  ROUTE_BLOCKER_SENTENCES,
  currentRevision,
  kindIsServed,
  routeBlocker,
} from '@/entities/executor-connection';

import { GROUP_MEMBERS_MAX, GROUP_MEMBERS_MIN, GROUP_NAME_MAX_LENGTH } from './vocabulary';

export interface MemberCandidate {
  readonly connectionId: ExecutorConnectionId;
  readonly name: string;
  readonly kind: ExecutorKind;
  readonly archived: boolean;
  /** The connection's current revision, or `null` when it has no settings yet or they were not read. */
  readonly revisionId: ExecutorRevisionId | null;
  readonly revisionNo: number | null;
  readonly pinId: string | null;
  readonly gatewayModel: string | null;
  readonly billing: ExecutorBilling | null;
  /** The capacity of the current revision: one when it says none (a revision from before capacity). */
  readonly capacity: number;
  /** Why the connection cannot serve now, in words, or `null` when it can. Informs; never blocks. */
  readonly readiness: string | null;
}

/**
 * Every connection as a candidate, in the order the list came in. `details` holds the connections
 * whose settings were read; one that was not has no revision to offer yet.
 */
export function memberCandidates(
  connections: readonly ExecutorConnection[],
  details: ReadonlyMap<string, ExecutorConnectionDetail>,
): MemberCandidate[] {
  return connections.map((connection) => {
    const detail = details.get(connection.connection_id);
    const revision = detail === undefined ? undefined : currentRevision(connection, detail.revisions);
    const blocker = detail === undefined ? null : routeBlocker(connection, revision);
    return {
      connectionId: connection.connection_id,
      name: connection.display_name,
      kind: connection.kind,
      archived: connection.archived_at !== undefined,
      revisionId: revision?.revision_id ?? null,
      revisionNo: revision?.revision_no ?? null,
      pinId: revision?.pin_id ?? null,
      gatewayModel: revision?.gateway_model ?? null,
      billing: revision?.billing ?? null,
      capacity: revision?.max_active_runs ?? 1,
      readiness: detail === undefined ? 'настройки подключения не прочитаны'
        : blocker === null ? null : ROUTE_BLOCKER_SENTENCES[blocker],
    };
  });
}

/** The fields every member must share: what a draft says the group is. */
export interface GroupSettings {
  readonly pinId: string;
  readonly gatewayModel: string;
  /** `''` until chosen. */
  readonly billing: ExecutorBilling | '';
}

export type MemberProblem =
  | 'archived'
  | 'no_revision'
  | 'kind_not_served'
  | 'pin_mismatch'
  | 'model_mismatch'
  | 'billing_mismatch';

export const MEMBER_PROBLEM_SENTENCES: Readonly<Record<MemberProblem, string>> = {
  archived: 'подключение в архиве',
  no_revision: 'настройки подключения не заданы или ещё не прочитаны',
  kind_not_served: 'этот вид подключения пока не обслуживается',
  pin_mismatch: 'у подключения закреплена другая модель, чем у группы',
  model_mismatch: 'у подключения другое имя модели на шлюзе, чем у группы',
  billing_mismatch: 'у подключения другая тарификация, чем у группы',
};

/**
 * What stands against this candidate being a member of a group with these settings, or `null`.
 * A setting not yet filled in judges nothing: the form says it is missing, not that a member
 * disagrees with it.
 */
export function memberProblem(candidate: MemberCandidate, settings: GroupSettings): MemberProblem | null {
  if (candidate.archived) return 'archived';
  if (candidate.revisionId === null) return 'no_revision';
  if (!kindIsServed(candidate.kind)) return 'kind_not_served';
  if (settings.pinId !== '' && candidate.pinId !== settings.pinId) return 'pin_mismatch';
  const model = settings.gatewayModel.trim();
  if (model !== '' && candidate.gatewayModel !== model) return 'model_mismatch';
  if (settings.billing !== '' && candidate.billing !== settings.billing) return 'billing_mismatch';
  return null;
}

export interface GroupDraft {
  /** The name of a new group; ignored when a group is revised (a revision does not rename it). */
  readonly name: string;
  readonly settings: GroupSettings;
  readonly memberIds: readonly ExecutorConnectionId[];
}

/**
 * The first reason a draft cannot be sent, in words, or `null` when it can. The order is the
 * order of the form: the name, the three shared fields, then the size of the group, then each
 * selected member against the settings.
 */
export function groupDraftProblem(
  draft: GroupDraft,
  candidates: readonly MemberCandidate[],
  needsName: boolean,
): string | null {
  const name = draft.name.trim();
  if (needsName && name === '') return 'Укажите название группы.';
  if (needsName && name.length > GROUP_NAME_MAX_LENGTH) {
    return `Название группы не длиннее ${GROUP_NAME_MAX_LENGTH} знаков.`;
  }
  if (draft.settings.pinId === '') return 'Выберите модель группы.';
  if (draft.settings.gatewayModel.trim() === '') return 'Укажите имя модели на шлюзе.';
  if (draft.settings.billing === '') return 'Выберите тарификацию группы.';
  if (draft.memberIds.length < GROUP_MEMBERS_MIN || draft.memberIds.length > GROUP_MEMBERS_MAX) {
    return `В группе должно быть от ${GROUP_MEMBERS_MIN} до ${GROUP_MEMBERS_MAX} подключений.`;
  }
  for (const id of draft.memberIds) {
    const candidate = candidates.find((one) => one.connectionId === id);
    if (candidate === undefined) return 'Выбранного подключения нет в списке. Обновите страницу.';
    const problem = memberProblem(candidate, draft.settings);
    if (problem !== null) return `Подключение «${candidate.name}»: ${MEMBER_PROBLEM_SENTENCES[problem]}.`;
  }
  return null;
}

/**
 * The members of a request: each selected connection with the revision the picker showed. A member
 * the group already holds keeps its `tie_break_order`; a new one has none, and the server orders it.
 * Only valid once `groupDraftProblem` is `null`, so every selected candidate has a revision.
 */
export function groupMembers(
  draft: GroupDraft,
  candidates: readonly MemberCandidate[],
  previous: readonly ExecutorGroupMember[] = [],
): ExecutorGroupMember[] {
  const members: ExecutorGroupMember[] = [];
  for (const id of draft.memberIds) {
    const candidate = candidates.find((one) => one.connectionId === id);
    if (candidate === undefined || candidate.revisionId === null) continue;
    const order = previous.find((one) => one.connection_id === id)?.tie_break_order;
    members.push({
      connection_id: id,
      connection_revision_id: candidate.revisionId,
      ...(order === undefined ? {} : { tie_break_order: order }),
    });
  }
  return members;
}

/**
 * The request that makes a new group of a valid draft, or `null` when a shared field is still
 * unchosen: nothing is guessed in its place.
 */
export function createGroupBody(
  draft: GroupDraft,
  candidates: readonly MemberCandidate[],
): CreateExecutorGroupRequest | null {
  if (draft.settings.billing === '') return null;
  return {
    display_name: draft.name.trim(),
    pin_id: draft.settings.pinId,
    gateway_model: draft.settings.gatewayModel.trim(),
    billing: draft.settings.billing,
    members: groupMembers(draft, candidates),
  };
}

/** The request that adds a revision to a group (the full settings, never a patch), or `null` likewise. */
export function reviseGroupBody(
  draft: GroupDraft,
  candidates: readonly MemberCandidate[],
  previous: readonly ExecutorGroupMember[],
): ReviseExecutorGroupRequest | null {
  if (draft.settings.billing === '') return null;
  return {
    pin_id: draft.settings.pinId,
    gateway_model: draft.settings.gatewayModel.trim(),
    billing: draft.settings.billing,
    members: groupMembers(draft, candidates, previous),
  };
}

/** The draft a revision starts from: the settings and the members of the group's current revision. */
export function draftFromRevision(name: string, revision: ExecutorGroupRevision): GroupDraft {
  return {
    name,
    settings: { pinId: revision.pin_id, gatewayModel: revision.gateway_model, billing: revision.billing },
    memberIds: revision.members.map((member) => member.connection_id),
  };
}

/** True when a member of the group's current revision holds an earlier revision of its connection. */
export function memberRevisionIsStale(
  member: ExecutorGroupMember,
  candidates: readonly MemberCandidate[],
): boolean {
  const candidate = candidates.find((one) => one.connectionId === member.connection_id);
  return candidate !== undefined && candidate.revisionId !== null && candidate.revisionId !== member.connection_revision_id;
}
