/**
 * Frozen React Query key namespaces.
 *
 * Two slices caching the same resource under two different keys is how a UI shows a
 * stale verdict next to a fresh one. The namespaces are fixed here, by the toolchain
 * owner, and `web/docs/PC01_UI_SEAM.md` records which Gate B session uses which.
 *
 * Rules:
 *   - every key starts with one of the eight root namespaces below;
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
  RegistrationStatus,
  RunId,
  RunStatus,
  UserUid,
  Verdict,
  VersionUid,
} from './generated/types.gen';

/**
 * The eight root namespaces. Nothing else is a legal first key segment.
 *
 * `account`, `users` and `registrations` entered together, once, in `W50-REGISTRY-01`
 * (`W50-PLAN.md` §3.6): the signed-in account, the administrator's account list and the
 * registration requests. Later lanes add key factories inside them and no new root.
 */
export const QUERY_NAMESPACES = [
  'projects',
  'versions',
  'runs',
  'findings',
  'dashboard',
  'account',
  'users',
  'registrations',
] as const;

export type QueryNamespace = (typeof QUERY_NAMESPACES)[number];

/** Filters that make a decision journal page a distinct cache entry. */
export interface DecisionJournalFilters {
  readonly category?: FindingCategory;
  readonly verdict?: Verdict;
  readonly cursor?: string;
  readonly limit?: number;
}

/** Filters that make a page of `listUsers` a distinct cache entry. */
export interface UserListFilters {
  readonly includeArchived?: boolean;
  readonly cursor?: string;
  readonly limit?: number;
}

/** Filters that make a page of `listRegistrations` a distinct cache entry. */
export interface RegistrationListFilters {
  readonly status?: RegistrationStatus;
  readonly cursor?: string;
  readonly limit?: number;
}

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
    /**
     * `getVersionBlocks`. `W45-BLOCKS`.
     *
     * Under `versions` and not under a fifth root namespace, for the same reason
     * `content` is: the block index is a property of the version, not of any run of it
     * -- `page_geometry_extraction` carries no model and no provider reference, so its
     * output is deterministic and identical across every run that reaches it.
     */
    blocks: (versionUid: VersionUid) => ['versions', 'blocks', versionUid] as const,
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
    /**
     * One page of `listDecisions` — the decision journal across every finding.
     *
     * Under `findings` and not under a fifth root namespace, because the question it asks
     * is *what has been decided about findings* and the answer changes exactly when a
     * finding's verdict does. `decisionCacheKeys` already invalidates
     * `findings.decisions` and `findings.detail` after an append; a key outside this
     * namespace would need a fourth entry there, and the entry somebody forgets is how a
     * screen shows `accepted` in one panel and `pending` in the one beside it.
     *
     * The filters are one object, so a partial key matches every filtered journal of the
     * deployment: React Query compares query keys by deep partial equality, and
     * `['findings','journal',{}]` therefore reaches the filtered pages too.
     */
    journal: (filters: DecisionJournalFilters = {}) =>
      ['findings', 'journal', filters] as const,
  },
  /**
   * `getDashboardSummary`. `W46-WIRE`.
   *
   * Its own root namespace, and not filed under `projects`, `runs` or `findings`: it is
   * one read that aggregates across all three of those — documents per project, findings
   * by verdict, run activity and spend, documents per section — computed server-side over
   * the whole deployment. Nesting it under any one of the three would misstate which of
   * them it depends on and would still miss the other two, and this key has exactly one
   * entry today so a fourth root would not amortise the way `journal`'s comment above
   * argues `findings.journal` does not need one.
   *
   * Every mutation that changes a number this key answers for invalidates it, from its
   * own feature or entity rather than from here: `createProject`
   * (`features/create-project`, a new row in `documents_by_project`, and for the first
   * project, whether `hasProjects` is true at all — `X-6`/`Y6-a`, `W46-CLIENT`),
   * `uploadDocument` (`features/upload-document`, `documents_by_project` and
   * `section_breakdown`), `startRun` (`features/start-run`, a new row in
   * `run_activity.by_state` the moment the command is accepted) and the run-status poll's
   * terminal reading (`entities/audit-run/api/use-run-status.ts`, `run_activity.spend` and
   * the state distribution, which only settle once a run reaches a terminal state), and an
   * appended decision (`entities/expert-decision/model/cache.ts`'s `decisionCacheKeys`,
   * `findings_by_verdict`). Forgetting one is how this screen shows last month's numbers
   * after this month's upload — `web/tests/guards/dashboard-invalidation.guard.test.ts`
   * maps every mutation hook under `features/**` against this promise.
   */
  dashboard: {
    summary: () => ['dashboard', 'summary'] as const,
  },
  /**
   * `getMe`. The signed-in account as the API describes it now — its name, roles and profile
   * state. Its own root, because it belongs to no product resource: it changes when the
   * account does (`updateMyProfile`, an administrator's role change), and nothing a project,
   * run or finding does reaches it.
   */
  account: {
    all: () => ['account'] as const,
    me: () => ['account', 'me'] as const,
  },
  /**
   * `listUsers` and `getUser` — the administrator's view of the accounts (`W51`). A root of
   * its own, apart from `account`: one is *who am I*, the other is *who is there*, and an
   * administrator changing another account must not invalidate their own.
   */
  users: {
    all: () => ['users'] as const,
    list: (filters: UserListFilters = {}) => ['users', 'list', filters] as const,
    detail: (userUid: UserUid) => ['users', 'detail', userUid] as const,
  },
  /**
   * `listRegistrations` — the requests waiting for, or past, an administrator's decision
   * (`W51`; the home page's count of pending requests reads the same page). A decision
   * invalidates `registrations.all()` and, because it creates an account, `users.all()`.
   */
  registrations: {
    all: () => ['registrations'] as const,
    list: (filters: RegistrationListFilters = {}) => ['registrations', 'list', filters] as const,
  },
} as const;
