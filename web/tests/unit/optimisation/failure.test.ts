/**
 * A refused price-list upload or vendor-list change, in Russian (`W60-PRICE-LIST-01`): every
 * file constraint the API answers has its own sentence, and nothing shows the API's English.
 */

import { describe, expect, it } from 'vitest';

import { TransportError } from '@/shared/api';
import {
  INHERIT_WITH_ENTRIES_TEXT,
  UPLOAD_CONSTRAINT_TEXT,
  VENDOR_LIST_CONFLICT_TEXT,
  uploadFailureMessage,
  vendorListFailureMessage,
} from '@/entities/price-list';

import { optimisationApiError } from './fixtures';

/** The file constraints `uploadPriceList` answers, as the domain catalog registers them. */
const REGISTERED = [
  'non_empty',
  'byte_size <= 10485760',
  'price_list_format',
  'price_list_unreadable',
  'price_list_encoding',
  'xlsx_part_size <= 67108864',
  'price_list_header',
  'price_list_header_ambiguous',
  'data_rows <= 20000',
  'price_list_no_positions',
];

describe('a refused upload', () => {
  it('has a sentence for exactly the registered file constraints', () => {
    expect(Object.keys(UPLOAD_CONSTRAINT_TEXT).sort()).toEqual([...REGISTERED].sort());
  });

  it.each(REGISTERED)('says what to do about %s', (constraint) => {
    const message = uploadFailureMessage(
      optimisationApiError(422, 'validation_failed', { field: 'content', constraint }),
    );
    expect(message.detail).toBe(UPLOAD_CONSTRAINT_TEXT[constraint]);
    const latin = message.detail.match(/[A-Za-z]{2,}/g) ?? [];
    expect(latin.filter((word) => !['MiB', 'CSV', 'Excel', 'UTF'].includes(word))).toEqual([]);
    expect(message.correlationId).toBe('0f0e9d8c-7b6a-4948-b726-150413021100');
  });

  it('says a refused file name, a reused key and an unknown constraint in Russian', () => {
    expect(
      uploadFailureMessage(
        optimisationApiError(422, 'validation_failed', { field: 'source_filename', constraint: 'plain_base_name' }),
      ).detail,
    ).toMatch(/^Имя файла не подходит/);
    expect(uploadFailureMessage(optimisationApiError(409, 'idempotency_key_reuse')).detail).toMatch(
      /другим файлом/,
    );
    const unknown = uploadFailureMessage(
      optimisationApiError(422, 'validation_failed', { field: 'content', constraint: 'something_new' }),
    );
    expect(unknown.detail).not.toBe('Сообщение об отказе.');
    expect(uploadFailureMessage(new TransportError('uploadPriceList: no answer')).kind).toBe('transport');
  });
});

describe('a refused vendor-list change', () => {
  it('says a stale list and entries with inherit in their own words', () => {
    expect(
      vendorListFailureMessage(optimisationApiError(409, 'conflict', { conflict_reason: 'vendor_list_changed' }))
        .detail,
    ).toBe(VENDOR_LIST_CONFLICT_TEXT);
    expect(
      vendorListFailureMessage(
        optimisationApiError(422, 'validation_failed', { field: 'entries', constraint: 'inherit_has_no_entries' }),
      ).detail,
    ).toBe(INHERIT_WITH_ENTRIES_TEXT);
  });
});
