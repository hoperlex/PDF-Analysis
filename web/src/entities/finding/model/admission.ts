/**
 * The admission gate: what this UI is willing to render as a finding.
 *
 * `P02_SEAMS.md` §5.1 is the rule this enforces on the client side. `B4` publishes an
 * observation as a finding only when every evidence item resolves at its declared anchor.
 * An item that fails is **not a finding**: it is retained as a diagnostic row carrying
 * `grounded = false`, a non-null `ungrounded_reason` and **no** `finding_uid`, and it
 * appears in no finding query and in no CSV row.
 *
 * So the API never hands this UI an ungrounded item, and the point of this module is that
 * the UI has no display path for one anyway. A screen that renders whatever the array
 * contained would resurrect a rejected item the moment a server, a fixture or a future
 * endpoint leaked one. The gate is cheap and it is the difference between "the server
 * currently does not send it" and "this UI cannot show it".
 *
 * The gate is deliberately not a filter that silently drops things. A payload that fails
 * admission is classified, and the caller renders the classification — an ungrounded item
 * is dropped from the list because it is not a finding, while a structurally impossible
 * finding is surfaced as a data-integrity error rather than as an empty pane.
 */

import type { Finding, FindingDetail } from '@/shared/api';

/** Why a payload was refused admission as a renderable finding. */
export type AdmissionRefusal =
  /** No `finding_uid`. Under §5.1 that is the signature of an ungrounded diagnostic. */
  | 'not_a_finding'
  /** The payload carried grounding-diagnostic fields. A diagnostic is never a finding. */
  | 'ungrounded_diagnostic'
  /** Admitted as a finding but structurally impossible: the P02 evidence gate forbids it. */
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
 */
export function admitFinding<T extends Finding | FindingDetail>(candidate: T): FindingAdmission<T> {
  if (carriesDiagnosticFields(candidate)) {
    return { kind: 'refused', refusal: 'ungrounded_diagnostic' };
  }

  const uid = candidate.finding_uid;
  if (typeof uid !== 'string' || uid.length === 0) {
    return { kind: 'refused', refusal: 'not_a_finding' };
  }

  if (candidate.observation.evidence.length === 0) {
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
