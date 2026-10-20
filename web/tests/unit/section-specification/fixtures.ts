/**
 * «Оптимизация разделов» seeds (`W63-SECTION-FORM7-01`), shared by its unit tests, the
 * rendered-language guard and the contrast census.
 *
 * Every string a seed carries is Cyrillic, a number, an identity or a contract enum, so
 * anything Latin a render shows is chrome the application authored.
 */

import type { SectionSpecification } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { SECTION_ROW_LIMIT } from '@/entities/section-specification';

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const PROJECT_UID = `prj_${ULID}`;
const DOCUMENT_UID = `doc_${ULID}`;
const VERSION_UID = `ver_${ULID}`;
const RUN_ID = `run_${ULID}`;
const SHA = '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f';
const SPEC_POSITION = 'prp_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

export { PROJECT_UID as SECTION_PROJECT_A, DOCUMENT_UID as SECTION_DOCUMENT_A, VERSION_UID as SECTION_VERSION_A };

/**
 * `W63-SECTION-FORM7-01`. One answer of «Оптимизация разделов», every value Cyrillic, an
 * identifier or a contract enum. `ready` carries two projects: one priced (a row of each status,
 * two currencies, every exclusion, a source of every state, a skipped line) and one with no
 * price list (its rows without any match), a current version nobody classified, the rows of
 * both projects and a second page; the other shapes carry the bounds, an empty section, one
 * project and a search that finds nothing.
 */
