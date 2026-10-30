/**
 * Every screen address this application has, built in one place.
 *
 * `web/docs/PC01_UI_SEAM.md` §2 froze four URLs and said *"there is no route for a
 * document version"*. That is the sentence `D-16` is about: with no address for a
 * document and no address for a version, everything below the project list could only be
 * reached by having just created it, and a reload lost it. The table there is amended by
 * this session and this module is what it is amended to.
 *
 * Why a module rather than template literals at each call site: an address that exists in
 * four places is an address that can be wrong in three of them, and the one property this
 * session has to prove — **a URL pasted into a fresh tab renders** — is a property of the
 * string. Here it can be asserted without a browser, and the browser then confirms the
 * same strings.
 *
 * Nothing here parses an identifier. Every parameter is an opaque `<prefix>_<ULID>` and is
 * interpolated as given; `version_ordinal` is never a path parameter, because the contract
 * refuses it as one.
 */

/** The `<prefix>_<ULID>` identities that appear in an address. */
export interface RouteIdentities {
  readonly projectUid: string;
  readonly documentUid: string;
  readonly versionUid: string;
  readonly runId: string;
}

/**
 * The fragment of the version screen's stage-and-section panel (`W59-SECTION-UI-01`). The
 * panel carries it as its `id`, and a run refused for its classification links to it.
 */
export const VERSION_CLASSIFICATION_ANCHOR = 'version-classification';

export const routes = {
  /** Execution journal, optionally focused on one run. */
  logs: (runId?: string): string =>
    runId === undefined ? '/logs' : `/logs?run_id=${encodeURIComponent(runId)}`,

  /** Durable execution queue. */
  queue: (): string => '/queue',

  /** «Сравнение версий»: the projects and steps of the version comparison, and the sheet matrix (`CMP-VC-UI-01`). */
  versionComparison: (): string => '/version-comparison',

  /** «Сравнение стадий»: catalog of expert-confirmed П↔Р pairs. */
  stageComparison: (): string => '/stage-comparison',

  /** The worker registry, «Исполнители» (`W54-WORKERS-WEB`). */
  workers: (): string => '/workers',

  /** «Нормы»: the search over the current norms snapshot (`W55A-WEB-NORMS`). */
  norms: (): string => '/norms',

  /**
   * One norm document, optionally opened at one page of its PDF (`W55A-WEB-NORMS`).
   *
   * The identity travels in the query rather than in a path segment. The search is the only
   * road to a norm document, and a cold walk of the application (`tests/e2e/pc01/journey`)
   * never searches, so an address with a `[norm_document_id]` segment would be one the
   * journey cannot fill; `/norms/document` with no `id` is a screen of its own that says no
   * document was chosen. `page` is the PDF's own 1-based page number (`page_label`).
   */
  normDocument: (normDocumentId: string, page?: number): string =>
    `/norms/document?id=${encodeURIComponent(normDocumentId)}` +
    (page === undefined ? '' : `&page=${page}`),
  /** The project list. The home screen at `/` links here. */
  projects: (): string => '/projects',

  /** One project: its documents, and the upload that adds one. */
  project: (projectUid: string): string => `/projects/${projectUid}`,

  /**
   * One document and its versions.
   *
   * Through this surface a document has exactly one version today, because
   * `uploadDocument` declares no `document_uid` — `W18-SEAL` §2 measured it. The address
   * still exists, because `document_uid` is a value this system hands a user: it is a
   * column of the exported CSV and a field of every `DocumentVersion` body. An identifier
   * a product prints and cannot open is the shape of `D-16`.
   */
  document: (projectUid: string, documentUid: string): string =>
    `/projects/${projectUid}/documents/${documentUid}`,

  /** One published version: its manifest, its runs, and the control that starts one. */
  version: (projectUid: string, versionUid: string): string =>
    `/projects/${projectUid}/versions/${versionUid}`,

  /**
   * The same version screen, scrolled to its stage-and-section panel. Where the run control
   * sends a reader whose run was refused because the version has no confirmed classification,
   * or because the confirmed section has no analysis profile (`W59-SECTION-UI-01`).
   */
  versionClassification: (projectUid: string, versionUid: string): string =>
    `/projects/${projectUid}/versions/${versionUid}#${VERSION_CLASSIFICATION_ANCHOR}`,

  /**
   * Two runs of one published version, side by side.
   *
   * A child of the version and not of a run, because a version is immutable: a difference
   * between two of its runs is a difference in the analysis and not in the document.
   */
  comparison: (projectUid: string, versionUid: string): string =>
    `/projects/${projectUid}/versions/${versionUid}/comparison`,

  /** One run's progress. */
  run: (projectUid: string, runId: string): string => `/projects/${projectUid}/runs/${runId}`,

  /**
   * Findings, evidence, decisions and export for one run. A child of the run and not a
   * sibling: a finding is only meaningful against the run that produced it.
   */
  review: (projectUid: string, runId: string): string =>
    `/projects/${projectUid}/runs/${runId}/review`,

  /** The account list of the administration screens. */
  users: (): string => '/admin/users',

  /** One account, addressed by its opaque identity rather than its display name. */
  user: (userUid: string): string => `/admin/users/${userUid}`,
} as const;
