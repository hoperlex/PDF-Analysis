'use client';

/**
 * The price-list upload command (`W60-PRICE-LIST-01`).
 *
 * One CSV or Excel file, sent by the generated client as `uploadPriceList`'s
 * `multipart/form-data` body with the intent's `Idempotency-Key`; nothing here builds a
 * `FormData`, a URL or a boundary. On success the project's revision list is asked again
 * (a new current revision), and nothing else: a price list changes no number the dashboard
 * reads.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { PriceListRevision, ProjectUid, UploadPriceListRequest } from '@/shared/api';
import { queryKeys, uploadPriceList } from '@/shared/api';

export interface UploadPriceListCommand {
  readonly projectUid: ProjectUid;
  readonly file: File;
  /** An ISO 4217 code for rows whose currency the file does not state; `null` for none. */
  readonly defaultCurrency: string | null;
  /** Minted once per intent by the caller and reused on every retry. */
  readonly idempotencyKey: string;
}

export function useUploadPriceList() {
  const queryClient = useQueryClient();

  return useMutation<PriceListRevision, unknown, UploadPriceListCommand>({
    mutationFn: async ({ projectUid, file, defaultCurrency, idempotencyKey }) => {
      const body: UploadPriceListRequest =
        defaultCurrency === null ? { file } : { file, default_currency: defaultCurrency };
      const response = await uploadPriceList({
        path: { project_uid: projectUid },
        body,
        idempotencyKey,
      });
      return response.data;
    },
    onSuccess: (revision) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.optimisation.priceLists(revision.project_uid),
      });
      // The new revision is the project's current one: every price in «Спецификация и цены»
      // (`W60-OPT-MATCH-01`) was read from the previous one.
      void queryClient.invalidateQueries({
        queryKey: queryKeys.optimisation.specificationPricesAll(revision.project_uid),
      });
    },
  });
}
