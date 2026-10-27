/**
 * The «Оптимизация» tab's seeds (`W60-PRICE-LIST-01`), shared by its unit tests, the rendered-
 * language guard and the contrast census.
 *
 * Every string a seed carries is Cyrillic, a number, an identity or a contract enum, so
 * anything Latin a render shows is chrome the application authored. The shapes reach every
 * branch the tab's widgets have: revisions, a positions page with skipped rows, warnings,
 * ambiguous and ignored columns and a next page, an empty page, each refused read, every
 * upload refusal, both vendor-list editors and a refused vendor-list change.
 */

import { createElement } from 'react';
import type { ReactElement } from 'react';
import type { QueryClient } from '@tanstack/react-query';

import type {
  EffectiveVendorLists,
  ErrorCode,
  PriceListPositionPage,
  PriceListRevision,
  ProjectSection,
  SectionVendorList,
  VendorListRevision,
} from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import {
  INHERIT_WITH_ENTRIES_TEXT,
  POSITION_PAGE_LIMIT,
  UPLOAD_CONSTRAINT_TEXT,
  VENDOR_LIST_CONFLICT_TEXT,
} from '@/entities/price-list';
import { UploadPriceListFormView } from '@/features/upload-price-list';
import {
  PriceListPositionsView,
  ProjectOptimisation,
  VendorListsView,
} from '@/widgets/project-optimisation';

import { seedError } from '../screens/harness';

export const OPT_PROJECT_UID = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
export const CURRENT_PRICE_LIST = 'prl_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
export const OLDER_PRICE_LIST = 'prl_01J9ZQ8K7NHVXW3T2R5M6P4Q8D';
const EXPERT_UID = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8E';
const ADMIN_UID = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const CORRELATION = '0f0e9d8c-7b6a-4948-b726-150413021100';

export function revision(overrides: Partial<PriceListRevision> = {}): PriceListRevision {
  return {
    price_list_id: CURRENT_PRICE_LIST,
    project_uid: OPT_PROJECT_UID,
    revision_number: 2,
    is_current: true,
    uploaded_by_user_uid: EXPERT_UID,
    uploaded_at: '2026-10-20T09:00:00Z',
    source_format: 'csv',
    source_filename: 'прайс-2026.csv',
    media_type: 'text/csv',
    size_bytes: 2048,
    sha256: 'a'.repeat(64),
    default_currency: 'RUB',
    data_row_count: 4,
    accepted_row_count: 3,
    skipped_row_count: 1,
    ...overrides,
  };
}

export const REVISIONS: readonly PriceListRevision[] = [
  revision(),
  revision({
    price_list_id: OLDER_PRICE_LIST,
    revision_number: 1,
    is_current: false,
    source_format: 'xlsx',
    source_filename: 'прайс-2025.xlsx',
    media_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    default_currency: null,
  }),
];

export function positionPage(overrides: Partial<PriceListPositionPage> = {}): PriceListPositionPage {
  return {
    revision: revision(),
    parse_report: {
      report_version: 1,
      format: 'csv',
      sheet: null,
      encoding: 'cp1251',
      delimiter: ';',
      header_row: 2,
      columns: [
        { field: 'name', column: 2, header: 'Наименование' },
        { field: 'unit', column: 3, header: 'Ед. изм.' },
        { field: 'unit_price', column: 4, header: 'Цена, руб.' },
        { field: 'code', column: 1, header: 'Код' },
        { field: 'vendor', column: 5, header: 'Поставщик' },
        { field: 'section', column: 6, header: 'Раздел' },
      ],
      ambiguous_columns: [{ field: 'mark', headers: ['Марка', 'Тип'] }],
      ignored_columns: ['Примечание'],
      price_header_currency: 'RUB',
      default_currency: 'RUB',
      preamble_rows: 1,
      blank_rows: 0,
      data_rows: 4,
      accepted_rows: 3,
      skipped_rows: 1,
      skipped_by_reason: [{ reason: 'price_not_a_number', count: 1 }],
      skipped: [{ row: 4, reason: 'price_not_a_number' }],
      skipped_listed_in_full: false,
      warnings_by_reason: [{ reason: 'section_unrecognised', count: 1 }],
      warnings: [{ row: 5, reason: 'section_unrecognised' }],
      currency_sources: [
        { source: 'price_header', count: 2 },
        { source: 'column', count: 1 },
      ],
    },
    items: [
      {
        price_list_position_id: 'prp_01J9ZQ8K7NHVXW3T2R5M6P4Q8G',
        row_number: 3,
        code: 'К-1',
        name: 'Кабель ВВГнг 3х2,5',
        mark: null,
        unit: 'м',
        unit_price: '125.5',
        currency: 'RUB',
        vendor: 'Кабельный завод',
        section_code: 'EOM',
      },
      {
        price_list_position_id: 'prp_01J9ZQ8K7NHVXW3T2R5M6P4Q8H',
        row_number: 5,
        code: null,
        name: 'Щит распределительный',
        mark: 'ЩР-1',
        unit: 'шт',
        unit_price: '12345.67',
        currency: 'EUR',
        vendor: null,
        section_code: null,
      },
    ],
    offset: 50,
    limit: POSITION_PAGE_LIMIT,
    total: 120,
    next_offset: 100,
    ...overrides,
  };
}

