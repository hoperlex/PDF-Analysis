/**
 * `W55A-WEB-NORMS` — the norms entity's rules, each without a screen: which snapshot is
 * current, how a fragment is cut at its matched spans, which address values are a document
 * and a page, when the PDF is read, and what each norms refusal says.
 */

import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError, TransportError } from '@/shared/api';
import {
  attributionLabel, buildStateLabel, currentSnapshotOf, fragmentParts, looksLikeNormDocumentId,
  normFailure, pageFromAddress, wantsNormPdf,
} from '@/entities/norms';

import { NORM_DOCUMENT_ID, NORM_SNAPSHOTS, normDocument } from './fixtures';

function refusal(status: number, code: ErrorCode, details: Record<string, string> = {}): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.10.0',
    error_code: code,
    message: 'English the client never prints.',
    correlation_id: 'cid-norms-1',
    retryable: code === 'dependency_unavailable',
    details,
  };
  return new ApiError(status, envelope, 'cid-norms-1');
}

describe('which snapshot is current, as far as one read of the list can tell', () => {
  it('finds the current one wherever it sits on the page', () => {
    const reading = currentSnapshotOf({ items: [...NORM_SNAPSHOTS].reverse(), page: { next_cursor: null } });
    expect(reading).toEqual({ kind: 'current', snapshot: NORM_SNAPSHOTS[0] });
  });

  it('says none only when the whole list was read', () => {
    const others = NORM_SNAPSHOTS.slice(1);
    expect(currentSnapshotOf({ items: others, page: { next_cursor: null } })).toEqual({ kind: 'none' });
    expect(currentSnapshotOf({ items: [], page: { next_cursor: null } })).toEqual({ kind: 'none' });
    // More pages exist: the current one was not read, which is not the same as none.
    expect(currentSnapshotOf({ items: others, page: { next_cursor: 'Y3Vyc29y' } })).toEqual({ kind: 'beyond' });
  });
});

describe('NORM-Q01: a fragment is cut at its matched spans and never changed', () => {
  const join = (parts: readonly { text: string }[]) => parts.map((part) => part.text).join('');

  it('marks each span and keeps the text whole', () => {
    const text = 'Высота жилых помещений';
    const parts = fragmentParts({ text, highlights: [{ char_start: 13, char_end: 22 }, { char_start: 0, char_end: 6 }] });
    expect(parts).toEqual([
      { text: 'Высота', hit: true },
      { text: ' жилых ', hit: false },
      { text: 'помещений', hit: true },
    ]);
    expect(join(parts)).toBe(text);
  });

  it('counts characters, not UTF-16 units, so a character outside the BMP shifts nothing', () => {
    const text = '𝔸 высота';
    const parts = fragmentParts({ text, highlights: [{ char_start: 2, char_end: 8 }] });
    expect(parts).toEqual([{ text: '𝔸 ', hit: false }, { text: 'высота', hit: true }]);
  });

  it('drops a span that is outside the text, empty or overlapping, and loses no word', () => {
    const text = 'норма высоты';
    const parts = fragmentParts({
      text,
      highlights: [
        { char_start: 0, char_end: 5 },
        { char_start: 3, char_end: 9 },
        { char_start: 6, char_end: 6 },
        { char_start: 6, char_end: 40 },
        { char_start: -1, char_end: 2 },
      ],
    });
    expect(parts).toEqual([{ text: 'норма', hit: true }, { text: ' высоты', hit: false }]);
    expect(join(parts)).toBe(text);
    expect(fragmentParts({ text, highlights: [] })).toEqual([{ text, hit: false }]);
  });
});

