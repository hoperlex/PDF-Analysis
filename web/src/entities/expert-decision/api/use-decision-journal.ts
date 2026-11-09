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
 *
 * `useDecisionVerdictTotals` (`UI-B-32`) is the same listing read for its `total` alone: one page of one
 * record per verdict, so the numbers on the knowledge base's verdict chips are the server's counts over every page.
 */

import { useQueries, useQuery } from '@tanstack/react-query';

import type { DecisionRecordPage, FindingCategory, KnowledgeBaseEntryPage, ProjectUid, ProposalDecisionRecordPage, Verdict } from '@/shared/api';
import { listDecisions, listKnowledgeBaseEntries, listProposalDecisionJournal, queryKeys } from '@/shared/api';

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

/**
 * `UI-B-32`: how many journal entries each verdict chip stands for -- «Принято», «Отклонено», «Не решено» and «Все».
 *
 * The server counts: each number is the `total` of `listDecisions` for that verdict, read with `limit=1` so a page
 * carries one record and the count carries the whole journal. The numbers follow the other two filters of the screen --
 * the project and the category -- because a chip beside a list that those two narrow would otherwise count a
 * different set than the list holds. They never follow the verdict itself: a chip's number is its own verdict's.
 *
 * A read that has not answered, or failed, is `undefined` and drawn as no number; it is never a zero nobody read. The
 * four reads are cached under `queryKeys.findings.journal`, so an accepted decision (`decisionCacheKeys`) refreshes
 * them with the list.
 */
export interface DecisionVerdictTotals {
  readonly accepted: number | undefined;
  readonly rejected: number | undefined;
  readonly pending: number | undefined;
  readonly all: number | undefined;
}

/** The verdicts a chip counts, in the order the chips are drawn; `undefined` is the read with no verdict filter. */
const TOTALS_VERDICTS: readonly (Verdict | undefined)[] = ['accepted', 'rejected', 'pending', undefined];

export function useDecisionVerdictTotals({ category, project_uid }: Pick<DecisionJournalQuery, 'category' | 'project_uid'> = {}, enabled = true): DecisionVerdictTotals {
  const totals = useQueries({
    queries: TOTALS_VERDICTS.map((verdict) => {
      const filters = {
        ...(project_uid === undefined ? {} : { project_uid }),
        ...(category === undefined ? {} : { category }),
        ...(verdict === undefined ? {} : { verdict }),
        limit: 1,
      };
      return {
        queryKey: queryKeys.findings.journal(filters),
        queryFn: async (): Promise<DecisionRecordPage> => (await listDecisions({ query: filters })).data,
        enabled,
      };
    }),
  });
  return {
    accepted: totals[0]?.data?.total,
    rejected: totals[1]?.data?.total,
    pending: totals[2]?.data?.total,
    all: totals[3]?.data?.total,
  };
}

/**
 * `R-151h`: the knowledge base's «Предложения» half -- every decision on an optimisation proposal, newest first, one
 * page, optionally of one project. The same cursor discipline as the findings journal.
 */
export function useProposalDecisionJournal({ project_uid, cursor }: { readonly project_uid?: ProjectUid | undefined; readonly cursor?: string | undefined } = {}, enabled = true) {
  const filters = {
    ...(project_uid === undefined ? {} : { project_uid }),
    ...(cursor === undefined ? {} : { cursor }),
    limit: JOURNAL_PAGE_LIMIT,
  };
  return useQuery<ProposalDecisionRecordPage>({
    queryKey: queryKeys.findings.proposalJournal(filters),
    queryFn: async () => (await listProposalDecisionJournal({ query: filters })).data,
    enabled,
  });
}

/**
 * `D-317`: the knowledge base's «Все» -- the decisions on findings and on optimisation proposals as one journal, newest
 * first, one page, optionally of one project. Each entry names its kind and carries that journal's own record.
 */
export function useKnowledgeBaseJournal({ project_uid, cursor }: { readonly project_uid?: ProjectUid | undefined; readonly cursor?: string | undefined } = {}, enabled = true) {
  const filters = {
    ...(project_uid === undefined ? {} : { project_uid }),
    ...(cursor === undefined ? {} : { cursor }),
    limit: JOURNAL_PAGE_LIMIT,
  };
  return useQuery<KnowledgeBaseEntryPage>({
    queryKey: queryKeys.findings.knowledgeBase(filters),
    queryFn: async () => (await listKnowledgeBaseEntries({ query: filters })).data,
    enabled,
  });
}
