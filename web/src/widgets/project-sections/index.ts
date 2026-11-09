/** Public API of the `project-sections` widget. */

export type { ProjectSectionsProps, ProjectStructureViewProps } from './ui/project-sections';
export { ProjectSections, ProjectStructureView } from './ui/project-sections';

export type { ProjectStructure, SectionGroup } from './model/structure';
export { projectStructure } from './model/structure';

// `R-151c`, `R-151a`, `R-151e`, `UI-A-35`: the parts the section page shares with the project page.
export type { BatchSelection, CardSelection } from './model/use-batch-selection';
export { startable, useBatchSelection } from './model/use-batch-selection';
export type { BatchBarProps } from './ui/batch-bar';
export { BatchBar, selectionSlot } from './ui/batch-bar';
export type { ArchivedToggleProps, TagFilterProps } from './ui/document-filters';
export { ArchivedToggle, TagFilter } from './ui/document-filters';

// `UI-A-35`: the server's own figures per section, for the screens that would otherwise count a page.
export type { SectionFigures } from './model/section-figures';
export { UNCLASSIFIED_FIGURES, sectionFigures, totalFigures } from './model/section-figures';
export { useSectionFigures } from './api/use-section-figures';
