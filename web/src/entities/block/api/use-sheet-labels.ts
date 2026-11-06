'use client';

/**
 * A version's pages with their drawing sheets (`listVersionSheetLabels`, contract 1.30.0, `UI-PARITY-P0O`).
 *
 * The original shows a finding's «Лист» beside its PDF page; the sheet is the label the portal's blocks of that page
 * carry. One read per version, kept as the portal blocks are: the geometry belongs to the version and changes only when
 * a run first produces it.
 */

import { useQuery } from '@tanstack/react-query';

import type { VersionSheetLabelList, VersionUid } from '@/shared/api';
import { listVersionSheetLabels, queryKeys } from '@/shared/api';

export function useSheetLabels(versionUid: string | null) {
  return useQuery<VersionSheetLabelList>({
    queryKey: queryKeys.versions.sheetLabels((versionUid ?? '') as VersionUid),
    enabled: versionUid !== null && versionUid !== '',
    queryFn: async () => (await listVersionSheetLabels({ path: { version_uid: versionUid as VersionUid } })).data,
  });
}

/** The sheet of a PDF page, or `undefined` when the portal named none (never the page number itself). */
export function sheetOfPage(labels: VersionSheetLabelList | undefined, page: number): number | undefined {
  return labels?.items.find((item) => item.page_number === page)?.page_label;
}
