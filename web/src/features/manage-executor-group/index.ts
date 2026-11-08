/**
 * Public API of the `manage-executor-group` feature slice (`EXEC2-WEB-GROUPS-01`).
 *
 * The administrator's commands on groups, rules and the routing mode: create a group, add a revision
 * to it, archive it, point the rule of a work kind at a group revision, and move between the legacy
 * Primary/Standby routing and rules (the cut-over and its rollback). The server decides who may; the
 * controls are offered to an administrator only.
 */

export {
  useArchiveExecutorGroup,
  useCreateExecutorGroup,
  useReviseExecutorGroup,
  useSetExecutorRoutingMode,
  useSetExecutorRoutingRule,
} from './model/use-manage-executor-group';

export type { ArchiveGroupControlProps } from './ui/archive-group-control';
export { ArchiveGroupControl } from './ui/archive-group-control';
export type { CutOverPanelProps } from './ui/cut-over-panel';
export { CutOverPanel, CutOverPreviewTable } from './ui/cut-over-panel';
export { GroupCommandFailure } from './ui/group-command-failure';
export type { GroupFormProps } from './ui/group-form';
export { GroupForm } from './ui/group-form';
export type { RuleEditorProps } from './ui/rule-editor';
export { RuleEditor } from './ui/rule-editor';
