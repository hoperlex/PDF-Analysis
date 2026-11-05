/**
 * Public API of the `project-switcher` widget: the «Проекты ▾» selector of the frame's top
 * strip (`R-150b`). Importers use `@/widgets/project-switcher` and nothing deeper.
 */

export type { ProjectSwitcherViewProps } from './ui/project-switcher';
export { ProjectSwitcher, ProjectSwitcherLive, ProjectSwitcherView, switcherMenuProps } from './ui/project-switcher';

export type {
  SwitcherAddress,
  SwitcherEntry,
  SwitcherList,
  SwitcherModel,
  SwitcherNote,
} from './model/switcher';
export {
  ALL_PROJECTS_LABEL,
  GLOBAL_SCREEN_HINT,
  MORE_PROJECTS_LABEL,
  NEW_PROJECT_LABEL,
  NOT_RUN_LABEL,
  NO_EXPERT_DECISION_LABEL,
  RETRY_LABEL,
  SWITCHER_CAPTION,
  buildSwitcherModel,
  chooseProject,
  projectFigures,
  projectRowLabels,
  switcherContext,
  switcherListOf,
} from './model/switcher';
