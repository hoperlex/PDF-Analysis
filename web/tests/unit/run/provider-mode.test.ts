/**
 * `provider_mode` is visible, and a recorded run never passes as a live one.
 *
 * This is a named PC-01 acceptance criterion. The failure it guards against is not a
 * missing badge — it is a *default*: a reading that carries no provenance being rendered
 * as `live` because `live` is the ordinary case.
 */

import { describe, expect, it } from 'vitest';

import type { RunState, RunStatus } from '@/shared/api';
import { PROVIDER_MODE_VALUES } from '@/shared/api';
import {
  PROVIDER_MODE_UNKNOWN,
  badgeProviderMode,
  interruptedReason,
  isRunAnimating,
  providerModeCaption,
  providerModeLabel,
  runHasPublishedResult,
  runProviderMode,
} from '@/entities/audit-run';

function reading(state: RunState, extra: Partial<RunStatus> = {}): RunStatus {
  return {
    run_id: 'run_01M2545JSD15ETSNNV904X991J',
    project_uid: 'prj_01M2545JSD15ETSNNV904X991J',
    version_uid: 'ver_01M2545JSD15ETSNNV904X991J',
    provider_mode: 'live',
    created_at: '2026-01-01T00:00:00Z',
    state,
    stages: [],
    ...extra,
  };
}

describe('a run with no provider provenance renders `unknown`, never `live`', () => {
  it('renders unknown for an absent, null, empty or unrecognised value', () => {
    for (const value of [undefined, null, '', 'LIVE', 'Live', 'replayed', 0, {}]) {
      expect(providerModeLabel(value)).toBe(PROVIDER_MODE_UNKNOWN);
      expect(providerModeLabel(value)).not.toBe('live');
    }
  });

  it('renders unknown for a reading whose provider_mode is missing', () => {
    // Typed loosely on purpose: the contract makes the field required, and a client that
    // trusts that has decided a malformed response should read as `live`.
    const malformed: { provider_mode?: unknown } = {};
    expect(runProviderMode(malformed)).toBe(PROVIDER_MODE_UNKNOWN);
  });

  it('renders the contract value when there is one', () => {
    expect(runProviderMode(reading('running'))).toBe('live');
    expect(runProviderMode(reading('running', { provider_mode: 'recorded' }))).toBe('recorded');
  });

  it('offers the badge only the two qualifiers it declares', () => {
    expect(badgeProviderMode('live')).toBe('live');
    expect(badgeProviderMode('recorded')).toBe('recorded');
    expect(badgeProviderMode(PROVIDER_MODE_UNKNOWN)).toBeUndefined();
  });

  it('covers exactly the contract value set, plus the explicit absence', () => {
    expect(PROVIDER_MODE_VALUES).toEqual(['live', 'recorded']);
  });
});

describe('the caption says what the provenance is not evidence of', () => {
  it('says a recorded run is not evidence of a live provider call', () => {
    expect(providerModeCaption('recorded').toLowerCase()).toContain('не является свидетельством');
  });

  it('says an unknown provenance is not treated as live', () => {
    expect(providerModeCaption(PROVIDER_MODE_UNKNOWN).toLowerCase()).toContain('не считается живым');
  });

  it('has a caption for every label', () => {
    for (const label of ['live', 'recorded', PROVIDER_MODE_UNKNOWN] as const) {
      expect(providerModeCaption(label).length).toBeGreaterThan(0);
    }
  });
});

describe('a reconciled interrupted run stops animating', () => {
  it('animates while the run is genuinely open', () => {
    expect(isRunAnimating(reading('queued'))).toBe(true);
    expect(isRunAnimating(reading('running'))).toBe(true);
    expect(isRunAnimating(reading('validating'))).toBe(true);
    expect(isRunAnimating(reading('created'))).toBe(true);
  });

  it('stops on every terminal state', () => {
    for (const state of ['published', 'partial', 'failed', 'cancelled'] as const) {
      expect(isRunAnimating(reading(state))).toBe(false);
    }
  });

  it('stops on a non-terminal reading that carries an OD-10 interrupted reason', () => {
    const interrupted = reading('running', { interrupted_reason: 'worker lost' });
    expect(interruptedReason(interrupted)).toBe('worker lost');
    expect(isRunAnimating(interrupted)).toBe(false);
  });

  it('treats an empty or null reason as no reason', () => {
    expect(interruptedReason(reading('failed', { interrupted_reason: null }))).toBeNull();
    expect(interruptedReason(reading('failed', { interrupted_reason: '' }))).toBeNull();
  });
});

describe('the review entry point is offered exactly when a result was published', () => {
  it('offers it for published and partial, per OD-11', () => {
    expect(runHasPublishedResult('published')).toBe(true);
    expect(runHasPublishedResult('partial')).toBe(true);
  });

  it('withholds it for failed, cancelled and every non-terminal state', () => {
    for (const state of ['failed', 'cancelled', 'created', 'queued', 'running', 'validating'] as const) {
      expect(runHasPublishedResult(state)).toBe(false);
    }
  });
});
