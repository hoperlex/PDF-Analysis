/**
 * Public API of the `project` entity. Importers use `@/entities/project` and nothing
 * deeper; the file layout below is this slice's own business.
 */

export type { ProjectNameProblem } from './model/project';
export {
  PROJECT_NAME_MAX_LENGTH,
  PROJECT_NAME_MIN_LENGTH,
  UNKNOWN_COUNT_LABEL,
  looksLikeProjectUid,
  projectDocumentCount,
  projectDocumentCountLabel,
  projectNameProblemMessage,
  validateProjectName,
} from './model/project';

export type { CreateProjectFailure, CreateProjectFailureKind } from './model/create-failure';
export { classifyCreateProjectFailure } from './model/create-failure';

export type { ProjectListFailure, ProjectListFailureKind } from './model/list-failure';
export { classifyProjectListFailure } from './model/list-failure';

export { PROJECT_PAGE_LIMIT, useProjectList } from './api/use-project-list';

export type { ProjectRowProps } from './ui/project-row';
export { ProjectRow } from './ui/project-row';
