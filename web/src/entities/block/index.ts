/**
 * Public API of the `block` entity: a version's portal blocks as the «Блоки» screen reads
 * them (`W55B-WEB-BLOCKS`). The text-line index (`getVersionBlocks`) stays local to the
 * page that alone reads it.
 */

export { PORTAL_BLOCK_PAGE_LIMIT, portalBlocksQueryOptions, usePortalBlocks } from './api/use-portal-blocks';
export { sheetOfPage, useSheetLabels } from './api/use-sheet-labels';
export { runFindingBlocksQueryOptions, useRunFindingBlocks } from './api/use-run-finding-blocks';
export { blocksOfFinding, findingBlockIndex } from './model/finding-blocks';
export type { FindingBlockIndex } from './model/finding-blocks';
export { hasMeaningfulContent } from './model/content';
export { PORTAL_BLOCK_LIST_ROLE, versionHasPortalBundle } from './model/bundle';
export {
  blocksOfSelection,
  effectiveSelection,
  loadedPortalBlocks,
  nextPortalCursor,
  pageChips,
  pageSelectionOf,
  pageSelectionParam,
  sectionsByPage,
  sectionsOfSelection,
  stepIndex,
} from './model/pages';
export type { PageChip, PageSelection, PortalPageSection } from './model/pages';
export { TILE_EXCERPT_LIMIT, textExcerpt } from './model/excerpt';
export {
  MAX_ZOOM,
  MIN_ZOOM,
  WHEEL_IN,
  WHEEL_OUT,
  WHOLE_IMAGE,
  clampView,
  isZoomed,
  panBy,
  viewTransform,
  wheelZoom,
  zoomAround,
  zoomLabel,
} from './model/image-view';
export type { Point, Size, View } from './model/image-view';
export {
  DESCRIPTION_MARKER,
  GEOMETRY_MISMATCH_LABEL,
  PORTAL_BLOCK_TYPE_LABELS,
  RECOGNISED_FLAGS,
  RECOGNISED_MARKER,
  UNKNOWN_BLOCK_TYPE_LABEL,
  UNKNOWN_FLAG,
  UNKNOWN_PORTAL_STATUS,
  flagPresentation,
  geometryLabel,
  portalBlockTypeLabel,
  portalStatusPresentation,
} from './model/vocabulary';
export type { FlagPresentation, PortalStatusPresentation } from './model/vocabulary';
