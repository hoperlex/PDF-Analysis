/**
 * Seeding a query cache for the screens of «Сравнение версий», shared by the screen tests and the contrast census
 * (`CMP-VC-UI-01`). A static render never runs a query function, so every state a screen is judged in is a cache entry built
 * here — including the error states, which are an `ApiError` set on the entry.
 */

import type { QueryClient } from '@tanstack/react-query';

import type { Account, DocumentVersion, ProductVersion } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import { VERSION_PAGE_LIMIT } from '@/entities/document-version';
import { COMPARISON_KEYS } from '@/entities/version-series';

import { seedError } from '../screens/harness';

import {
  DOCUMENT_UID,
  PROJECT_UID,
  TRANSITION_23,
  V1,
  V2,
  V3,
  edits,
  matrix,
  overview,
  pairs,
  queueSummary,
  series,
  uid,
} from './fixtures';

export const EXPERT: Account = {
  archived_at: null, display_label: 'Сьютова Е.', first_name: 'Е', is_default_credential: false, last_name: 'Сьютова',
  login: 'e@suite.invalid', middle_name: null, profile_complete: true, roles: ['expert'], user_uid: uid('usr', 1),
};
export const READER: Account = { ...EXPERT, roles: ['admin'], login: 'a@suite.invalid' };

export function product(modules: ProductVersion['comparison_modules']): ProductVersion {
  return { build_id: 'build-1', contract_version: '1.10.0', product_version: '0.9.0', ...(modules === undefined ? {} : { comparison_modules: modules }) };
}

export function version(uidOf: string, ordinal: number, file: string): DocumentVersion {
  return {
    byte_size: 1000, document_uid: DOCUMENT_UID, input_manifest: [], media_type: 'application/pdf', page_count: 7,
    project_uid: PROJECT_UID, published_at: '2026-10-20T00:00:00Z', sha256: 'a'.repeat(64), source_filename: file,
    version_ordinal: ordinal, version_uid: uidOf,
  } as DocumentVersion;
}

export function refusal(code: 'dependency_unavailable' | 'conflict' | 'internal_error', details: Record<string, string> = {}): ApiError {
  return new ApiError(
    code === 'dependency_unavailable' ? 503 : code === 'conflict' ? 409 : 500,
    {
      contract_version: '1.10.0', error_code: code, message: 'A caller-safe sentence in English.',
      correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100', retryable: code !== 'conflict', details,
    },
    '0f0e9d8c-7b6a-4948-b726-150413021100',
  );
}

export interface Seed {
  readonly account?: Account | null;
  readonly modules?: ProductVersion['comparison_modules'] | null;
  readonly projects?: boolean | 'error';
  readonly overview?: 'ok' | 'wired-not' | 'error' | 'none';
  readonly sheets?: boolean;
}

/** The projects, the session and the module set; with `sheets`, everything the second tab reads. */
export function seedComparison(client: QueryClient, seed: Seed = {}): void {
  if (seed.account !== null) client.setQueryData(queryKeys.account.me(), seed.account ?? EXPERT);
  if (seed.modules !== null) client.setQueryData(queryKeys.releases.version(), product(seed.modules ?? 'versions'));
  const listKey = queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT);
  if (seed.projects === 'error') seedError(client, listKey, refusal('internal_error'));
  else if (seed.projects !== false) {
    client.setQueryData(listKey, {
      items: [{ project_uid: PROJECT_UID, name: 'Корпус 1', created_at: '2026-10-01T00:00:00Z', document_count: 3 }],
      page: { next_cursor: null },
    });
  }
  const mode = seed.overview ?? 'ok';
  if (mode === 'ok') client.setQueryData(COMPARISON_KEYS.overview(PROJECT_UID), overview());
  else if (mode === 'wired-not') seedError(client, COMPARISON_KEYS.overview(PROJECT_UID), refusal('dependency_unavailable', { dependency: 'comparison_overview' }));
  else if (mode === 'error') seedError(client, COMPARISON_KEYS.overview(PROJECT_UID), refusal('internal_error'));
  if (seed.sheets === true) {
    client.setQueryData(COMPARISON_KEYS.matrix(PROJECT_UID, DOCUMENT_UID), matrix());
    client.setQueryData(COMPARISON_KEYS.edits(PROJECT_UID, DOCUMENT_UID), { items: edits(), page: { next_cursor: null } });
    client.setQueryData(COMPARISON_KEYS.seriesList(PROJECT_UID, DOCUMENT_UID), series());
    client.setQueryData(COMPARISON_KEYS.pairs(TRANSITION_23), pairs());
    client.setQueryData(COMPARISON_KEYS.orders(PROJECT_UID, DOCUMENT_UID), null);
    client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), {
      items: [version(V1, 1, 'ЭМ-изм0.pdf'), version(V2, 2, 'ЭМ-изм1.pdf'), version(V3, 3, 'ЭМ-изм2.pdf')],
      page: { next_cursor: null },
    });
  }
}

export { queueSummary };
