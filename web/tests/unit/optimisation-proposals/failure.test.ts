/**
 * A refused pass or decision, in Russian (`W60-OPT-PROPOSALS-01`): every `conflict_reason` of
 * `startOptimisationPass` has its own sentence that says what to do, a `revise` without a
 * comment is said as such, and nothing shows the API's English.
 */

import { describe, expect, it } from 'vitest';

import { TransportError } from '@/shared/api';
import {
  COMMENT_REQUIRED_TEXT,
  COMMENT_TOO_LONG_TEXT,
  PASS_REFUSAL_TEXT,
  decideFailureMessage,
  startPassFailureMessage,
} from '@/entities/optimisation-proposal';

import { optimisationApiError } from '../optimisation/fixtures';

/** The reasons `startOptimisationPass` answers, as the domain catalog registers them. */
const REGISTERED = [
  'version_unclassified',
  'section_not_ar',
  'price_list_missing',
  'analysis_missing',
  'text_unavailable',
  'specification_too_large',
  'vendor_list_missing',
];

describe('a refused start', () => {
  it('has a sentence for exactly the registered reasons', () => {
    expect(Object.keys(PASS_REFUSAL_TEXT).sort()).toEqual([...REGISTERED].sort());
  });

  it.each(REGISTERED)('says what to do about %s', (reason) => {
    const message = startPassFailureMessage(
      optimisationApiError(409, 'conflict', { conflict_reason: reason, aggregate_type: 'OptimisationPass' }),
    );
    expect(message.detail).toBe(PASS_REFUSAL_TEXT[reason]);
    expect(message.detail).not.toMatch(/[A-Za-z_]{3,}/);
    expect(message.correlationId).toBe('0f0e9d8c-7b6a-4948-b726-150413021100');
  });

  it('does not tell the expert that proposals exist for АР only, or that the list is the АР one', () => {
    for (const sentence of Object.values(PASS_REFUSAL_TEXT)) {
      expect(sentence).not.toMatch(/только для АР|раздела АР|раздел АР/);
    }
    expect(PASS_REFUSAL_TEXT['vendor_list_missing']).toMatch(/раздела этого комплекта/);
  });

  it('falls back to the catalog’s Russian for a reason it does not know, a reused key and a transport failure', () => {
    const unknown = startPassFailureMessage(
      optimisationApiError(409, 'conflict', { conflict_reason: 'something_new' }),
    );
    expect(unknown.detail).not.toBe('Сообщение об отказе.');
    expect(Object.values(PASS_REFUSAL_TEXT)).not.toContain(unknown.detail);
    expect(startPassFailureMessage(optimisationApiError(409, 'idempotency_key_reuse')).detail).toMatch(
      /другого комплекта/,
    );
    expect(startPassFailureMessage(optimisationApiError(403, 'permission_denied')).kind).toBe(
      'permission_denied',
    );
    expect(startPassFailureMessage(new TransportError('POST /x', { status: null })).kind).toBe('transport');
  });
});

describe('a refused decision', () => {
  it('says a revise without a comment and a comment that is too long', () => {
    expect(
      decideFailureMessage(
        optimisationApiError(422, 'validation_failed', { field: 'comment', constraint: 'required' }),
      ).detail,
    ).toBe(COMMENT_REQUIRED_TEXT);
    expect(
      decideFailureMessage(
        optimisationApiError(422, 'validation_failed', { field: 'comment', constraint: 'max_length' }),
      ).detail,
    ).toBe(COMMENT_TOO_LONG_TEXT);
  });

  it('keeps the catalog’s Russian for everything else, and says an admin alone is refused', () => {
    const other = decideFailureMessage(
      optimisationApiError(422, 'validation_failed', { field: 'verdict', constraint: 'enum' }),
    );
    expect(other.detail).not.toBe(COMMENT_REQUIRED_TEXT);
    expect(other.detail).not.toBe('Сообщение об отказе.');
    expect(decideFailureMessage(optimisationApiError(403, 'permission_denied')).kind).toBe('permission_denied');
    expect(decideFailureMessage(optimisationApiError(409, 'idempotency_key_reuse')).detail).toMatch(
      /другим решением/,
    );
  });
});
