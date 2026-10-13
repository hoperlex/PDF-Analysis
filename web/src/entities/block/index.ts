/**
 * Public API of the `block` entity: a version's portal blocks as the «Блоки» screen reads
 * them (`W55B-WEB-BLOCKS`). The text-line index (`getVersionBlocks`) stays local to the
 * page that alone reads it.
 */

export { PORTAL_BLOCK_PAGE_LIMIT, portalBlocksQueryOptions, usePortalBlocks } from './api/use-portal-blocks';
export { portalBlockCropUrl } from './api/crop-url';
export { PORTAL_BLOCK_LIST_ROLE, versionHasPortalBundle } from './model/bundle';
export { loadedPortalBlocks, nextPortalCursor, sectionsByPage } from './model/pages';
export type { PortalPageSection } from './model/pages';
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
