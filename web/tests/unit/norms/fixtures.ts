/**
 * `W55A-WEB-NORMS` — norms values the screen tests and the two instruments (the language
 * guard and the contrast census) seed. Cyrillic, or an identity, or a digest, like every
 * value those instruments seed: a Latin word here would read as English on a screen.
 */

import type {
  NormDocument, NormParagraph, NormSearchHit, NormSnapshot, NormSnapshotEvent,
} from '@/shared/api';

import { NORM_DOCUMENT_ID } from '../screens/route-screens';

export { NORM_DOCUMENT_ID, NORM_PAGE, NORM_QUERY } from '../screens/route-screens';

export const CURRENT_SNAPSHOT_ID = 'ns_01J9ZQ8K7NHVXW3T2R5M6P4Q8A';
export const QUALIFIED_SNAPSHOT_ID = 'ns_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
export const INCOMPLETE_SNAPSHOT_ID = 'ns_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
export const UNBOUND_SNAPSHOT_ID = 'ns_01J9ZQ8K7NHVXW3T2R5M6P4Q8E';
export const ADMIN_UID = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

export function normSnapshot(over: Partial<NormSnapshot> = {}): NormSnapshot {
  return {
    norms_snapshot_id: CURRENT_SNAPSHOT_ID,
    content_key: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
    document_count: 674,
    paragraph_count: 191204,
    unreliable_count: 312,
    build_state: 'complete',
    qualified: true,
    current: true,
    created_at: '2026-10-10T08:00:00Z',
    ...over,
  };
}

/** The current snapshot, a qualifying one, one without a complete index, one with an unbound PDF. */
export const NORM_SNAPSHOTS: readonly NormSnapshot[] = [
  normSnapshot(),
  normSnapshot({
    norms_snapshot_id: QUALIFIED_SNAPSHOT_ID,
    content_key: '1f0e9d8c7b6a5948b726150413021100aabbccddeeff00112233445566778899',
    current: false,
    created_at: '2026-10-11T08:00:00Z',
  }),
  normSnapshot({
    norms_snapshot_id: INCOMPLETE_SNAPSHOT_ID,
    content_key: '2f0e9d8c7b6a5948b726150413021100aabbccddeeff00112233445566778899',
    current: false,
    qualified: false,
    build_state: 'incomplete',
    created_at: '2026-10-12T08:00:00Z',
  }),
  normSnapshot({
    norms_snapshot_id: UNBOUND_SNAPSHOT_ID,
    content_key: '3f0e9d8c7b6a5948b726150413021100aabbccddeeff00112233445566778899',
    current: false,
    qualified: false,
    created_at: '2026-10-12T09:00:00Z',
  }),
];

export const NORM_EVENTS: readonly NormSnapshotEvent[] = [
  {
    event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
    from_norms_snapshot_id: QUALIFIED_SNAPSHOT_ID,
    to_norms_snapshot_id: CURRENT_SNAPSHOT_ID,
    actor_user_uid: ADMIN_UID,
    changed_at: '2026-10-12T10:00:00Z',
  },
  {
    event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
    from_norms_snapshot_id: null,
    to_norms_snapshot_id: QUALIFIED_SNAPSHOT_ID,
    actor_user_uid: ADMIN_UID,
    changed_at: '2026-10-11T10:00:00Z',
  },
];

export const NORM_HITS: readonly NormSearchHit[] = [
  {
    norms_snapshot_id: CURRENT_SNAPSHOT_ID,
    norm_document_id: NORM_DOCUMENT_ID,
    norm_paragraph_id: 'npar_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
    designation: 'СП 54.13330.2022',
    title: 'Здания жилые многоквартирные',
    doc_type: 'СП',
    clause_number: '5.1',
    page_label: 12,
    block_ref: 'стр12-абз3',
    fragment: {
      text: 'Высота жилых помещений от пола до потолка должна быть не менее 2,5 м.',
      highlights: [{ char_start: 0, char_end: 6 }, { char_start: 13, char_end: 22 }],
    },
    source_attribution: 'consultant_plus',
  },
  {
    norms_snapshot_id: CURRENT_SNAPSHOT_ID,
    norm_document_id: NORM_DOCUMENT_ID,
    norm_paragraph_id: 'npar_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
    designation: 'СП 54.13330.2022',
    title: 'Здания жилые многоквартирные',
    doc_type: 'СП',
    clause_number: null,
    page_label: 13,
    block_ref: 'стр13-абз1',
    fragment: { text: 'Высоту помещений мансардного этажа допускается принимать меньшей.', highlights: [] },
    source_attribution: 'unattributed',
  },
];

export function normDocument(over: Partial<NormDocument> = {}): NormDocument {
  return {
    norm_document_id: NORM_DOCUMENT_ID,
    norms_snapshot_id: CURRENT_SNAPSHOT_ID,
    designation: 'СП 54.13330.2022',
    title: 'Здания жилые многоквартирные',
    doc_type: 'СП',
    drawn_on: '2022-05-13',
    pdf_page_count: 48,
    paragraph_count: 412,
    unreliable_paragraph_count: 1,
    content_available: true,
    source_attribution: 'consultant_plus',
    ...over,
  };
}

export const NORM_PARAGRAPHS: readonly NormParagraph[] = [
  {
    norm_paragraph_id: 'npar_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
    ordinal: 0,
    page_label: 12,
    block_ref: 'стр12-абз1',
    kind: 'heading',
    clause_number: '5',
    text: 'Требования к помещениям',
    text_reliability: 'reliable',
  },
  {
    norm_paragraph_id: 'npar_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
    ordinal: 1,
    page_label: 12,
    block_ref: 'стр12-абз3',
    kind: 'body',
    clause_number: '5.1',
    text: 'Высота жилых помещений от пола до потолка должна быть не менее 2,5 м.',
    text_reliability: 'reliable',
  },
  {
    norm_paragraph_id: 'npar_01J9ZQ8K7NHVXW3T2R5M6P4Q8D',
    ordinal: 2,
    page_label: 14,
    block_ref: 'стр14-абз2',
    kind: 'table_row',
    clause_number: null,
    text: 'Тнблица 5.1 — Плсщади пом..щений',
    text_reliability: 'unreliable',
  },
];
