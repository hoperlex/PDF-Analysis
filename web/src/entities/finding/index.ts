/**
 * Public API of the `finding` entity.
 *
 * What a finding is allowed to be on screen, and how a page of them is ordered. No
 * fetching: an entity holds the model, a feature holds the request.
 */

export type { AdmissionRefusal, AdmittedFindings, FindingAdmission } from './model/admission';
export { admitFinding, admitFindings, isRenderableFinding } from './model/admission';

export type { FindingGroup } from './model/grouping';
export { countGrouped, groupByCategory } from './model/grouping';

/** The Russian label of each AR v2 severity; no expert choice is implied. */
export { SEVERITY_LABELS } from './model/severity-labels';

/** The Russian words for the state of one norm citation of a finding. */
export {
  NORM_CITATION_STATE_LABELS,
  NORM_CITATION_STATE_MEANINGS,
  normCitationStateLabel,
  normCitationStateMeaning,
} from './model/citation-labels';

export type { SeverityBadgeProps } from './ui/severity-badge';
export { SeverityBadge } from './ui/severity-badge';
