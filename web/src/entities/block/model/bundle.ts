/**
 * Whether a published version came from a portal bundle.
 *
 * `listVersionPortalBlocks` answers `not_produced` for two different versions, and the
 * screen must not say the same thing about both (`W55B-GEOMETRY-01` §5 item 4): a bundle no
 * run has reached yet, whose blocks WILL appear after its first run, and a version published
 * before W55b as a bare PDF, which has no portal blocks and never will — its runs produce no
 * portal geometry at all. The version's own manifest tells them apart: a bundle publishes its
 * block list under the role `source.structured_companion` (`documents/models.py`, the stage
 * registry's declared input), and a bare PDF publishes none.
 */

import type { DocumentVersion } from '@/shared/api';

export const PORTAL_BLOCK_LIST_ROLE = 'source.structured_companion';

export function versionHasPortalBundle(version: Pick<DocumentVersion, 'input_manifest'>): boolean {
  return version.input_manifest.some((entry) => entry.role === PORTAL_BLOCK_LIST_ROLE);
}
