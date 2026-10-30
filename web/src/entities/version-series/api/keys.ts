/**
 * The query keys of the version comparison.
 *
 * They live here and not in `shared/api`'s registry, as the key of the analysis presets does: the
 * comparison is read by one set of screens and written by one set of commands, and every command
 * invalidates the whole namespace (a series moves the overview, the matrix's progress and the
 * transitions at once). One root, `comparison`, so `COMPARISON_KEYS.all` is the one prefix to name.
 */

export const COMPARISON_KEYS = {
  all: ['comparison'] as const,
  overview: (projectUid: string) => ['comparison', 'overview', projectUid] as const,
  matrix: (projectUid: string, documentUid: string) => ['comparison', 'matrix', projectUid, documentUid] as const,
  edits: (projectUid: string, documentUid: string) => ['comparison', 'edits', projectUid, documentUid] as const,
  seriesList: (projectUid: string, documentUid: string) => ['comparison', 'series-list', projectUid, documentUid] as const,
  series: (seriesId: string) => ['comparison', 'series', seriesId] as const,
  pairs: (transitionId: string) => ['comparison', 'pairs', transitionId] as const,
  pair: (pairId: string) => ['comparison', 'pair', pairId] as const,
  profile: (profileId: string) => ['comparison', 'profile', profileId] as const,
  orders: (projectUid: string, documentUid: string) => ['comparison', 'orders', projectUid, documentUid] as const,
  uploads: (projectUid: string) => ['comparison', 'uploads', projectUid] as const,
  queue: () => ['comparison', 'queue'] as const,
  // wave C2 (`CMP-VC-UI-02`): the AI layer, the specifications, the reports and the queues
  aiPair: (projectUid: string, documentUid: string) => ['comparison', 'ai-pair', projectUid, documentUid] as const,
  aiHints: (projectUid: string, documentUid: string) => ['comparison', 'ai-hints', projectUid, documentUid] as const,
  aiSheets: (seriesId: string) => ['comparison', 'ai-sheets', seriesId] as const,
  estimate: (scope: string) => ['comparison', 'estimate', scope] as const,
  specs: (seriesId: string) => ['comparison', 'specs', seriesId] as const,
  specChanges: (transitionId: string) => ['comparison', 'spec-changes', transitionId] as const,
  reports: (seriesId: string) => ['comparison', 'reports', seriesId] as const,
  report: (reportId: string) => ['comparison', 'report', reportId] as const,
  launchQueue: (projectUid: string) => ['comparison', 'launch-queue', projectUid] as const,
  aiQueue: () => ['comparison', 'ai-queue'] as const,
  description: (pairId: string) => ['comparison', 'description', pairId] as const,
  descriptionHistory: (pairId: string) => ['comparison', 'description-history', pairId] as const,
  reviewSheets: (transitionId: string) => ['comparison', 'review-sheets', transitionId] as const,
} as const;
