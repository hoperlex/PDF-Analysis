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
 *   - invalidation targets a prefix — `queryKeys.runs.all()` invalidates every run key.
 */

import type {
  DocumentUid,
  FindingCategory,
  FindingUid,
  ProjectUid,
  RunId,
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
    detail: (runId: RunId) => ['runs', 'detail', runId] as const,
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
