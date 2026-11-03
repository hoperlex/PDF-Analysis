/**
 * The groups, the rules, the cut-over proposal and the run readings the `EXEC2-WEB-GROUPS-01` tests
 * render. Written out, not derived from the contract, and Cyrillic wherever a screen prints the value.
 *
 * The connections come from `../workers/executor-fixtures`: `READY` and `TWIN` agree on the model, the
 * name on the gateway and the billing, so they can be members of one group; `OTHER_MODEL`, `OTHER_NAME`
 * and `SPARE` each disagree with them on exactly one of the three (SPARE on the billing), which is what
 * the member picker has to flag before the server refuses.
 */

import type {
  ExecutorGroup,
  ExecutorGroupCapacity,
  ExecutorGroupMember,
  ExecutorGroupRevision,
  ExecutorRoutingPreview,
  ExecutorRoutingPreviewItem,
  ExecutorRoutingRule,
  ExecutorRoutingRuleList,
  ExecutorWorkKind,
} from '@/shared/api';
import { EXECUTOR_WORK_KIND_VALUES } from '@/shared/api';
import {
  executorGroupCapacityKey,
  executorGroupsKey,
  executorRoutingRulesKey,
} from '@/entities/executor-group';

import type { newClient } from '../screens/harness';
import type { ExecutorCase } from '../workers/executor-fixtures';
import { ADMIN_UID, SPARE, READY, ago, executorCase, seedExecutors, ulid } from '../workers/executor-fixtures';

type Client = ReturnType<typeof newClient>;

export const groupId = (n: number): `exg_${string}` => `exg_${ulid(n)}`;
export const groupRevisionId = (n: number): `exgr_${string}` => `exgr_${ulid(n)}`;
export const ruleRevisionId = (n: number): `exrr_${string}` => `exrr_${ulid(n)}`;

const HOUR = 3_600_000;
const OK_PROBE = {
  outcome: 'ok', reported_model: 'шлюзовая-основная', identity_basis: 'reported', latency_ms: 700, rate_check: 'checked',
} as const;

export { READY, SPARE };

/** Agrees with `READY` on the pinned model, the name on the gateway and the billing. */
export const TWIN = executorCase({ n: 80, name: 'Парный шлюз', secrets: [{}], probe: OK_PROBE });

/** Pins another model than `READY`. */
export const OTHER_MODEL = executorCase({
  n: 81, name: 'Шлюз другой модели', secrets: [{}], probe: OK_PROBE, revision: { pin_id: 'модель-быстрая' },
});

/** Pins the same model and names it otherwise on the gateway. */
export const OTHER_NAME = executorCase({
  n: 82, name: 'Шлюз с другим именем модели', secrets: [{}], probe: OK_PROBE,
  revision: { gateway_model: 'иное-имя-на-шлюзе' },
});

/** An archived connection, which a revision cannot keep as a member. */
export const ARCHIVED = executorCase({ n: 83, name: 'Шлюз в архиве', secrets: [{}], probe: OK_PROBE, archived: true });

export const CONNECTION_CASES: readonly ExecutorCase[] = [READY, TWIN, OTHER_MODEL, OTHER_NAME, SPARE, ARCHIVED];

export function member(one: ExecutorCase): ExecutorGroupMember {
  return {
    connection_id: one.connection.connection_id,
    connection_revision_id: one.detail.revisions[0]!.revision_id,
  };
}

export function revisionOf(n: number, over: Partial<ExecutorGroupRevision> = {}): ExecutorGroupRevision {
  return {
    group_id: groupId(n),
    group_revision_id: groupRevisionId(n),
    revision_no: 1,
    created_at: ago(HOUR),
    created_by: ADMIN_UID,
    pin_id: 'модель-основная',
    gateway_model: 'шлюзовая-основная',
    billing: 'metered',
    input_per_mtok_usd: 3,
    output_per_mtok_usd: 15,
    strategy: 'least_loaded',
    members: [member(READY), member(TWIN)],
    ...over,
  };
}

export function groupOf(
  n: number,
  name: string,
  over: Partial<ExecutorGroup> = {},
  revision: Partial<ExecutorGroupRevision> = {},
): ExecutorGroup {
  return {
    group_id: groupId(n),
    display_name: name,
    created_at: ago(2 * HOUR),
    created_by: ADMIN_UID,
    routed_work_kinds: [],
    current_revision: revisionOf(n, revision),
    ...over,
  };
}

