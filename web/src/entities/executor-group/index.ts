/**
 * Public API of the `executor-group` entity (`EXEC2-WEB-GROUPS-01`, ADR-0026 decisions 10, 11, 14
 * and 17): the reads of «Группы» and «Правила», the words, and the rules that decide which
 * connections can make a group and what a cut-over would do.
 *
 * Nothing here writes. The commands are in `features/manage-executor-group`, and the choice of a
 * group at run start is in `features/start-run`.
 */

export {
  executorGroupCapacityKey, executorGroupCapacityQueryOptions, executorGroupsKey, executorGroupsQueryOptions,
  executorRoutingPreviewKey, executorRoutingPreviewQueryOptions, executorRoutingRulesKey,
  executorRoutingRulesQueryOptions, useExecutorGroupCapacity, useExecutorGroups,
  useExecutorRoutingPreview, useExecutorRoutingRules,
} from './api/use-executor-groups';
export { groupCapacitySentence, memberOccupancySentence, memberStatusSentence } from './model/capacity';
export {
  CUT_OVER_CONFIRMATION, CUT_OVER_CONFIRM_LABEL, CUT_OVER_LABEL, MAPPING_CONFIRMATION_LABEL, NO_READY_ITEMS,
  ROLLBACK_CONFIRMATION, ROLLBACK_CONFIRM_LABEL, ROLLBACK_LABEL, cutOverCanBeConfirmed, cutOverMapping,
  previewItems, readyItems,
} from './model/cut-over';
export { groupFailure, groupRefusalSentence } from './model/failure';
export type { GroupDraft, GroupSettings, MemberCandidate, MemberProblem } from './model/member-candidates';
export {
  MEMBER_PROBLEM_SENTENCES, createGroupBody, draftFromRevision, groupDraftProblem, groupMembers,
  memberCandidates, memberProblem, memberRevisionIsStale, reviseGroupBody,
} from './model/member-candidates';
export type { RuleRow } from './model/rule-rows';
export { ruleRows, ruleTargets } from './model/rule-rows';
export {
  GROUP_BINDING_SENTENCE, GROUP_MEMBERS_MAX, GROUP_MEMBERS_MIN, GROUP_NAME_MAX_LENGTH, MEMBER_ISSUE_SENTENCES,
  PREVIEW_ISSUE_SENTENCES, PREVIEW_STATUS_LABELS, ROUTING_MODE_LABELS, STRATEGY_SENTENCE,
} from './model/vocabulary';
