/**
 * Public API of the `finding` entity.
 *
 * What a finding is allowed to be on screen, and how a page of them is ordered. Writes
 * belong to the features; the one read here is the complete list of a run's findings, which
 * fills `queryKeys.runs.findings` and has no other home (`api/run-findings-query.ts`).
 */

export type { AdmissionRefusal, AdmittedFindings, FindingAdmission } from './model/admission';
export { admitFinding, admitFindings, isRenderableFinding } from './model/admission';

/**
 * `D-683`, `CRIT-SEAL-50`: a finding that stands on portal blocks rather than text spans, and where a finding comes from
 * (the «Источник» chip). A finding with none of the new members is a text finding.
 */
export { blockEvidenceOf, groundedOnBlocks, standsOnBlocksOnly } from './model/block-grounding';
export { FINDING_ORIGIN_LABELS, findingOriginOf, runHasNonTextFindings } from './model/origin';
export type { OriginChipProps } from './ui/origin-chip';
export { OriginChip } from './ui/origin-chip';

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

export type { CompleteRunFindings } from './api/run-findings-query';
export {
  RUN_FINDINGS_MAX_PAGES,
  RUN_FINDINGS_PAGE_LIMIT,
  RunFindingsReadFault,
  readAllRunFindings,
  runFindingsQueryOptions,
} from './api/run-findings-query';

// `R-151g`: the designer's execution status of an accepted finding.
export { EXECUTION_STATUS_LABELS, EXECUTION_STATUS_ORDER } from './model/execution-status';