/** The group the tests mostly use: two compatible members. */
export const MAIN_GROUP = groupOf(1, 'Основная группа');

/** A group a rule names, so it cannot be archived. */
export const ROUTED_GROUP = groupOf(2, 'Группа правила', { routed_work_kinds: ['text_analysis'] }, { revision_no: 3 });

export const ARCHIVED_GROUP = groupOf(3, 'Прежняя группа', { archived_at: ago(HOUR) });

export function capacityOf(group: ExecutorGroup, over: Partial<ExecutorGroupCapacity> = {}): ExecutorGroupCapacity {
  return {
    group_id: group.group_id,
    group_revision_id: group.current_revision.group_revision_id,
    capacity: 4,
    used: 1,
    waiting: 2,
    members: [
      {
        connection_id: READY.connection.connection_id,
        snapshot_revision_id: READY.detail.revisions[0]!.revision_id,
        current_revision_id: READY.detail.revisions[0]!.revision_id,
        eligible: true,
        occupancy: { active_runs: 1, active_calls: 0, capacity: 2 },
      },
      {
        connection_id: TWIN.connection.connection_id,
        snapshot_revision_id: TWIN.detail.revisions[0]!.revision_id,
        current_revision_id: TWIN.detail.revisions[0]!.revision_id,
        eligible: false,
        ineligible_reason: 'runner_offline',
      },
    ],
    ...over,
  };
}

export function ruleOf(
  workKind: ExecutorWorkKind, group: ExecutorGroup, n: number,
): ExecutorRoutingRule {
  return {
    work_kind: workKind,
    group_id: group.group_id,
    group_revision_id: group.current_revision.group_revision_id,
    rule_revision_id: ruleRevisionId(n),
    set_at: ago(HOUR),
    set_by: ADMIN_UID,
  };
}

export function ruleList(
  mode: 'legacy' | 'rules', items: readonly ExecutorRoutingRule[] = [],
): ExecutorRoutingRuleList {
  return {
    items: [...items],
    routing_mode: mode === 'legacy' ? { mode } : { mode, changed_at: ago(HOUR), changed_by: ADMIN_UID },
  };
}

const READY_REVISION = READY.detail.revisions[0]!.revision_id;

/**
 * The proposal: `text_analysis` can become a group (its route has a standby, which is shown and not
 * converted), one route is incompatible, and the rest have no route.
 */
export const PREVIEW: ExecutorRoutingPreview = {
  preview_digest: 'b'.repeat(64),
  routing_mode: { mode: 'legacy' },
  items: EXECUTOR_WORK_KIND_VALUES.map((kind): ExecutorRoutingPreviewItem => {
    if (kind === 'text_analysis') {
      return {
        work_kind: kind,
        status: 'ready',
        primary_connection_id: READY.connection.connection_id,
        standby_connection_id: SPARE.connection.connection_id,
        connection_revision_id: READY_REVISION,
        pin_id: 'модель-основная',
        gateway_model: 'шлюзовая-основная',
        billing: 'metered',
        proposed_group_name: 'Анализ текста: Основной шлюз',
      };
    }
    if (kind === 'comparison_pair_check') {
      return {
        work_kind: kind,
        status: 'incompatible',
        incompatible_reason: 'connection_archived',
        primary_connection_id: ARCHIVED.connection.connection_id,
      };
    }
    return { work_kind: kind, status: 'no_route' };
  }),
};

/** Seed the connections and their settings, the groups, and the capacity of each group not archived. */
export function seedGroups(
  client: Client,
  groups: readonly ExecutorGroup[] = [MAIN_GROUP, ROUTED_GROUP],
  cases: readonly ExecutorCase[] = CONNECTION_CASES,
): void {
  seedExecutors(client, cases);
  client.setQueryData(executorGroupsKey(), { items: [...groups] });
  for (const group of groups) {
    if (group.archived_at === undefined) client.setQueryData(executorGroupCapacityKey(group.group_id), capacityOf(group));
  }
}

/** Seed the rules and the mode. */
export function seedRules(client: Client, mode: 'legacy' | 'rules', items: readonly ExecutorRoutingRule[] = []): void {
  client.setQueryData(executorRoutingRulesKey(), ruleList(mode, items));
}
