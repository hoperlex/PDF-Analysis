/** Public API of the `document-context` widget (`UI-A-22`). */

export type { ContextFacts, ContextLevel, ContextStep, DocumentContextProps } from './ui/document-context';
export { DocumentContext, contextSteps } from './ui/document-context';

// `UI-A-28`: «‹ Предыдущий · N из M · Следующий ›» between the documents of one section.
export type { SectionNeighboursProps, SectionNeighboursViewProps } from './ui/section-neighbours';
export {
  NEXT_DOCUMENT_LABEL,
  PREVIOUS_DOCUMENT_LABEL,
  SectionNeighbours,
  SectionNeighboursView,
} from './ui/section-neighbours';
