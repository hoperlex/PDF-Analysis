'use client';

/**
 * The numbers on the frame's «Блоки» and «Оптимизация» tabs (`UIP-S04-02`): both come from the one read of the version,
 * `getDocumentVersion` — `block_count` (the portal blocks of the version's built index) and the optimisation counts of its
 * `audit` (the proposals of the version's latest pass, and those with no decision in force). There is no second source: the
 * frame's former read of the document's passes is gone, so the two numbers cannot disagree with each other or with the
 * version they sit on, and a change of version changes them together with the tabs.
 *
 * **The key.** The read is filed under `queryKeys.versions.detail`, the entry the version page, the frame's own name read and
 * every command that writes a version already share, so a cold page asks once. The entity's reader keeps that entry for ever
 * because a published version is immutable; these two figures are not (a run builds the blocks, a decision empties the
 * undecided count), so this observer asks for a fresh read on every mount (`staleTime: 0`) and keeps whatever is in the entry
 * until the answer comes. A page that holds its version from a listing (the document's page) has no audit and no block
 * count in it, which is why the frame reads the version for the figures even when it does not need it for the names.
 *
 * **No number is no number**: while the read is pending, after it failed with nothing to show, and for a figure the server
 * did not give, the result is `undefined` / absent and the tab says nothing, never a zero.
 */

import { useQuery } from '@tanstack/react-query';

import type { DocumentVersion, VersionUid } from '@/shared/api';
import { getDocumentVersion, queryKeys } from '@/shared/api';

import type { VersionFigures } from '../model/version-tabs';
import { versionFigures } from '../model/version-tabs';

export function useVersionFigures(versionUid: string | undefined): VersionFigures | undefined {
  const known = versionUid !== undefined && versionUid !== '';
  const query = useQuery<DocumentVersion, Error, VersionFigures>({
    queryKey: queryKeys.versions.detail((versionUid ?? '') as VersionUid),
    enabled: known,
    staleTime: 0,
    queryFn: async () => (await getDocumentVersion({ path: { version_uid: versionUid ?? '' } })).data,
    select: versionFigures,
  });
  return known ? query.data : undefined;
}
