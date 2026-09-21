/**
 * Create and list failures.
 *
 * The point of separating these two classifiers is the wording: a failed `GET /projects`
 * must not tell the reader that creating a project failed, because it sends them looking
 * for something they never asked for.
 */

import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError, TransportError, UnrecognizedApiError } from '@/shared/api';
import { classifyCreateProjectFailure, classifyProjectListFailure } from '@/entities/project';

function apiError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.0.0-draft.1',
    error_code: code,
    message: 'A caller-safe sentence.',
    correlation_id: 'corr-1',
    retryable,
  };
  return new ApiError(status, envelope, 'corr-1');
}

describe('creating a project', () => {
  it('renders a refused name as unsupported, with no retry', () => {
    const failure = classifyCreateProjectFailure(apiError(422, 'validation_failed', false));
    expect(failure.kind).toBe('invalid_name');
    expect(failure.presentation).toBe('unsupported');
    expect(failure.retryable).toBe(false);
  });

  it('keeps in-progress apart from reuse, and retries only the first', () => {
    const inProgress = classifyCreateProjectFailure(
      apiError(409, 'idempotency_key_in_progress', true),
    );
    const reuse = classifyCreateProjectFailure(apiError(409, 'idempotency_key_reuse', false));

    expect(inProgress.kind).toBe('in_progress');
    expect(inProgress.retryable).toBe(true);
    expect(inProgress.detail).toContain('тем же ключом');
    expect(inProgress.detail).toContain('второй проект');

    expect(reuse.kind).toBe('duplicate_intent');
    expect(reuse.retryable).toBe(false);
  });

  it('renders an unavailable dependency as retryable under the same key', () => {
    const failure = classifyCreateProjectFailure(apiError(503, 'dependency_unavailable', true));
    expect(failure.kind).toBe('dependency_unavailable');
    expect(failure.retryable).toBe(true);
    expect(failure.detail).toContain('тот же ключ идемпотентности');
  });

  it('classifies anything else explicitly and never as retryable', () => {
    expect(classifyCreateProjectFailure(new Error('x')).kind).toBe('unknown');
    expect(classifyCreateProjectFailure(new Error('x')).retryable).toBe(false);
    expect(
      classifyCreateProjectFailure(new UnrecognizedApiError(500, 'future_code', 'm', 'c')).kind,
    ).toBe('unrecognized');
  });
});

describe('reading the project list', () => {
  it('does not describe a failed read as a failed create', () => {
    const failure = classifyProjectListFailure(apiError(500, 'internal_error', false));
    expect(failure.kind).toBe('server_error');
    expect(failure.title.toLowerCase()).not.toContain('creat');
  });

  it('carries the correlation id and the envelope retryability', () => {
    const failure = classifyProjectListFailure(apiError(503, 'dependency_unavailable', true));
    expect(failure.kind).toBe('dependency_unavailable');
    expect(failure.retryable).toBe(true);
    expect(failure.correlationId).toBe('corr-1');
  });

  it('classifies a transport failure and an unclassifiable value', () => {
    expect(classifyProjectListFailure(new TransportError('no route', { retryable: true })).kind).toBe(
      'transport',
    );
    expect(classifyProjectListFailure(42).kind).toBe('unknown');
    expect(classifyProjectListFailure(42).retryable).toBe(false);
  });
});
