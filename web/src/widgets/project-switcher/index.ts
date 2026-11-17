/**
 * Public API of the `project-switcher` widget: the object selector of the frame's top
 * strip (`R-150b`). Importers use `@/widgets/project-switcher` and nothing deeper.
 */

export type { ProjectSwitcherViewProps } from './ui/project-switcher';
export { ProjectSwitcher, ProjectSwitcherLive, ProjectSwitcherView, switcherMenuProps } from './ui/project-switcher';
export type { ObjectMenuItem, ObjectMenuProps, ObjectMenuViewProps } from './ui/object-menu';
export { ObjectMenu, ObjectMenuView } from './ui/object-menu';

export type { NewObjectDialogProps } from './ui/new-object-dialog';
export { NEW_OBJECT_CANCEL_LABEL, NEW_OBJECT_CREATE_LABEL, NewObjectDialog } from './ui/new-object-dialog';

export type {
  CreatedObjectEffects,
  RowFigure,
  SwitcherAddress,
  SwitcherEntry,
  SwitcherList,
  SwitcherModel,
  SwitcherNote,
  SwitcherOptions,
} from './model/switcher';
export {
  ALL_PROJECTS_LABEL,
  GLOBAL_SCREEN_HINT,
  MORE_PROJECTS_LABEL,
  NEW_PROJECT_LABEL,
  NOT_RUN_LABEL,
  NO_EXPERT_DECISION_LABEL,
  RETRY_LABEL,
  SWITCHER_LABEL,
  afterObjectCreated,
  buildSwitcherModel,
  chooseProject,
  chosenProject,
  projectBadges,
  projectFigures,
  projectRowLabels,
  switcherContext,
  switcherListOf,
} from './model/switcher';
