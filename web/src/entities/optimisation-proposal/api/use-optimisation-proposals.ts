'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import type {
  DocumentUid,
  OptimisationPassId,
  OptimisationPassList,
  OptimisationProposalId,
  OptimisationProposalPage,
  ProjectUid,
  ProposalDecisionList,
  ProposalDecisionState,
} from '@/shared/api';
import {
  listOptimisationPasses,
  listOptimisationProposals,
  listProposalDecisions,
  queryKeys,
} from '@/shared/api';

/** Proposals per page on the «Оптимизация» tab; the contract allows up to 200. */
export const PROPOSAL_PAGE_LIMIT = 20;

/**
 * `listOptimisationPasses` (`W60-OPT-PROPOSALS-01`): a project's passes for one document set,
 * newest first, each with its counts by decision. One read, no paging (at most 100).
 */
export function optimisationPassesQueryOptions(projectUid: ProjectUid, documentUid: DocumentUid | null) {
  return {
    queryKey: queryKeys.optimisation.passes(projectUid, documentUid),
    queryFn: async () =>
      (
        await listOptimisationPasses({
          path: { project_uid: projectUid },
          ...(documentUid === null ? {} : { query: { document_uid: documentUid } }),
        })
      ).data,
  } as const;
}

export function useOptimisationPasses(projectUid: ProjectUid, documentUid: DocumentUid | null) {
  return useQuery<OptimisationPassList>({
    ...optimisationPassesQueryOptions(projectUid, documentUid),
    enabled: documentUid !== null,
  });
}

/** One page of `listOptimisationProposals`, with the pass and its counts by decision. */
export function optimisationProposalsQueryOptions(
  passId: OptimisationPassId,
  decision: ProposalDecisionState | null,
  offset: number,
  limit: number = PROPOSAL_PAGE_LIMIT,
) {
  return {
    queryKey: queryKeys.optimisation.proposals(passId, decision, offset, limit),
    queryFn: async () =>
      (
        await listOptimisationProposals({
          path: { optimisation_pass_id: passId },
          query: { offset, limit, ...(decision === null ? {} : { decision }) },
        })
      ).data,
  } as const;
}

export function useOptimisationProposals(
  passId: OptimisationPassId | null,
  decision: ProposalDecisionState | null,
  offset: number,
) {
  return useQuery<OptimisationProposalPage>({
    ...optimisationProposalsQueryOptions(passId ?? '', decision, offset),
    enabled: passId !== null,
    // Paging and filtering keep the page on screen until the next one arrives.
    placeholderData: keepPreviousData,
  });
}

/** `listProposalDecisions`: one proposal's append-only history, read only when asked for. */
export function proposalDecisionsQueryOptions(proposalId: OptimisationProposalId) {
  return {
    queryKey: queryKeys.optimisation.proposalDecisions(proposalId),
    queryFn: async () =>
      (await listProposalDecisions({ path: { optimisation_proposal_id: proposalId } })).data,
  } as const;
}

export function useProposalDecisions(proposalId: OptimisationProposalId, enabled: boolean) {
  return useQuery<ProposalDecisionList>({ ...proposalDecisionsQueryOptions(proposalId), enabled });
}
