/**
 * The severity the expert has picked in the decision panel, kept with the observation it was
 * picked for.
 *
 * The panel instance survives a change of selected finding (the page renders it at the same
 * place for every finding), so a bare `useState<Severity>` would carry finding A's choice
 * onto finding B's accept — a severity the expert never chose for B, recorded under their
 * name. The draft therefore names its observation, and `chosenSeverity` returns nothing for
 * any other one.
 *
 * The model's proposal is deliberately NOT the initial value: the expert's decided severity
 * is an act of its own, and a proposal copied into it would make the model's output the
 * expert's decision (`AGENTS.md` §4).
 */

import type { FindingObservationId, Severity } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';

export interface SeverityDraft {
  readonly observationId: FindingObservationId;
  readonly severity: Severity;
}

/** The choice that belongs to this observation, or nothing. */
export function chosenSeverity(
  draft: SeverityDraft | null,
  observationId: FindingObservationId,
): Severity | undefined {
  return draft !== null && draft.observationId === observationId ? draft.severity : undefined;
}

/**
 * What a `<select>` value means: one of the closed severities, or no choice. The empty
 * option and any value outside the contract's set read as «not chosen», which the feature
 * then refuses to send on an accept — never as a default.
 */
export function draftFromControl(
  value: string,
  observationId: FindingObservationId,
): SeverityDraft | null {
  const severity = (SEVERITY_VALUES as readonly string[]).find((candidate) => candidate === value);
  return severity === undefined
    ? null
    : { observationId, severity: severity as Severity };
}
