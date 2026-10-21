/**
 * What an accept or a reject is allowed to send.
 *
 * `AppendDecisionRequest.severity` is the expert's decided severity, and the ledger is strict
 * about it (`W56A-INT-DECIDED-SEVERITY-01`): it accepts a severity on an `accept` only, and
 * for the optional v2 path it requires the observation to carry a proposed severity. This
 * file is where the browser keeps the same two rules so that a request the ledger would
 * refuse is not sent, and a request the ledger needs is not sent half-built.
 *
 *   - A finding WITHOUT a proposed severity sends no `severity`, whatever the caller passes:
 *     the legacy request stays byte-for-byte what it always was.
 *   - A finding WITH a proposed severity cannot be accepted without a decided one. The
 *     proposal is the model's; the expert's choice is a separate act and is never copied
 *     from it, so an accept with no choice is REFUSED here, in words, not defaulted.
 *   - A reject never sends a severity. The ledger's fold clears the decided severity on a
 *     reject, so a value on it could only be refused or ignored.
 *
 * Pure: no React, no request. The hook calls it; a test calls it the same way.
 */

import type {
  AppendDecisionRequest,
  FindingObservationId,
  Severity,
} from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';

export type VerdictIntent = 'accept' | 'reject';

/**
 * Every reason this tier refuses to send a verdict, as a value.
 *
 * An array so a test can render the screen for EVERY member (`D-84`'s repair, as for
 * `COMMENT_REFUSALS`), and a union so a new member is a compile error until it has words.
 */
export const VERDICT_REFUSALS = ['severity_required'] as const;

export type VerdictRefusal = (typeof VERDICT_REFUSALS)[number];

/**
 * The sentence a reviewer reads. No `default` on purpose: a new member must not compile
 * until it has words of its own, and the widget renders on PRESENCE of a refusal.
 */
export function verdictRefusalMessage(refusal: VerdictRefusal): string {
  switch (refusal) {
    case 'severity_required':
      return 'Перед принятием выберите важность. Ничего не отправлено.';
  }
}

export interface VerdictRequestInput {
  readonly intent: VerdictIntent;
  readonly observationId: FindingObservationId;
  /** The model's proposal on the observation being judged; absent on a legacy finding. */
  readonly proposedSeverity?: Severity | undefined;
  /** What the expert chose, or nothing if they have not chosen. */
  readonly decidedSeverity?: Severity | undefined;
}

export type VerdictRequestCheck =
  | { readonly kind: 'ok'; readonly request: AppendDecisionRequest }
  | { readonly kind: 'refused'; readonly refusal: VerdictRefusal };

export function buildVerdictRequest(input: VerdictRequestInput): VerdictRequestCheck {
  const request: AppendDecisionRequest = {
    event_type: input.intent,
    finding_observation_id: input.observationId,
  };

  if (input.intent === 'reject' || input.proposedSeverity === undefined) {
    return { kind: 'ok', request };
  }

  const decided = input.decidedSeverity;
  if (decided === undefined || !(SEVERITY_VALUES as readonly unknown[]).includes(decided)) {
    return { kind: 'refused', refusal: 'severity_required' };
  }
  return { kind: 'ok', request: { ...request, severity: decided } };
}
