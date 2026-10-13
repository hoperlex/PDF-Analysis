/**
 * Portal blocks for the «Блоки» tests and for the instruments that render the screen
 * (`W55B-WEB-BLOCKS`): the language guard and the contrast census import these, so the
 * blocks they measure are the blocks the unit tests assert on.
 *
 * Synthetic throughout. Every member a `PortalBlock` can carry appears on some block here:
 * each of the three types, both geometry verdicts, a polygon, a crop, a recognised text with
 * every flag the backend emits today plus one it does not, a description, a status the
 * portal is known to send and one it is not, a page whose portal label differs, and a stamp
 * with no ordinal.
 */

import type { DocumentVersion, PortalBlock, PortalBlockPage } from '@/shared/api';

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
export const BLOCKS_PROJECT_UID = `prj_${ULID}`;
export const BLOCKS_VERSION_UID = `ver_${ULID}`;
export const BLOCKS_RUN_ID = `run_${ULID}`;

/** `blk_` and 32 lowercase hexadecimal digits, distinct per `n`. */
export function blockId(n: number): string {
  return `blk_${n.toString(16).padStart(32, '0')}`;
}

export function textBlock(over: Partial<PortalBlock> = {}): PortalBlock {
  return {
    portal_block_id: blockId(1),
    page_number: 1,
    page_label: 1,
    ordinal: 1,
    block_type: 'text',
    status: 'recognized',
    bbox_norm: [0.1, 0.1, 0.9, 0.3],
    geometry: 'ok',
    recognised_text: { quote_source: 'recognised', text: 'Пояснительная записка. Раздел 1.', flags: [] },
    ...over,
  };
}

export function imageBlock(over: Partial<PortalBlock> = {}): PortalBlock {
  return {
    portal_block_id: blockId(2),
    page_number: 1,
    page_label: 1,
    ordinal: 2,
    block_type: 'image',
    status: 'recognized',
    bbox_norm: [0.1, 0.4, 0.9, 0.8],
    geometry: 'ok',
    crop: {
      media_type: 'image/png',
      width_px: 1177,
      height_px: 593,
      sha256: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
    },
    portal_description: 'План первого этажа с осями А–Г и 1–4.',
    ...over,
  };
}

export function stampBlock(over: Partial<PortalBlock> = {}): PortalBlock {
  return {
    portal_block_id: blockId(3),
    page_number: 1,
    page_label: 1,
    ordinal: null,
    block_type: 'stamp',
    status: 'recognized',
    bbox_norm: [0.6, 0.85, 0.98, 0.98],
    geometry: 'ok',
    ...over,
  };
}

/** The flag vocabulary `analysis/recognised/flags.py` emits, in its order. */
export const KNOWN_FLAGS = [
  'mixed_script',
  'homoglyph',
  'cjk',
  'doubled_list_marker',
  'degenerate_instruction_echo',
  'degenerate_first_person_plan',
  'degenerate_page_narration',
  'degenerate_serialised_payload',
  'empty_text',
] as const;

/** A flag the backend does not emit today: the screen must not print it. */
export const UNKNOWN_FLAG_TOKEN = 'future_quality_signal';

/** A portal status the screen does not know: the screen must not print it. */
export const UNKNOWN_STATUS_TOKEN = 'partially_recognised';

/** One block of each kind the screen distinguishes, across three pages. */
export function everyKindOfBlock(): PortalBlock[] {
  return [
    textBlock({
      recognised_text: {
        quote_source: 'recognised',
        text: 'Уровень пола — 0.000\n- - пункт списка\nкажд梯й',
        flags: [...KNOWN_FLAGS, UNKNOWN_FLAG_TOKEN],
      },
    }),
    imageBlock({ polygon_points: [[0.1, 0.4], [0.9, 0.4], [0.9, 0.8], [0.1, 0.8]] }),
    stampBlock(),
    textBlock({ portal_block_id: blockId(4), page_number: 2, page_label: 5, ordinal: 1, status: 'failed' }),
    omit(
      textBlock({ portal_block_id: blockId(5), page_number: 2, page_label: 5, ordinal: 2, status: UNKNOWN_STATUS_TOKEN }),
      'recognised_text',
    ),
    omit(
      imageBlock({ portal_block_id: blockId(6), page_number: 3, page_label: 3, ordinal: 1, geometry: 'geometry_mismatch' }),
      'crop',
      'portal_description',
    ),
    stampBlock({ portal_block_id: blockId(7), page_number: 3, page_label: 3, geometry: 'geometry_mismatch' }),
  ];
}

/** The wire omits an absent member (never `null`): a fixture leaves it out the same way. */
export function omit(block: PortalBlock, ...members: (keyof PortalBlock)[]): PortalBlock {
  const copy: Partial<PortalBlock> = { ...block };
  for (const member of members) delete copy[member];
  return copy as PortalBlock;
}

export function portalPage(
  items: readonly PortalBlock[],
  over: Partial<PortalBlockPage> = {},
): PortalBlockPage {
  return {
    version_uid: BLOCKS_VERSION_UID,
    status: 'produced',
    produced_by_run_id: BLOCKS_RUN_ID,
    block_count: items.length,
    items: [...items],
    page: { next_cursor: null },
    ...over,
  };
}

export function notProducedPage(): PortalBlockPage {
  return portalPage([], { status: 'not_produced', produced_by_run_id: null, block_count: 0 });
}

/** A version as `listDocuments` answers it; `bundle` decides whether it carries a block list. */
export function blocksVersion(bundle: boolean, over: Partial<DocumentVersion> = {}): DocumentVersion {
  return {
    version_uid: BLOCKS_VERSION_UID,
    document_uid: `doc_${ULID}`,
    project_uid: BLOCKS_PROJECT_UID,
    version_ordinal: 1,
    media_type: 'application/pdf',
    byte_size: 92161,
    page_count: 3,
    sha256: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
    published_at: '2026-10-14T08:00:00Z',
    source_filename: 'ar_baseline.zip',
    input_manifest: [
      {
        role: 'source.document',
        media_type: 'application/pdf',
        sha256: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
        size_bytes: 1,
      },
      ...(bundle
        ? [
            {
              role: 'source.structured_companion',
              media_type: 'application/json',
              sha256: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
              size_bytes: 1,
            },
          ]
        : []),
    ],
    ...over,
  };
}

/** The crop address the instruments use instead of the configured one. */
export const TEST_CROP_SRC = (block: PortalBlock): string =>
  `/bff/v1/versions/${BLOCKS_VERSION_UID}/portal-blocks/${block.portal_block_id}/crop`;
