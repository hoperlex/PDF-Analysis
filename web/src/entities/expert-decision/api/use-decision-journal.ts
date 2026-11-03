'use client';

/**
 * The decision journal query — `listDecisions`, one page.
 *
 * The journal is a **projection** over the append-only ledger (`ADR-0012`), and this hook
 * is the client's window onto it and nothing more: it stores nothing, derives nothing and
 * recomputes no verdict. Everything the knowledge base shows is a property of a record the
 * server sent.
 *
 * Why there is a query here at all, rather than a walk: before `R-24` the only way to see
 * what had been decided was to list every run, list every run's findings and read each
 * finding's history — three round trips per finding, and a client that had to know every
 * identity before it could ask the question. The owner ruled for the operation.
 *
 * The cursor is opaque. It is handed back exactly as received, never parsed and never
 * constructed.
 *
 * `project_uid` (`UI-PARITY-P0A`) restricts the journal to one project; absent is «Все проекты».
 * It is one of the filters and so part of the cache key, and a cursor belongs to the filters it
 * was issued under: the caller starts again from the first page when the project changes. An
 * unknown project is not an error here: the server answers an empty page with `total: 0`.
 */

import { useQuery } from '@tanstack/react-query';

import type { DecisionRecordPage, FindingCategory, ProjectUid, Verdict } from '@/shared/api';
import { listDecisions, queryKeys } from '@/shared/api';

/** Page size. Inside the contract's 1..200 bound and equal to the contract default. */
export const JOURNAL_PAGE_LIMIT = 50;

export interface DecisionJournalQuery {
  readonly category?: FindingCategory | undefined;
  readonly verdict?: Verdict | undefined;
  readonly project_uid?: ProjectUid | undefined;
  readonly cursor?: string | undefined;
}

export function useDecisionJournal({ category, verdict, project_uid, cursor }: DecisionJournalQuery = {}) {
  const filters = {
    ...(project_uid === undefined ? {} : { project_uid }),
    ...(category === undefined ? {} : { category }),
    ...(verdict === undefined ? {} : { verdict }),
    ...(cursor === undefined ? {} : { cursor }),
    limit: JOURNAL_PAGE_LIMIT,
  };
  return useQuery<DecisionRecordPage>({
    queryKey: queryKeys.findings.journal(filters),
    queryFn: async () => {
      const response = await listDecisions({ query: filters });
      return response.data;
    },
  });
}