function vendorRevision(overrides: Partial<VendorListRevision> = {}): VendorListRevision {
  return {
    vendor_list_id: 'vnl_01J9ZQ8K7NHVXW3T2R5M6P4Q8J',
    scope: 'global',
    project_uid: null,
    section_code: 'EOM',
    mode: 'list',
    revision_number: 3,
    entries: [
      { material: 'Кабель силовой', vendor: 'Кабельный завод', note: 'только с сертификатом' },
      { material: null, vendor: 'Электрокабель', note: null },
    ],
    set_by_user_uid: ADMIN_UID,
    set_at: '2026-10-19T12:00:00Z',
    ...overrides,
  };
}

const SECTION_CODES: readonly ProjectSection[] = [
  'AR', 'AI', 'KM', 'KJ', 'OV', 'EOM', 'VK', 'PT', 'PB', 'SS', 'ITP', 'GP', 'TX', 'POS', 'PS',
];

export function vendorLists(): EffectiveVendorLists {
  const items: SectionVendorList[] = SECTION_CODES.map((code) => {
    if (code === 'EOM') {
      const global = vendorRevision();
      const project = vendorRevision({
        vendor_list_id: 'vnl_01J9ZQ8K7NHVXW3T2R5M6P4Q8K',
        scope: 'project',
        project_uid: OPT_PROJECT_UID,
        revision_number: 1,
        entries: [{ material: 'Светильники', vendor: 'Световые технологии', note: null }],
        set_by_user_uid: EXPERT_UID,
      });
      return { section_code: code, source: 'project', effective: project, global_revision: global, project_revision: project };
    }
    if (code === 'OV') {
      const global = vendorRevision({ vendor_list_id: 'vnl_01J9ZQ8K7NHVXW3T2R5M6P4Q8M', section_code: 'OV', entries: [] });
      const inherit = vendorRevision({
        vendor_list_id: 'vnl_01J9ZQ8K7NHVXW3T2R5M6P4Q8N', scope: 'project', project_uid: OPT_PROJECT_UID,
        section_code: 'OV', mode: 'inherit', entries: [], set_by_user_uid: EXPERT_UID,
      });
      return { section_code: code, source: 'global', effective: global, global_revision: global, project_revision: inherit };
    }
    return { section_code: code, source: 'none', effective: null, global_revision: null, project_revision: null };
  });
  return { project_uid: OPT_PROJECT_UID, items };
}

export function optimisationApiError(status: number, code: ErrorCode, details?: Record<string, string>): ApiError {
  return new ApiError(
    status,
    {
      contract_version: '1.8.0',
      error_code: code,
      message: 'Сообщение об отказе.',
      correlation_id: CORRELATION,
      retryable: false,
      ...(details === undefined ? {} : { details }),
    },
    CORRELATION,
  );
}

const KEYS = {
  priceLists: queryKeys.optimisation.priceLists(OPT_PROJECT_UID),
  positions: queryKeys.optimisation.positions(CURRENT_PRICE_LIST, 0, POSITION_PAGE_LIMIT),
  vendorLists: queryKeys.optimisation.projectVendorLists(OPT_PROJECT_UID),
};

/** Seed a client with a loaded «Оптимизация» tab. */
export function seedLoadedOptimisation(client: QueryClient): void {
  client.setQueryData(KEYS.priceLists, { items: [...REVISIONS] });
  client.setQueryData(KEYS.positions, positionPage({ offset: 0, next_offset: 50 }));
  client.setQueryData(KEYS.vendorLists, vendorLists());
}

const noop = (): void => undefined;

/** One render of a shape: a name, an element and how to seed the client it renders under. */
export interface OptimisationShape {
  readonly name: string;
  readonly make: () => ReactElement;
  readonly seedClient?: (client: QueryClient) => void;
}

