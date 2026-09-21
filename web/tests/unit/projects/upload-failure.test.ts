/**
 * Every upload failure is an explicit, distinguishable state.
 *
 * The three the PC-01 acceptance criteria name separately — an unsupported input, a
 * checksum failure and an unavailable dependency — must not collapse into one another
 * and must not collapse into a spinner or a success. That is what this suite holds.
 */

import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError, TransportError, UnrecognizedApiError } from '@/shared/api';
import { classifyUploadFailure } from '@/entities/document-version';

function envelope(
  code: ErrorCode,
  retryable: boolean,
  details?: Record<string, string | number | boolean | null>,
): ErrorEnvelope {
  return {
    contract_version: '1.0.0-draft.1',
    error_code: code,
    message: 'A caller-safe sentence.',
    correlation_id: 'corr-upload-1',
    retryable,
    ...(details === undefined ? {} : { details }),
  };
}

function apiError(
  status: number,
  code: ErrorCode,
  retryable: boolean,
  details?: Record<string, string | number | boolean | null>,
): ApiError {
  return new ApiError(status, envelope(code, retryable, details), 'corr-upload-1');
}

describe('the three named criteria are three different states', () => {
  const unsupported = classifyUploadFailure(
    apiError(422, 'validation_failed', false, { constraint: 'page_count_at_most_30' }),
  );
  const checksum = classifyUploadFailure(
    apiError(422, 'storage_integrity_error', false, { role: 'source.pdf' }),
  );
  const unavailable = classifyUploadFailure(apiError(503, 'dependency_unavailable', true));

  it('classifies an unsupported input as unsupported, with no retry', () => {
    expect(unsupported.kind).toBe('unsupported_input');
    expect(unsupported.presentation).toBe('unsupported');
    expect(unsupported.retryable).toBe(false);
    expect(unsupported.errorCode).toBe('validation_failed');
  });

  /**
   * `W31-RUS`, under `R-18`. This asserted the **envelope message** and the classifier.
   * The message is the API's own English — `contracts/domain/v1/error-codes.json` carries
   * 22 summaries and not one Cyrillic character — so the screen now renders
   * `catalogMessage(code)` in its place and keeps `details`.
   *
   * The claim in the name survives the change and is what is asserted here: the state is
   * still **specific**, not generic. The discriminating fact was never in the English
   * prose — it is `details.constraint`, which is what `tests/e2e/pc01/journey/manifest.json`
   * checks under `expects_rendered_from_envelope` (`not_encrypted`,
   * `every_page_has_extractable_text`, `page_count`). So: the constraint is still rendered,
   * and two different codes still read differently.
   */
  it('renders the specific reason, not a sentence every code would get', () => {
    expect(unsupported.detail).toContain('page_count_at_most_30');
    expect(unsupported.detail).not.toBe(checksum.detail);
    expect(unsupported.detail).not.toBe(unavailable.detail);
    // And it is Russian, which is the whole point of the substitution.
    expect(/[а-яА-ЯёЁ]/u.test(unsupported.detail)).toBe(true);
    expect(unsupported.detail).not.toContain('A caller-safe sentence.');
  });

  it('classifies a checksum failure as its own state, not as an unsupported input', () => {
    expect(checksum.kind).toBe('checksum_mismatch');
    expect(checksum.kind).not.toBe(unsupported.kind);
    expect(checksum.retryable).toBe(false);
    expect(checksum.errorCode).toBe('storage_integrity_error');
    expect(checksum.detail).toContain('Ничего не опубликовано');
  });

  it('classifies an unavailable dependency as its own state, and as retryable', () => {
    expect(unavailable.kind).toBe('dependency_unavailable');
    expect(unavailable.retryable).toBe(true);
    expect(unavailable.errorCode).toBe('dependency_unavailable');
  });

  it('gives the three of them three distinct kinds and three distinct titles', () => {
    const kinds = new Set([unsupported.kind, checksum.kind, unavailable.kind]);
    const titles = new Set([unsupported.title, checksum.title, unavailable.title]);
    expect(kinds.size).toBe(3);
    expect(titles.size).toBe(3);
  });

  it('never reads as a success and never as "still working"', () => {
    for (const failure of [unsupported, checksum, unavailable]) {
      expect(failure.title.length).toBeGreaterThan(0);
      expect(failure.title.toLowerCase()).not.toContain('success');
      expect(failure.title.toLowerCase()).not.toContain('uploading');
      expect(failure.detail.length).toBeGreaterThan(0);
    }
  });
});

describe('retryability comes from the envelope and never from the status', () => {
  it('does not treat a 503 as retryable when the envelope says it is not', () => {
    const failure = classifyUploadFailure(apiError(503, 'storage_integrity_error', false));
    expect(failure.retryable).toBe(false);
  });

  it('does treat a 422 as retryable when the envelope says it is', () => {
    const failure = classifyUploadFailure(apiError(422, 'dependency_unavailable', true));
    expect(failure.retryable).toBe(true);
  });
});

describe('the idempotency outcomes stay apart', () => {
  it('separates in-progress, which is retried under the same key, from reuse, which is terminal', () => {
    const inProgress = classifyUploadFailure(
      apiError(409, 'idempotency_key_in_progress', true, { command_type: 'upload_document' }),
    );
    const reuse = classifyUploadFailure(apiError(409, 'idempotency_key_reuse', false));
    const stale = classifyUploadFailure(apiError(409, 'idempotency_key_stale', false));

    expect(inProgress.kind).toBe('in_progress');
    expect(inProgress.retryable).toBe(true);
    expect(inProgress.detail).toContain('тем же ключом');

    expect(reuse.kind).toBe('duplicate_intent');
    expect(reuse.retryable).toBe(false);
    expect(reuse.detail).toContain('Ничего не создано');

    expect(stale.kind).toBe('stale_intent');
    expect(stale.retryable).toBe(false);
    expect(new Set([inProgress.kind, reuse.kind, stale.kind]).size).toBe(3);
  });
});

describe('nothing thrown escapes classification', () => {
  it('renders an unrecognized code as an explicit state that retries nothing', () => {
    const failure = classifyUploadFailure(
      new UnrecognizedApiError(422, 'a_code_from_the_future', 'ignored', 'corr-9'),
    );
    expect(failure.kind).toBe('unrecognized');
    expect(failure.retryable).toBe(false);
    expect(failure.correlationId).toBe('corr-9');
  });

  it('renders a transport failure as its own state', () => {
    const failure = classifyUploadFailure(
      new TransportError('uploadDocument could not reach the API.', { retryable: true }),
    );
    expect(failure.kind).toBe('transport');
    expect(failure.retryable).toBe(true);
  });

  it('renders an unclassifiable value explicitly, and never as retryable', () => {
    const failure = classifyUploadFailure(new Error('something nobody modelled'));
    expect(failure.kind).toBe('unknown');
    expect(failure.retryable).toBe(false);
    expect(failure.correlationId).toBeNull();
    expect(failure.title.length).toBeGreaterThan(0);
  });
});

describe('only the safe classifiers the catalog declares are rendered', () => {
  it('ignores a detail key that is not declared safe for the reported code', () => {
    const failure = classifyUploadFailure(
      apiError(422, 'validation_failed', false, {
        constraint: 'encrypted_pdf',
        // Not in the safe key list for validation_failed. It must not reach the screen
        // even if a server ever put it in the envelope.
        dependency: 'must-not-be-rendered',
      }),
    );
    expect(failure.detail).toContain('encrypted_pdf');
    expect(failure.detail).not.toContain('must-not-be-rendered');
  });
});
