/** Public API of the `document-context` widget (`UI-A-22`). */

export type { ContextFacts, ContextLevel, ContextStep, DocumentContextProps } from './ui/document-context';
export { DocumentContext, contextSteps } from './ui/document-context';

// `UIP-G-09`: the version bar under the tabs, and the PDF window a page hands the frame.
export type { PdfDrawerProps, PdfSlot, VersionBarProps } from './ui/version-bar';
export { ALL_VERSIONS_LABEL, PDF_BUTTON_HINT, PDF_BUTTON_LABEL, PDF_OPEN_PARAM, VersionBar } from './ui/version-bar';

// `UI-A-28`: «‹ Предыдущий · N из M · Следующий ›» between the documents of one section.
export type { SectionNeighboursProps, SectionNeighboursViewProps } from './ui/section-neighbours';
export {
  NEXT_DOCUMENT_LABEL,
  PREVIOUS_DOCUMENT_LABEL,
  SectionNeighbours,
  SectionNeighboursView,
} from './ui/section-neighbours';

// `UI-A-22`, `R-151m`, `UIP-G-09`: the version's tabs, «Инфо · Блоки · Лог · Разбор · Оптимизация», and where another
// version or neighbour opens on the same tab.
export type {
  OptimisationCount, TabLevel, VersionFigures, VersionTab, VersionTabFacts, VersionTabKey,
} from './model/version-tabs';
export {
  latestResultRun, mayReadLogOf, optimisationOf, runLogAddress, versionFigures, versionTabs,
} from './model/version-tabs';
export type { TabTarget } from './model/tab-address';
export { levelAddress, levelNeedsRuns, targetOfAudit, targetOfRuns, versionChoiceLevel } from './model/tab-address';
export type { VersionTabsViewProps } from './ui/version-tabs';
export { VersionTabs, VersionTabsView } from './ui/version-tabs';
