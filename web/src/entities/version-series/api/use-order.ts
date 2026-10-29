'use client';

/**
 * The order in which the versions of a document set are compared (`listComparisonVersionOrders`,
 * `appendComparisonVersionOrder`). The order never changes the documents' ordinal that runs and finding
 * carry-over use (ADR-0025 decision 16, `D-5`): it only says which version follows which in a comparison.
 */

import { useQuery } from '@tanstack/react-query';

import type { ComparisonVersionOrder, DocumentUid, ProjectUid, VersionUid } from '@/shared/api';
import { appendComparisonVersionOrder, listComparisonVersionOrders } from '@/shared/api';

import { COMPARISON_KEYS } from './keys';
import { useKeyedCommand } from './use-keyed-command';

/** The newest revision of the order, or `null` when the document set compares in its own order. */
export function useLatestOrder(projectUid: ProjectUid, documentUid: DocumentUid | null) {
  return useQuery<ComparisonVersionOrder | null>({
    queryKey: COMPARISON_KEYS.orders(projectUid, documentUid ?? 'none'),
    queryFn: async () => {
      const page = (
        await listComparisonVersionOrders({
          path: { project_uid: projectUid, document_uid: documentUid as DocumentUid },
          query: { limit: 1 },
        })
      ).data;
      return page.items[0] ?? null;
    },
    enabled: documentUid !== null,
    retry: false,
  });
}

export interface AppendOrderCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  /** The latest revision the reader saw (`0` for none). */
  readonly baseRevisionNo: number;
  readonly versionUids: readonly VersionUid[];
}

export function useAppendOrder() {
  return useKeyedCommand<AppendOrderCommand, ComparisonVersionOrder>({
    signatureOf: (command) =>
      ['order', command.projectUid, command.documentUid, command.baseRevisionNo, command.versionUids.join(',')].join('|'),
    send: async (command, idempotencyKey) =>
      (
        await appendComparisonVersionOrder({
          path: { project_uid: command.projectUid, document_uid: command.documentUid },
          body: { base_revision_no: command.baseRevisionNo, version_uids: [...command.versionUids] },
          idempotencyKey,
        })
      ).data,
  });
}
