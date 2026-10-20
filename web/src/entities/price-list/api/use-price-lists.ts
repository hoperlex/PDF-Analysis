'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import type {
  EffectiveVendorLists,
  PriceListId,
  PriceListPositionPage,
  PriceListRevisionList,
  ProjectUid,
} from '@/shared/api';
import {
  getEffectiveVendorLists,
  listPriceListPositions,
  listPriceListRevisions,
  queryKeys,
} from '@/shared/api';

/** Positions per page on the «Оптимизация» tab; the contract allows up to 500. */
export const POSITION_PAGE_LIMIT = 50;

/**
 * `listPriceListRevisions` (`W60-PRICE-LIST-01`): every revision of one project's price list,
 * newest first, the first one current. One read, no paging.
 */
export function priceListRevisionsQueryOptions(projectUid: ProjectUid) {
  return {
    queryKey: queryKeys.optimisation.priceLists(projectUid),
    queryFn: async () => (await listPriceListRevisions({ path: { project_uid: projectUid } })).data,
  } as const;
}

export function usePriceListRevisions(projectUid: ProjectUid) {
  return useQuery<PriceListRevisionList>(priceListRevisionsQueryOptions(projectUid));
}

/** One page of `listPriceListPositions`, with the revision and its parse report. */
export function priceListPositionsQueryOptions(
  priceListId: PriceListId,
  offset: number,
  limit: number = POSITION_PAGE_LIMIT,
) {
  return {
    queryKey: queryKeys.optimisation.positions(priceListId, offset, limit),
    queryFn: async () =>
      (await listPriceListPositions({ path: { price_list_id: priceListId }, query: { offset, limit } }))
        .data,
  } as const;
}

export function usePriceListPositions(priceListId: PriceListId | null, offset: number) {
  return useQuery<PriceListPositionPage>({
    ...priceListPositionsQueryOptions(priceListId ?? '', offset),
    enabled: priceListId !== null,
    // Paging keeps the page on screen until the next one arrives.
    placeholderData: keepPreviousData,
  });
}

/** `getEffectiveVendorLists`: the fifteen sections' vendor lists as they apply to a project. */
export function effectiveVendorListsQueryOptions(projectUid: ProjectUid) {
  return {
    queryKey: queryKeys.optimisation.projectVendorLists(projectUid),
    queryFn: async () => (await getEffectiveVendorLists({ path: { project_uid: projectUid } })).data,
  } as const;
}

export function useEffectiveVendorLists(projectUid: ProjectUid) {
  return useQuery<EffectiveVendorLists>(effectiveVendorListsQueryOptions(projectUid));
}
