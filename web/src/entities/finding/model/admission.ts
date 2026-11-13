/**
 * The admission gate: what this UI is willing to render as a finding.
 *
 * A Finding identity admits a meaningful issue for a human decision. Exact text/block
 * grounding and the explicit unverified variant are separate evidence states. Only the
 * latter may omit all evidence, with a nonempty limitation reason. Diagnostics without a
 * Finding identity remain outside the review ledger; malformed variants are reported as
 * integrity faults, rather than hidden as an empty result.
 */

import type { Finding, FindingDetail } from '@/shared/api';

import { groundedOnBlocks } from './block-grounding';
import { unverifiedReason } from './verification';

/** Why a payload was refused admission as a renderable finding. */
export type AdmissionRefusal =
  /** No `finding_uid`. Under §5.1 that is the signature of an ungrounded diagnostic. */
  | 'not_a_finding'
  /** The payload carried grounding-diagnostic fields. A diagnostic is never a finding. */
  | 'ungrounded_diagnostic'
  /**
   * Admitted as a finding but structurally impossible: it has neither a text span nor a portal block to stand on
   * (the P02 evidence gate forbids it).
   */
  | 'no_evidence';

export type FindingAdmission<T extends Finding | FindingDetail> =
  | { readonly kind: 'admitted'; readonly finding: T }
  | { readonly kind: 'refused'; readonly refusal: AdmissionRefusal };

/**
 * Fields that only ever exist on a grounding diagnostic. None is declared on `Finding` —
 * the contract schema is closed — so seeing one means something upstream handed us a row
 * from the diagnostic side of the grounding gate.
 */
const DIAGNOSTIC_FIELDS = ['grounded', 'ungrounded_reason'] as const;

function carriesDiagnosticFields(candidate: Finding | FindingDetail): boolean {
  const record = candidate as unknown as Record<string, unknown>;
  for (const field of DIAGNOSTIC_FIELDS) {
    const value = record[field];
    if (value === undefined) continue;
    // `grounded: true` is still a diagnostic-side field on a shape that must not carry
    // one; the presence of the key is the signal, not its value.
    return true;
  }
  return false;
}

/**
 * Decide whether one payload may be rendered as a finding.
 *
 * `no_evidence` is separated from the two ungrounded refusals on purpose. An item with no
 * `finding_uid` is simply not a finding and belongs in no list; a finding with an empty
 * evidence array passed the grounding gate and then arrived impossible, which is a
 * data-integrity fault worth showing an operator rather than hiding.
 *
 * `D-683` (contract 1.52.0): a finding of a `one_list` run grounded on a portal block has no text span, so its
 * observation's `evidence` is `[]` and its places are the finding's `block_evidence`. That finding is evidenced,
 * and is admitted: `grounding_kind = portal_block` with at least one block. Nothing else relaxes the rule -- a text
 * finding with no text span, and a block-grounded observation with no block, are still refused.
 */
export function admitFinding<T extends Finding | FindingDetail>(candidate: T): FindingAdmission<T> {
  if (carriesDiagnosticFields(candidate)) {
    return { kind: 'refused', refusal: 'ungrounded_diagnostic' };
  }

  const uid = candidate.finding_uid;
  if (typeof uid !== 'string' || uid.length === 0) {
    return { kind: 'refused', refusal: 'not_a_finding' };
  }

  // The explicit unverified variant is a reviewable Finding, never a claim of exact grounding.
  // A reason is required; merely dropping evidence cannot admit a legacy diagnostic.
  if (candidate.observation.grounding_kind === 'unverified') {
    return unverifiedReason({ observation: candidate.observation }) === null
      ? { kind: 'refused', refusal: 'no_evidence' }
      : { kind: 'admitted', finding: candidate };
  }

  if (candidate.observation.evidence.length === 0 && !groundedOnBlocks(candidate)) {
    return { kind: 'refused', refusal: 'no_evidence' };
  }

  return { kind: 'admitted', finding: candidate };
}

/** True when this payload may appear in a finding list. */
export function isRenderableFinding<T extends Finding | FindingDetail>(candidate: T): boolean {
  return admitFinding(candidate).kind === 'admitted';
}

/**
 * The findings of a page, split into the ones that render and the faults worth reporting.
 *
 * An ungrounded item is not reported: it is not a finding, and telling the reviewer that
 * the model produced something the grounding gate rejected is a run diagnostic
 * (`RunStatus.diagnostic_observation_count`), not a row on their review screen.
 */
export interface AdmittedFindings<T extends Finding | FindingDetail> {
  readonly findings: readonly T[];
  /** Findings that were admitted and then found structurally impossible. */
  readonly integrityFaults: readonly { readonly findingUid: string; readonly refusal: AdmissionRefusal }[];
  /** How many payloads were refused as not-a-finding. Never rendered as findings. */
  readonly refusedCount: number;
}

export function admitFindings<T extends Finding | FindingDetail>(
  candidates: readonly T[],
): AdmittedFindings<T> {
  const findings: T[] = [];
  const integrityFaults: { findingUid: string; refusal: AdmissionRefusal }[] = [];
  let refusedCount = 0;

  for (const candidate of candidates) {
    const verdict = admitFinding(candidate);
    if (verdict.kind === 'admitted') {
      findings.push(verdict.finding);
      continue;
    }
    refusedCount += 1;
    if (verdict.refusal === 'no_evidence') {
      integrityFaults.push({ findingUid: candidate.finding_uid, refusal: verdict.refusal });
    }
  }

  return { findings, integrityFaults, refusedCount };
}
