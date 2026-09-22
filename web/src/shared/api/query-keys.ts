/**
 * Frozen React Query key namespaces.
 *
 * Two slices caching the same resource under two different keys is how a UI shows a
 * stale verdict next to a fresh one. The namespaces are fixed here, by the toolchain
 * owner, and `web/docs/PC01_UI_SEAM.md` records which Gate B session uses which.
 *
 * Rules:
 *   - every key starts with one of the four root namespaces below;
 *   - a key is built by calling a function here, never by writing an array literal;
 *   - invalidation targets a prefix — `queryKeys.runs.all()` invalidates every run key;
 *   - a key filled by more than one site carries its value type, as a `DataTag`. See
 *     `runs.detail` below.
 *
 * **What `D-57` cost, and what the tag is for.** `runs.detail` was written as a bare
 * `RunStatus` by the run screen and filed as the generated client's `{ data }` envelope
 * by the review screen, into one `QueryClient`. Neither side was a type error: an
 * explicit `getQueryData<RunStatus>(key)` *asserts* the shape instead of checking it, and
 * `useQuery` takes its shape from its own `queryFn`. The key was the only thing the two
 * sites shared and it carried no type at all, so the disagreement could only surface at
 * render time — as an empty review screen over a cached run, and as a crash on the run
 * screen when it read the envelope back.
 *
 * A `DataTag` is a phantom type on the key itself. `QueryClient.getQueryData` and
 * `.setQueryData` infer from it (`InferDataFromTag` in `@tanstack/query-core`), so the
 * shape stops being a convention in a comment and becomes the compiler's business.
 *
 * **It does not reach `useQuery`.** In `@tanstack/react-query` 5.102.8 — measured, not
 * assumed: `InferDataFromTag` appears nowhere in that package's build — `useQuery` infers
 * `TQueryFnData` from the `queryFn` and ignores the tag on the key. So the one filling
 * route the compiler cannot police is a `useQuery` over this key, and that is exactly the
 * route the review screen took. `web/tests/guards/query-key-shape.guard.test.ts` closes
 * it: there is one query-options factory for this key and no other site may pass it as a
 * `queryKey`.
 */

import type { DataTag } from '@tanstack/react-query';

import type {
  DocumentUid,
  FindingCategory,
  FindingUid,
  ProjectUid,
  RunId,
  RunStatus,
  Verdict,
  VersionUid,
} from './generated/types.gen';

/** The four root namespaces. Nothing else is a legal first key segment. */
export const QUERY_NAMESPACES = ['projects', 'versions', 'runs', 'findings'] as const;

export type QueryNamespace = (typeof QUERY_NAMESPACES)[number];

/** Filters that make a finding list a distinct cache entry. */
export interface FindingListFilters {
  readonly category?: FindingCategory;
  readonly verdict?: Verdict;
  readonly cursor?: string;
  readonly limit?: number;
}

export const queryKeys = {
  projects: {
    all: () => ['projects'] as const,
    list: (cursor?: string, limit?: number) => ['projects', 'list', { cursor, limit }] as const,
    detail: (projectUid: ProjectUid) => ['projects', 'detail', projectUid] as const,
    /**
     * One page of `listDocuments` for one project.
     *
     * Filed under `projects` and not under `versions` even though the items are
     * `DocumentVersion`s, because the *question* is "what is in this project" and the
     * answer changes when the project gains a document. `uploadDocument` already
     * invalidates `projects.detail(project_uid)`; a key under `versions` would not be
     * reached by that invalidation and the screen would show a stale project.
     */
    documents: (projectUid: ProjectUid, cursor?: string, limit?: number) =>
      ['projects', 'documents', projectUid, { cursor, limit }] as const,
  },
  versions: {
    all: () => ['versions'] as const,
    detail: (versionUid: VersionUid) => ['versions', 'detail', versionUid] as const,
    content: (versionUid: VersionUid) => ['versions', 'content', versionUid] as const,
    /** One page of `listVersions` for one document. */
    list: (documentUid: DocumentUid, cursor?: string, limit?: number) =>
      ['versions', 'list', documentUid, { cursor, limit }] as const,
  },
  runs: {
    all: () => ['runs'] as const,
    /**
     * One run's status. Holds the **model**, never the transport envelope.
     *
     * Chosen over the envelope because every consumer wants a run: the poller writes
     * readings, `useStartRun` writes the 202 body, the run screen reads `.state` and the
     * review screen reads `.provider_mode`. Nothing reads `status` or `correlationId`
     * off this entry. The envelope is a property of one call, not of the resource, and
     * `versions.detail` had already settled the same question the same way —
     * `useDocumentVersion` unwraps in its `queryFn` and `useUploadDocument` writes the
     * bare model. `runs.detail` was the one key that departed from it.
     *
     * The tag is what makes that a fact about the key rather than about its callers:
     * `setQueryData(queryKeys.runs.detail(id), envelope)` no longer compiles.
     */
    detail: (runId: RunId) =>
      ['runs', 'detail', runId] as const as DataTag<readonly ['runs', 'detail', RunId], RunStatus>,
    /**
     * One page of `listRuns` for one version. Under `runs` so that
     * `queryKeys.runs.all()` — which `startRun` reaches for — invalidates the listing
     * that a new run has just changed.
     */
    list: (versionUid: VersionUid, cursor?: string, limit?: number) =>
      ['runs', 'list', versionUid, { cursor, limit }] as const,
    findings: (runId: RunId, filters: FindingListFilters = {}) =>
      ['runs', 'findings', runId, filters] as const,
  },
  findings: {
    all: () => ['findings'] as const,
    detail: (findingUid: FindingUid) => ['findings', 'detail', findingUid] as const,
    decisions: (findingUid: FindingUid) => ['findings', 'decisions', findingUid] as const,
  },
} as const;