describe('the address values a norm document view accepts', () => {
  it('a norm document identity is an ndoc_ ULID and nothing else', () => {
    expect(looksLikeNormDocumentId(NORM_DOCUMENT_ID)).toBe(true);
    for (const bad of ['ndoc_short', `prj_${NORM_DOCUMENT_ID.slice(5)}`, `${NORM_DOCUMENT_ID}x`, '', undefined, ['a']]) {
      expect(looksLikeNormDocumentId(bad), String(bad)).toBe(false);
    }
  });

  it('a page is a positive whole number in plain digits; absent is none; anything else is no page', () => {
    expect(pageFromAddress(undefined)).toBeNull();
    expect(pageFromAddress('12')).toBe(12);
    expect(pageFromAddress('1')).toBe(1);
    for (const bad of ['0', '012', '1.5', '-3', 'двенадцать', '', '1e3', ['1', '2']]) {
      expect(pageFromAddress(bad), String(bad)).toBeUndefined();
    }
  });

  it('reads the PDF only for an asked page, a bound document and a page it has', () => {
    expect(wantsNormPdf(normDocument(), 12)).toBe(true);
    expect(wantsNormPdf(normDocument(), 48)).toBe(true);
    expect(wantsNormPdf(normDocument(), null)).toBe(false);
    expect(wantsNormPdf(normDocument(), 49)).toBe(false);
    expect(wantsNormPdf(normDocument({ content_available: false }), 12)).toBe(false);
  });
});

describe('the words for contract values', () => {
  it('names every build state and attribution in Russian', () => {
    expect(buildStateLabel('complete')).toBe('построен полностью');
    expect(buildStateLabel('incomplete')).toBe('построен не полностью');
    expect(buildStateLabel('absent')).toBe('не построен');
    expect(attributionLabel('consultant_plus')).toBe('Источник текста: КонсультантПлюс');
    expect(attributionLabel('unattributed')).toBe('Источник текста: не указан');
  });
});

describe('each norms refusal says what to do next, and nothing prints a thrown message', () => {
  it('tells the three required_norm_unavailable references apart', () => {
    expect(normFailure(refusal(422, 'required_norm_unavailable', { reference_kind: 'norms_snapshot' })).kind)
      .toBe('no_current_snapshot');
    expect(normFailure(refusal(422, 'required_norm_unavailable', { reference_kind: 'norm_embedding_build' })).kind)
      .toBe('index_incomplete');
    expect(normFailure(refusal(422, 'required_norm_unavailable', { reference_kind: 'norm_source' })).kind)
      .toBe('source_unbound');
    // An unregistered reference is the catalog's own reading, not a guess at one of the three.
    expect(normFailure(refusal(422, 'required_norm_unavailable', { reference_kind: 'prompt_bundle' })).kind)
      .toBe('required_norm_unavailable');
  });

  it('reads the timeout and the stale designation off their classifiers only', () => {
    const tooBroad = normFailure(refusal(422, 'validation_failed', { constraint: 'norms_search_too_broad' }));
    expect(tooBroad.kind).toBe('search_too_broad');
    expect(tooBroad.detail).toContain('Запрос слишком широкий');
    expect(normFailure(refusal(422, 'validation_failed')).kind).toBe('validation_failed');
    const stale = normFailure(refusal(409, 'conflict', { conflict_reason: 'stale_current_snapshot' }));
    expect(stale.kind).toBe('stale_current_snapshot');
    expect(stale.correlationId).toBe('cid-norms-1');
    expect(normFailure(refusal(409, 'conflict', { conflict_reason: 'login_taken' })).kind).toBe('conflict');
  });

  it('keeps the sealed stub a retryable dependency failure, and never prints the English', () => {
    const stub = normFailure(refusal(503, 'dependency_unavailable', { dependency: 'norms_search' }));
    expect(stub.kind).toBe('dependency_unavailable');
    expect(stub.retryable).toBe(true);
    for (const failure of [stub, normFailure(new TransportError('GET /norms/search 502')), normFailure(new Error('boom'))]) {
      expect(failure.detail).not.toMatch(/English|boom|502/);
    }
    expect(normFailure(new Error('boom')).kind).toBe('unexpected');
  });
});
