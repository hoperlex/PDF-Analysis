/**
 * Starting and watching a run: every failure explicit, and no silent downgrade.
 *
 * The load-bearing assertion is the last one. When the provider is unavailable, the
 * screen must not offer to start the run in `recorded` mode instead — a run whose
 * provenance the user did not choose is exactly the thing `provider_mode` exists to keep
 * distinguishable.
 */

import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError, TransportError, UnrecognizedApiError } from '@/shared/api';
import { classifyRunFailure } from '@/entities/audit-run';

function apiError(
  status: number,
  code: ErrorCode,
  retryable: boolean,
  details?: Record<string, string | number | boolean | null>,
): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.0.0-draft.1',
    error_code: code,
    message: 'A caller-safe sentence.',
    correlation_id: 'corr-run',
    retryable,
    ...(details === undefined ? {} : { details }),
  };
  return new ApiError(status, envelope, 'corr-run');
}

describe('an unavailable provider is explicit and offers no fallback', () => {
  const failure = classifyRunFailure(
    apiError(503, 'dependency_unavailable', true, { dependency: 'model_provider' }),
  );

  it('is its own state, retryable because the envelope says so', () => {
    expect(failure.kind).toBe('provider_unavailable');
    expect(failure.presentation).toBe('error');
    expect(failure.retryable).toBe(true);
    expect(failure.correlationId).toBe('corr-run');
  });

  it('names the dependency the catalog declared safe to name', () => {
    expect(failure.detail).toContain('model_provider');
  });

  it('never offers to fall back to recorded mode', () => {
    const text = `${failure.title} ${failure.detail}`.toLowerCase();
    expect(text).not.toContain('recorded');
    expect(text).not.toContain('fall back');
    expect(text).not.toContain('fallback');
    expect(text).not.toContain('instead of');
  });

  it('says the retry reuses the same key', () => {
    expect(failure.detail).toContain('same idempotency key');
  });
});

describe('an invalid analysis input is not the same state as an invalid request', () => {
  it('keeps analysis_input_invalid and validation_failed apart', () => {
    const analysis = classifyRunFailure(
      apiError(422, 'analysis_input_invalid', false, { stage_id: 'source_preparation' }),
    );
    const request = classifyRunFailure(apiError(422, 'validation_failed', false));

    expect(analysis.kind).toBe('analysis_input_invalid');
    expect(request.kind).toBe('request_invalid');
    expect(analysis.kind).not.toBe(request.kind);
    expect(analysis.title).not.toBe(request.title);
    expect(analysis.detail).toContain('source_preparation');
  });

  it('renders both as unsupported, with no retry', () => {
    for (const code of ['analysis_input_invalid', 'validation_failed'] as const) {
      const failure = classifyRunFailure(apiError(422, code, false));
      expect(failure.presentation).toBe('unsupported');
      expect(failure.retryable).toBe(false);
    }
  });
});

describe('the idempotency outcomes of a run request', () => {
  it('retries in-progress under the same key and never mints a second run', () => {
    const failure = classifyRunFailure(apiError(409, 'idempotency_key_in_progress', true));
    expect(failure.kind).toBe('in_progress');
    expect(failure.retryable).toBe(true);
    expect(failure.detail).toContain('same key');
    expect(failure.detail).toContain('second run');
  });

  it('treats reuse as terminal', () => {
    const failure = classifyRunFailure(apiError(409, 'idempotency_key_reuse', false));
    expect(failure.kind).toBe('duplicate_intent');
    expect(failure.retryable).toBe(false);
    expect(failure.detail).toContain('No run was created');
  });
});

describe('nothing thrown by a run request escapes classification', () => {
  it('classifies not_found, state_transition_not_allowed and analysis_failed distinctly', () => {
    const kinds = [
      classifyRunFailure(apiError(404, 'not_found', false)).kind,
      classifyRunFailure(apiError(409, 'state_transition_not_allowed', false)).kind,
      classifyRunFailure(apiError(500, 'analysis_failed', false)).kind,
    ];
    expect(new Set(kinds).size).toBe(3);
  });

  it('classifies an unrecognized code, a transport failure and an unknown value', () => {
    expect(classifyRunFailure(new UnrecognizedApiError(500, 'future_code', 'm', 'c')).kind).toBe(
      'unrecognized',
    );
    expect(classifyRunFailure(new TransportError('no route', { retryable: true })).kind).toBe(
      'transport',
    );
    const unknown = classifyRunFailure(null);
    expect(unknown.kind).toBe('unknown');
    expect(unknown.retryable).toBe(false);
  });

  it('never renders a failure as a success', () => {
    for (const code of [
      'dependency_unavailable',
      'analysis_input_invalid',
      'validation_failed',
      'not_found',
      'analysis_failed',
      'internal_error',
    ] as const) {
      const failure = classifyRunFailure(apiError(500, code, false));
      expect(failure.title.toLowerCase()).not.toContain('success');
      expect(failure.title.length).toBeGreaterThan(0);
    }
  });
});
