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
