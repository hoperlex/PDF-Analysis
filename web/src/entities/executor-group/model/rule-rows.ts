/**
 * The rows of «Правила»: exactly one per kind of model work (`EXEC2-WEB-GROUPS-01`, ADR-0026
 * decision 11).
 *
 * A rule points a work kind at an immutable group **revision**. The table is drawn from the
 * contract's own set of work kinds, so it has six rows whatever the server returned: a kind
 * without a rule is a row that says so, and an item for a kind this client does not know is not a
 * row. Rules are append-only: the list holds the current one of each kind.
 */

import type { ExecutorGroup, ExecutorRoutingRule, ExecutorWorkKind } from '@/shared/api';
import { EXECUTOR_WORK_KIND_VALUES } from '@/shared/api';

export interface RuleRow {
  readonly workKind: ExecutorWorkKind;
  /** The current rule of the kind, or `null` when it has none. */
  readonly rule: ExecutorRoutingRule | null;
  /** The group the rule names, when the list of groups holds it. */
  readonly group: ExecutorGroup | null;
  /**
   * True when the rule names the group's current revision. False means the group was revised after
   * the rule was set: new work still goes on the revision the rule names.
   */
  readonly onCurrentRevision: boolean;
}

export function ruleRows(
  rules: readonly ExecutorRoutingRule[],
  groups: readonly ExecutorGroup[],
): RuleRow[] {
  return EXECUTOR_WORK_KIND_VALUES.map((workKind) => {
    const rule = rules.find((item) => item.work_kind === workKind) ?? null;
    const group = rule === null ? null : (groups.find((item) => item.group_id === rule.group_id) ?? null);
    return {
      workKind,
      rule,
      group,
      onCurrentRevision: rule !== null && group !== null
        && group.current_revision.group_revision_id === rule.group_revision_id,
    };
  });
}

/** The groups a rule can name: not archived, and shown with the revision that is current now. */
export function ruleTargets(groups: readonly ExecutorGroup[]): ExecutorGroup[] {
  return groups.filter((group) => group.archived_at === undefined);
}
