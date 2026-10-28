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
} as const;