export const SECTION_ULID_B = '01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
export const SECTION_PROJECT_B = `prj_${SECTION_ULID_B}`;
export const SECTION_DOCUMENT_B = `doc_${SECTION_ULID_B}`;
export const SECTION_VERSION_B = `ver_${SECTION_ULID_B}`;
const SECTION_SKIPS = {
  table_header_ambiguous: 0, text_before_first_row: 0, continuation_limit: 0, anchor_ambiguous: 0,
  position_missing: 1, name_missing: 0, column_numbering: 0, rows_over_limit: 0,
} as const;
const sectionRowBase = {
  sheet_label: '10', line_start: 3, line_end: 3, table_ordinal: 1, group: null, unit_text: 'шт.', unit: 'шт' as const,
  quantity_text: '12', quantity: '12', quantity_issue: null, mass_text: null, note: null, reason: null, basis: null,
  price_position: null, candidate_position_ids: [], candidate_count: 0, amount: null, excluded_reason: null,
};
export const sectionAnswer = (over: Partial<SectionSpecification> = {}): SectionSpecification => ({
  section_code: 'AR',
  state: 'ready',
  limit_reason: null,
  project_filter: null,
  query: null,
  extraction_algorithm: 'specification-text-v1',
  match_algorithm: 'price-match-v1',
  projects: [
    {
      project_uid: PROJECT_UID,
      name: 'Школа на пятьсот мест',
      price_state: 'priced',
      price_list: {
        price_list_id: 'prl_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', revision_number: 3, source_filename: 'Прайс проекта',
        uploaded_at: '2026-10-20T08:00:00Z', default_currency: 'RUB', position_count: 120,
      },
      sources: [
        {
          document_uid: DOCUMENT_UID, display_title: 'Архитектурные решения', version_uid: VERSION_UID, version_ordinal: 2,
          page_count: 30, project_stage: 'R', state: 'ready', run_id: RUN_ID, text_layer_sha256: SHA, row_count: 4,
          table_count: 1, skipped_by_reason: SECTION_SKIPS,
        },
        {
          document_uid: `doc_${ULID}`.replace('B', 'F'), display_title: 'Архитектурные решения, паркинг', version_uid: `ver_${ULID}`.replace('B', 'F'),
          version_ordinal: 1, page_count: 12, project_stage: 'P', state: 'analysis_missing', run_id: null,
          text_layer_sha256: null, row_count: null, table_count: null, skipped_by_reason: null,
        },
        {
          document_uid: `doc_${ULID}`.replace('B', 'C'), display_title: 'Архитектурные решения, склад', version_uid: `ver_${ULID}`.replace('B', 'C'),
          version_ordinal: 1, page_count: 8, project_stage: 'R', state: 'text_unavailable', run_id: RUN_ID,
          text_layer_sha256: null, row_count: null, table_count: null, skipped_by_reason: null,
        },
        {
          document_uid: `doc_${ULID}`.replace('B', 'D'), display_title: 'Архитектурные решения, котельная', version_uid: `ver_${ULID}`.replace('B', 'D'),
          version_ordinal: 4, page_count: 8, project_stage: 'R', state: 'specification_too_large', run_id: RUN_ID,
          text_layer_sha256: SHA, row_count: null, table_count: 2, skipped_by_reason: SECTION_SKIPS,
        },
      ],
      row_count: 4,
      matching: {
        algorithm: 'price-match-v1',
        counts: { matched: 2, ambiguous: 1, unmatched: 1 },
        totals: [
          { currency: 'EUR', amount: '2550', row_count: 1 },
          { currency: 'RUB', amount: '502006.5', row_count: 1 },
        ],
        excluded: { no_position: 1, unit_mismatch: 0, row_unit_missing: 0, ambiguous: 1, quantity_not_numeric: 0 },
      },
    },
    {
      project_uid: SECTION_PROJECT_B,
      name: 'Детский сад',
      price_state: 'price_list_missing',
      price_list: null,
      sources: [
        {
          document_uid: SECTION_DOCUMENT_B, display_title: 'Архитектурные решения', version_uid: SECTION_VERSION_B, version_ordinal: 1,
          page_count: 20, project_stage: 'R', state: 'ready', run_id: RUN_ID, text_layer_sha256: SHA, row_count: 2,
          table_count: 1, skipped_by_reason: { ...SECTION_SKIPS, position_missing: 0 },
        },
      ],
      row_count: 2,
      matching: null,
    },
  ],
  excluded: [
    {
      project_uid: SECTION_PROJECT_B, project_name: 'Детский сад', document_uid: `doc_${ULID}`.replace('B', 'E'),
      display_title: 'Новый комплект', version_uid: `ver_${ULID}`.replace('B', 'E'), version_ordinal: 2, reason: 'version_unclassified',
    },
  ],
  excluded_count: 3,
  source_count: 5,
  row_count: 6,
  rows: {
    offset: 0,
    limit: SECTION_ROW_LIMIT,
    total: 6,
    next_offset: null,
    items: [
      {
        ...sectionRowBase, project_uid: PROJECT_UID, document_uid: DOCUMENT_UID, version_uid: VERSION_UID,
        row_id: `sr-${'a'.repeat(32)}`, page_number: 14, group: 'Изделия', position: '1', name: 'Металлический щит МЩ-1',
        mass_text: '45,5', note: 'по месту', price_status: 'matched', basis: 'name', amount: '180000',
        price_position: {
          price_list_position_id: SPEC_POSITION, row_number: 7, code: 'К-1', name: 'Мет. щит МЩ-1',
          mark: 'МЩ-1', unit: 'шт', unit_price: '15000', currency: 'RUB', vendor: 'Завод',
        },
        candidate_position_ids: [SPEC_POSITION], candidate_count: 1,
      },
      {
        ...sectionRowBase, project_uid: PROJECT_UID, document_uid: DOCUMENT_UID, version_uid: VERSION_UID,
        row_id: `sr-${'b'.repeat(32)}`, page_number: 15, sheet_label: null, position: '2', name: 'Лента монтажная',
        unit_text: 'компл.', unit: 'компл', quantity_text: '1 250', quantity: null, quantity_issue: 'ambiguous',
        price_status: 'matched', basis: 'mark', excluded_reason: 'quantity_not_numeric',
        price_position: {
          price_list_position_id: SPEC_POSITION, row_number: 8, code: null, name: 'Лента', mark: null, unit: 'компл',
          unit_price: '450', currency: 'RUB', vendor: null,
        },
        candidate_position_ids: [SPEC_POSITION], candidate_count: 1,
      },
      {
        ...sectionRowBase, project_uid: PROJECT_UID, document_uid: DOCUMENT_UID, version_uid: VERSION_UID,
        row_id: `sr-${'c'.repeat(32)}`, page_number: 15, sheet_label: null, position: '3', name: 'Пена монтажная',
        quantity_text: '-', quantity: null, quantity_issue: 'not_numeric', price_status: 'ambiguous',
        reason: 'several_positions', excluded_reason: 'ambiguous',
        candidate_position_ids: [SPEC_POSITION, SPEC_POSITION], candidate_count: 2,
      },
      {
        ...sectionRowBase, project_uid: PROJECT_UID, document_uid: DOCUMENT_UID, version_uid: VERSION_UID,
        row_id: `sr-${'d'.repeat(32)}`, page_number: 15, sheet_label: null, position: null, name: 'Профиль направляющий',
        unit_text: 'п. м', unit: 'п.м', quantity_text: '120', quantity: '120', price_status: 'unmatched',
        reason: 'unit_mismatch', excluded_reason: 'unit_mismatch', candidate_position_ids: [SPEC_POSITION], candidate_count: 1,
      },
      {
        ...sectionRowBase, project_uid: SECTION_PROJECT_B, document_uid: SECTION_DOCUMENT_B, version_uid: SECTION_VERSION_B,
        row_id: `sr-${'e'.repeat(32)}`, page_number: 9, position: '1', name: 'Металлический щит МЩ-1',
        price_status: 'price_list_missing',
      },
      {
        ...sectionRowBase, project_uid: SECTION_PROJECT_B, document_uid: SECTION_DOCUMENT_B, version_uid: SECTION_VERSION_B,
        row_id: `sr-${'f'.repeat(32)}`, page_number: 9, line_start: 4, line_end: 5, position: '2', name: 'Окно двухкамерное',
        unit_text: null, unit: null, quantity_text: null, quantity: null, price_status: 'price_list_missing',
      },
    ],
  },
  ...over,
});
export const SECTION_NO_ROWS = { rows: null, row_count: 0 } as const;
export const sectionKey = (filter: { projectUid?: string | null; q?: string | null } = {}) =>
  queryKeys.optimisation.sectionSpecification('AR', {
    projectUid: (filter.projectUid ?? null) as never, q: filter.q ?? null, offset: 0, limit: SECTION_ROW_LIMIT,
  });

/** The same answer one page into a longer list: the pager has a page before and after it. */
export const sectionPagedAnswer = (): SectionSpecification => {
  const answer = sectionAnswer();
  return {
    ...answer,
    row_count: 120,
    rows: { ...answer.rows!, offset: SECTION_ROW_LIMIT, total: 120, next_offset: SECTION_ROW_LIMIT * 2 },
  };
};