function uploadView(overrides: Partial<Parameters<typeof UploadPriceListFormView>[0]> = {}): ReactElement {
  return createElement(UploadPriceListFormView, {
    fileLabel: 'прайс-2026.csv',
    currency: 'RUB',
    precheck: null,
    pending: false,
    failure: null,
    stored: null,
    onChoose: noop,
    onCurrency: noop,
    onSubmit: noop,
    ...overrides,
  });
}

function failure(detail: string) {
  return { kind: 'validation_failed' as const, detail, correlationId: CORRELATION, errorCode: 'validation_failed' as const, retryable: false };
}

/** Every shape the tab can show, for the static renders. */
export function optimisationShapes(): readonly OptimisationShape[] {
  const tab = (roles: readonly ('expert' | 'admin')[]) => () =>
    createElement(ProjectOptimisation, { projectUid: OPT_PROJECT_UID, roles: [...roles] });
  const lists = vendorLists();
  const eom = lists.items.find((item) => item.section_code === 'EOM');
  return [
    { name: 'optimisation-loaded', make: tab(['expert', 'admin']), seedClient: seedLoadedOptimisation },
    // Nothing seeded: both reads are in flight.
    { name: 'optimisation-pending', make: tab(['expert']) },
    {
      name: 'optimisation-positions-pending',
      make: tab(['expert']),
      seedClient: (client) => {
        client.setQueryData(KEYS.priceLists, { items: [...REVISIONS] });
        client.setQueryData(KEYS.vendorLists, lists);
      },
    },
    {
      name: 'optimisation-empty',
      make: tab(['admin']),
      seedClient: (client) => {
        client.setQueryData(KEYS.priceLists, { items: [] });
        client.setQueryData(KEYS.vendorLists, lists);
      },
    },
    {
      name: 'optimisation-refused',
      make: tab(['expert']),
      seedClient: (client) => {
        seedError(client, KEYS.priceLists, optimisationApiError(503, 'dependency_unavailable'));
        seedError(client, KEYS.vendorLists, optimisationApiError(503, 'dependency_unavailable'));
      },
    },
    {
      name: 'optimisation-positions-refused',
      make: tab(['expert']),
      seedClient: (client) => {
        client.setQueryData(KEYS.priceLists, { items: [...REVISIONS] });
        seedError(client, KEYS.positions, optimisationApiError(404, 'not_found'));
        client.setQueryData(KEYS.vendorLists, lists);
      },
    },
    {
      name: 'optimisation-positions-empty-page',
      make: () => createElement(PriceListPositionsView, {
        page: positionPage({ items: [], offset: 150, next_offset: null }),
        onOffset: noop,
      }),
    },
    { name: 'upload-price-list-pending', make: () => uploadView({ pending: true }) },
    { name: 'upload-price-list-precheck', make: () => uploadView({ precheck: 'Файл пуст.' }) },
    { name: 'upload-price-list-stored', make: () => uploadView({ stored: revision() }) },
    ...Object.entries(UPLOAD_CONSTRAINT_TEXT).map(([constraint, detail]) => ({
      name: `upload-price-list-refused-${constraint}`,
      make: () => uploadView({ failure: failure(detail) }),
    })),
    {
      name: 'vendor-lists-editing-project',
      make: () => createElement(VendorListsView, {
        items: lists.items, canEditProject: true, canEditGlobal: true,
        editing: { sectionCode: 'EOM', scope: 'project' }, pending: false,
        failure: failure(VENDOR_LIST_CONFLICT_TEXT),
        onEdit: noop, onInherit: noop, onSave: noop, onCancel: noop,
      }),
    },
    {
      name: 'vendor-lists-editing-global-empty',
      make: () => createElement(VendorListsView, {
        items: lists.items, canEditProject: false, canEditGlobal: true,
        editing: { sectionCode: 'AR', scope: 'global' }, pending: false, failure: null,
        onEdit: noop, onInherit: noop, onSave: noop, onCancel: noop,
      }),
    },
    {
      name: 'vendor-lists-change-refused',
      make: () => createElement(VendorListsView, {
        items: eom === undefined ? [] : [eom], canEditProject: true, canEditGlobal: false,
        editing: null, pending: false,
        failure: failure(INHERIT_WITH_ENTRIES_TEXT),
        onEdit: noop, onInherit: noop, onSave: noop, onCancel: noop,
      }),
    },
  ];
}
