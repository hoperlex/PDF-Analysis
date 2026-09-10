/**
 * Contract-shaped fixtures for the `B8` unit suites.
 *
 * Built by hand against the generated types rather than captured from a running backend:
 * the backend is being written in parallel and its endpoints may not answer yet, and a
 * fixture that only matches today's server is not a test of the contract. Every builder
 * returns a value that type-checks as the generated model, so a contract change that
 * removes or renames a field takes these red at `tsc` time rather than at runtime.
 *
 * Identifiers follow the contract's patterns (`fnd_`, `fobs_`, `dec_`, `ver_`, `run_`,
 * `proj_` plus a 26-character Crockford ULID body). Nothing in the UI parses one, but a
 * fixture that ignored the shape would hide a bug in anything that ever does.
 *
 * This file lives under `tests/unit/review/` because that is a tree `B8` owns; the
 * decisions and export suites import it from here rather than duplicating the builders or
 * creating a shared fixture directory outside any session's ownership.
 */

import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import type { ReactElement } from 'react';

import type {
  DecisionEvent,
  DecisionEventType,
  Evidence,
  Finding,
  FindingCategory,
  FindingDetail,
  FindingObservation,
  ObservationProvenance,
  ProviderMode,
  RunState,
  RunStatus,
  Verdict,
} from '@/shared/api';

/**
 * Make `React` reachable as a free variable before any component module is evaluated.
 *
 * `web/tsconfig.json` sets `jsx: "preserve"`, which is right for Next — its own compiler
 * handles JSX with the automatic runtime. Vitest transforms the same files with esbuild,
 * and esbuild reads that setting as "classic runtime", emitting `React.createElement(...)`
 * against a `React` that no module imports. `B8`'s own components carry a
 * `@jsxRuntime automatic` pragma and are unaffected, but `src/shared/ui/**` is `A5`'s and
 * frozen, so every component that renders a `LoadingState`, `EmptyState`, `ErrorState` or a
 * badge would fail with `ReferenceError: React is not defined`.
 *
 * The classic transform emits a *free* `React` reference, so a global satisfies it. This is
 * a shim in a `B8`-owned test file rather than an edit to a frozen one.
 *
 * The real fix belongs to `A5` — one line in `web/vitest.config.ts`,
 * `esbuild: { jsx: 'automatic' }` — and is reported as a seam defect, not repaired here.
 */
(globalThis as unknown as { React?: typeof React }).React = React;

/** Render a component to markup. No DOM, no `jsdom`, no testing-library — none is a dependency. */
export function render(element: ReactElement): string {
  return renderToStaticMarkup(element);
}

const ULID_A = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const ULID_B = '01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const ULID_C = '01J9ZQ8K7NHVXW3T2R5M6P4Q8D';

export const PROJECT_UID = `proj_${ULID_A}`;
export const VERSION_UID = `ver_${ULID_A}`;
export const DOCUMENT_UID = `doc_${ULID_A}`;
export const RUN_ID = `run_${ULID_A}`;
export const FINDING_UID = `fnd_${ULID_A}`;
export const OBSERVATION_ID = `fobs_${ULID_A}`;

export function decisionId(suffix: string): string {
  return `dec_${ULID_A.slice(0, 25)}${suffix}`;
}

export function provenance(overrides: Partial<ObservationProvenance> = {}): ObservationProvenance {
  return {
    analysis_profile_id: `ap_${ULID_A}`,
    prompt_bundle_id: `pb_${ULID_A}`,
    stage_id: 'analysis',
    provider_mode: 'recorded',
    model_call_id: `mc_${ULID_A}`,
    model_identity: 'recorded-fixture',
    ...overrides,
  } as ObservationProvenance;
}

/**
 * One evidence item. `char_end` is derived from the quotation's own code-point length, so
 * a fixture cannot accidentally declare an anchor that disagrees with its own string —
 * `span_length_mismatch` is a grounding refusal, so a published finding never carries one.
 */
export function evidence(overrides: Partial<Evidence> = {}): Evidence {
  const quote = overrides.quote ?? 'Срок поставки составляет 30 дней.';
  const charStart = overrides.char_start ?? 1200;
  return {
    evidence_ordinal: 1,
    page_number: 7,
    quote,
    char_start: charStart,
    char_end: charStart + [...quote].length,
    block_id: 'blk_0042',
    ...overrides,
    // `quote` and `char_end` are recomputed after the spread so an override of `quote`
    // alone still produces a consistent anchor.
    ...(overrides.char_end === undefined ? { char_end: charStart + [...quote].length } : {}),
  };
}

export function observation(overrides: Partial<FindingObservation> = {}): FindingObservation {
  return {
    finding_observation_id: OBSERVATION_ID,
    run_id: RUN_ID,
    category: 'internal_contradiction' as FindingCategory,
    finding_text: 'Delivery term stated as 30 days in §4 and 45 days in §9.',
    recommendation_text: 'Reconcile the two delivery terms before signature.',
    evidence: [evidence()],
    provenance: provenance(),
    ...overrides,
  };
}

export function finding(overrides: Partial<Finding> = {}): Finding {
  return {
    finding_uid: FINDING_UID,
    project_uid: PROJECT_UID,
    version_uid: VERSION_UID,
    run_id: RUN_ID,
    category: 'internal_contradiction' as FindingCategory,
    current_verdict: 'pending' as Verdict,
    latest_decision_id: null,
    decision_recorded_at: null,
    observation: observation(),
    ...overrides,
  };
}

export function findingDetail(overrides: Partial<FindingDetail> = {}): FindingDetail {
  return {
    ...finding(),
    decision_event_count: 0,
    latest_comment: null,
    ...overrides,
  };
}

export function decisionEvent(overrides: Partial<DecisionEvent> = {}): DecisionEvent {
  return {
    decision_id: decisionId('A'),
    finding_uid: FINDING_UID,
    finding_observation_id: OBSERVATION_ID,
    event_type: 'accept' as DecisionEventType,
    verdict: 'accepted' as Verdict,
    comment: null,
    author_label: 'local-reviewer',
    recorded_at: '2026-09-10T09:00:00.000Z',
    ...overrides,
  };
}

export function runStatus(overrides: Partial<RunStatus> = {}): RunStatus {
  return {
    run_id: RUN_ID,
    project_uid: PROJECT_UID,
    state: 'published' as RunState,
    provider_mode: 'recorded' as ProviderMode,
    created_at: '2026-09-10T08:00:00.000Z',
    terminal_at: '2026-09-10T08:04:00.000Z',
    terminal_reason: null,
    interrupted_reason: null,
    stages: [],
    degradation_set: [],
    published_finding_count: 1,
    diagnostic_observation_count: 0,
    ...overrides,
  };
}

/**
 * Quotations chosen to break anything that "cleans up" a string on the way to the screen:
 * Cyrillic, a non-breaking space, typographic quotes, an interior newline, leading and
 * trailing whitespace, and an astral-plane character whose UTF-16 length differs from its
 * code-point length.
 */
export const AWKWARD_QUOTES = [
  '  leading and trailing whitespace  ',
  'Срок поставки — 30 дней',
  '«Исполнитель» обязуется … в течение 45 дней',
  'first line\nsecond line',
  'emoji anchor \u{1F5CE} in the middle',
  'double  interior   spaces',
] as const;
