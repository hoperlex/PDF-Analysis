'use client';

/**
 * The walk behind the "run activity and spend" panel.
 *
 * `R-44`'s own table: `listRuns` exists today and carries the cost fields, but it has no
 * global form — the contract's only `runs` address is `/versions/{version_uid}/runs`.
 * There is no operation that lists every run of a deployment, so the only way to answer
 * "activity and spend" without `W46-SEAL`'s aggregate is to walk what the surface already
 * offers: the first page of projects, the first page of each project's documents (each
 * one already carrying its current version — `useDocumentList`'s own header), and the
 * first page of each of those versions' runs.
 *
 * **This is the one panel of the four that is NOT a single request**, and the shape is
 * deliberately bounded rather than exhaustive: one page at each of three levels, no
 * cursor is followed past it. A deployment with more than a page of projects, or a project
 * with more than a page of documents, is under-counted here — visibly, via `moreProjects`
 * / `moreDocuments` / `moreRuns`, never silently. `W46-SEAL`'s aggregate read is what
 * deletes this walk; until it lands, a bounded and disclosed walk is the honest option
 * `R-24`'s own argument leaves on the table, not a second source of truth invented to
 * avoid saying so.
 *
 * `useQueries` (plural) rather than a fixed number of `useQuery` calls, because the
 * number of documents and versions is only known after the projects page resolves — the
 * Rules of Hooks forbid a per-item `useQuery`, and `useQueries` is the library's own
 * answer to a dynamic-length fan-out. Each query config is built by
 * `documentListQueryOptions` / `runListQueryOptions`, the same builders
 * `useDocumentList` / `useRunList` use, so this walk fills the exact cache entries those
 * single-resource hooks would — one key per (project, cursor) or (version, cursor) pair,
 * never a second key for the same question.
 */

import { useQueries } from '@tanstack/react-query';

import type { RunStatus } from '@/shared/api';
import { useProjectList } from '@/entities/project';
import { documentListQueryOptions } from '@/entities/document-version';
import { runListQueryOptions } from '@/entities/audit-run';

export interface RunActivityWalk {
  readonly isPending: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly runs: readonly RunStatus[];
  /** Projects the walk actually read — the size of the one page of `listProjects` taken. */
  readonly scannedProjectCount: number;
  /** Distinct current versions the walk found across every scanned project's documents. */
  readonly scannedVersionCount: number;
  /** `listProjects` had a further page this walk did not follow. */
  readonly moreProjects: boolean;
  /** At least one project's documents had a further page this walk did not follow. */
  readonly moreDocuments: boolean;
  /** At least one version's runs had a further page this walk did not follow. */
  readonly moreRuns: boolean;
  readonly refetch: () => void;
}

export function useRunActivityWalk(): RunActivityWalk {
  const projects = useProjectList();
  const projectItems = projects.data?.items ?? [];

  const documentQueries = useQueries({
    queries: projectItems.map((project) => documentListQueryOptions(project.project_uid)),
  });

  const documentsPending = documentQueries.some((query) => query.isPending);
  const failedDocumentQuery = documentQueries.find((query) => query.isError);
  const moreDocuments = documentQueries.some((query) => query.data?.page.next_cursor != null);

  const versionUids = [
    ...new Set(
      documentQueries.flatMap((query) => (query.data?.items ?? []).map((doc) => doc.version_uid)),
    ),
  ];

  const runQueries = useQueries({
    queries: versionUids.map((versionUid) => runListQueryOptions(versionUid)),
  });

  const runsPending = runQueries.some((query) => query.isPending);
  const failedRunQuery = runQueries.find((query) => query.isError);
  const moreRuns = runQueries.some((query) => query.data?.page.next_cursor != null);

  const runs = runQueries.flatMap((query) => query.data?.items ?? []);

  return {
    isPending: projects.isPending || documentsPending || runsPending,
    isError: projects.isError || failedDocumentQuery !== undefined || failedRunQuery !== undefined,
    error: projects.error ?? failedDocumentQuery?.error ?? failedRunQuery?.error ?? null,
    runs,
    scannedProjectCount: projectItems.length,
    scannedVersionCount: versionUids.length,
    moreProjects: (projects.data?.page.next_cursor ?? null) !== null,
    moreDocuments,
    moreRuns,
    refetch: () => {
      void projects.refetch();
    },
  };
}
