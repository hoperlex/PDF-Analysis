/**
 * Two page-level rules that are easy to get quietly wrong.
 *
 * **Retryability comes from the envelope, never from the HTTP status** (seam §4.4). The
 * contract pins `retryable` to the catalog value for the reported code, so a 503 that the
 * catalog calls terminal must not grow a retry button and a 409 the catalog calls retryable
 * must keep one. Offering a retry that cannot help teaches the reviewer the button is noise.
 *
 * **A page belongs to one finding.** Selecting a finding clears the page, because a page
 * number carried over from the previous finding would put the viewer on a page this finding
 * never cited.
 */

import { describe, expect, it } from 'vitest';

import { presentFailure, presentFailureOrNull } from '@/_pages/review';
import { resolveSelection, selectFinding, selectPage } from '@/_pages/review';
import { ApiError, TransportError, UnrecognizedApiError } from '@/shared/api';
import type { ErrorEnvelope } from '@/shared/api';

function envelope(overrides: Partial<ErrorEnvelope> = {}): ErrorEnvelope {
  return {
    error_code: 'dependency_unavailable',
    message: 'The analysis provider is unavailable.',
    retryable: true,
    correlation_id: 'corr-1',
    ...overrides,
  } as ErrorEnvelope;
}

const noop = () => {};

describe('presenting a failure', () => {
  it('offers a retry when the envelope says the failure is retryable', () => {
    const presented = presentFailure(new ApiError(503, envelope({ retryable: true }), 'corr-1'), {
      title: 'It failed',
      onRetry: noop,
    });
    expect(presented.onRetry).toBe(noop);
    expect(presented.correlationId).toBe('corr-1');
    expect(presented.detail).toContain('dependency_unavailable');
  });

  it('offers no retry when the envelope says it is not, whatever the status', () => {
    // A 503 the catalog calls terminal. Inferring from the status would put a useless
    // button here.
    const presented = presentFailure(new ApiError(503, envelope({ retryable: false }), 'corr-2'), {
      title: 'It failed',
      onRetry: noop,
    });
    expect(presented.onRetry).toBeUndefined();
  });

  it('offers a retry on a 4xx when the envelope says it is retryable', () => {
    // The mirror image: a status a status-based rule would refuse to retry.
    const presented = presentFailure(
      new ApiError(409, envelope({ error_code: 'conflict', retryable: true }), 'corr-3'),
      { title: 'It failed', onRetry: noop },
    );
    expect(presented.onRetry).toBe(noop);
  });

  it('never retries an unrecognized code', () => {
    // An explicit state, not a fallback: the server is ahead of this client, and retrying
    // a code we cannot interpret is guessing.
    const presented = presentFailure(
      new UnrecognizedApiError(500, 'some_future_code', 'Unknown.', 'corr-4'),
      { title: 'It failed', onRetry: noop },
    );
    expect(presented.onRetry).toBeUndefined();
    expect(presented.correlationId).toBe('corr-4');
    expect(presented.detail).toContain('не распознаёт');
  });

  it('carries the correlation id through every failure kind', () => {
    // It is the only handle an operator has on the diagnostic record.
    expect(
      presentFailure(new TransportError('unreachable', { correlationId: 'corr-5' }), {
        title: 'It failed',
      }).correlationId,
    ).toBe('corr-5');
  });

  it('renders something explicit for an error outside the contract', () => {
    const presented = presentFailure(new Error('boom'), { title: 'It failed' });
    expect(presented.title).toBe('It failed');
    expect(presented.onRetry).toBeUndefined();
    // Never the raw message: it is not a caller-safe string and may carry anything.
    expect(presented.detail).not.toContain('boom');
  });

  it('is null when there is no failure', () => {
    expect(presentFailureOrNull(null, { title: 'x' })).toBeNull();
    expect(presentFailureOrNull(undefined, { title: 'x' })).toBeNull();
  });
});

describe('the review selection', () => {
  const A = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
  const B = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';

  it('clears the page when a finding is selected', () => {
    expect(selectFinding(A)).toEqual({ findingUid: A, page: null });
    // The bug this prevents: selecting a finding cited on page 3 while the viewer is still
    // showing page 11 from the previous one.
    expect(selectPage(selectFinding(A), 11)).toEqual({ findingUid: A, page: 11 });
    expect(selectFinding(B)).toEqual({ findingUid: B, page: null });
  });

  it('keeps the finding when only the page changes', () => {
    expect(selectPage({ findingUid: A, page: 2 }, 7)).toEqual({ findingUid: A, page: 7 });
  });

  it('falls back to the first finding when the selection is no longer in the list', () => {
    // After a refetch that replaced the page, a selection pointing at a finding the list no
    // longer offers would leave the panels showing something the list does not.
    expect(resolveSelection({ findingUid: B, page: 4 }, [A])).toEqual({
      findingUid: A,
      page: null,
    });
  });

  it('keeps a selection that is still in the list, page and all', () => {
    expect(resolveSelection({ findingUid: A, page: 4 }, [A, B])).toEqual({
      findingUid: A,
      page: 4,
    });
  });

  it('selects the first finding when nothing is selected yet', () => {
    expect(resolveSelection(null, [A, B])).toEqual({ findingUid: A, page: null });
  });

  it('selects nothing when there are no findings', () => {
    expect(resolveSelection(null, [])).toBeNull();
    expect(resolveSelection({ findingUid: A, page: 1 }, [])).toBeNull();
  });
});
