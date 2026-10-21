'use client';

/**
 * The two vendor-list commands (`W60-PRICE-LIST-01`): an expert's list for one project and
 * section, and an administrator's global list for a section.
 *
 * Each sends the revision the screen showed as `expected_vendor_list_id` (`null` when there
 * was none), so a list somebody else changed meanwhile is refused (`409`) instead of
 * overwritten. Settled either way, every project's vendor lists are asked again — a global
 * change moves all of them — and nothing the dashboard reads changes.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type {
  ProjectSection,
  ProjectUid,
  SectionVendorList,
  VendorListEntry,
  VendorListMode,
  VendorListRevision,
} from '@/shared/api';
import { queryKeys, setGlobalVendorList, setProjectVendorList } from '@/shared/api';

export interface SetProjectVendorListCommand {
  readonly projectUid: ProjectUid;
  readonly sectionCode: ProjectSection;
  readonly mode: VendorListMode;
  readonly entries: readonly VendorListEntry[];
  /** The project revision the screen showed, `null` when it showed none. */
  readonly expectedVendorListId: string | null;
}

export interface SetGlobalVendorListCommand {
  readonly sectionCode: ProjectSection;
  readonly entries: readonly VendorListEntry[];
  /** The global revision the screen showed, `null` when it showed none. */
  readonly expectedVendorListId: string | null;
}

export function useSetProjectVendorList() {
  const queryClient = useQueryClient();
  return useMutation<SectionVendorList, unknown, SetProjectVendorListCommand>({
    mutationFn: async ({ projectUid, sectionCode, mode, entries, expectedVendorListId }) =>
      (
        await setProjectVendorList({
          path: { project_uid: projectUid, section_code: sectionCode },
          body: { mode, entries: [...entries], expected_vendor_list_id: expectedVendorListId },
        })
      ).data,
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.optimisation.vendorLists() });
    },
  });
}

export function useSetGlobalVendorList() {
  const queryClient = useQueryClient();
  return useMutation<VendorListRevision, unknown, SetGlobalVendorListCommand>({
    mutationFn: async ({ sectionCode, entries, expectedVendorListId }) =>
      (
        await setGlobalVendorList({
          path: { section_code: sectionCode },
          body: { entries: [...entries], expected_vendor_list_id: expectedVendorListId },
        })
      ).data,
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.optimisation.vendorLists() });
    },
  });
}
