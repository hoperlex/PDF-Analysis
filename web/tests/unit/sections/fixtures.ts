/**
 * Fixtures for the stage-and-section suites (`W59-SECTION-UI-01`): a version, its
 * classification, its fifteen-option review and the refusals the API answers with.
 */

import type {
  DocumentVersion,
  DocumentVersionPage,
  ErrorCode,
  ErrorEnvelope,
  SectionReview,
  VersionClassification,
} from '@/shared/api';
import { ApiError, PROJECT_SECTION_VALUES } from '@/shared/api';

import { DOCUMENT_UID, PROJECT_UID, VERSION_UID } from '../review/fixtures';

export { DOCUMENT_UID, PROJECT_UID, VERSION_UID };

export const ADDRESS = { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, versionUid: VERSION_UID };

export function version(overrides: Partial<DocumentVersion> = {}): DocumentVersion {
  return {
    version_uid: VERSION_UID,
    document_uid: DOCUMENT_UID,
    project_uid: PROJECT_UID,
    version_ordinal: 1,
    media_type: 'application/pdf',
    byte_size: 58978,
    sha256: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
    page_count: 8,
    published_at: '2026-09-18T06:55:52.642022Z',
    input_manifest: [],
    display_title: 'Комплект АР',
    ...overrides,
  };
}

/** A second document, distinct in both identities, with the same shape. */
export function otherVersion(suffix: string, overrides: Partial<DocumentVersion> = {}): DocumentVersion {
  return version({
    document_uid: `${DOCUMENT_UID.slice(0, -1)}${suffix}`,
    version_uid: `${VERSION_UID.slice(0, -1)}${suffix}`,
    display_title: `Документ ${suffix}`,
    ...overrides,
  });
}

export function page(items: DocumentVersion[], nextCursor: string | null = null): DocumentVersionPage {
  return { items, page: { next_cursor: nextCursor } as DocumentVersionPage['page'] };
}

export function classification(overrides: Partial<VersionClassification> = {}): VersionClassification {
  return {
    version_uid: VERSION_UID,
    project_stage: 'P',
    section_code: 'AR',
    confirmed_at: '2026-10-20T08:00:00Z',
    confirmed_by_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
    revision: 1,
    ...overrides,
  };
}

/**
 * All fifteen options in the API's own order (the contract's), AR and KJ suggested with
 * evidence, KM suggested more weakly, PB without a registered profile.
 */
export function review(overrides: Partial<SectionReview> = {}): SectionReview {
  return {
    version_uid: VERSION_UID,
    classification: null,
    revisions: [],
    recognised_text_consulted: true,
    options: PROJECT_SECTION_VALUES.map((code) => ({
      section_code: code,
      name: code,
      executable: true,
      suggestion:
        code === 'KJ'
          ? { score: 9, filename_patterns: ['КЖ', '-KJ'], text_keywords: ['армирование'], name_in_text: false }
          : code === 'AR'
            ? { score: 4, filename_patterns: [], text_keywords: ['поэтажный план'], name_in_text: true }
            : code === 'KM'
              ? { score: 4, filename_patterns: ['КМ'], text_keywords: [], name_in_text: false }
              : null,
    })),
    ...overrides,
  };
}

export function apiError(
  status: number,
  code: ErrorCode,
  details?: Record<string, string | number | boolean | null>,
): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.12.0',
    error_code: code,
    message: 'A caller-safe sentence.',
    correlation_id: 'cid-section',
    retryable: false,
    ...(details === undefined ? {} : { details }),
  };
  return new ApiError(status, envelope, 'cid-section');
}
