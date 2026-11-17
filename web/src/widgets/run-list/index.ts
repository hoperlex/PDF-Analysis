/** Public API of the `run-list` widget. */

export type { RunListProps } from './ui/run-list';
export { RunList } from './ui/run-list';

// `UIP-S04-03`: the first card of the version's «Инфо»: the last run, its stages, «Запустить».
export type { LastRunCardProps } from './ui/last-run-card';
export { LastRunCard } from './ui/last-run-card';
export { chipHint, lastRunChips, reusedStageIdsOf } from './model/last-run-chips';

// `READINESS-WEB-01`: «Запустить» with the line under it read from `getRunStartReadiness`, the reason it is inactive, and the plan window.
export type { StartRunWithReadinessProps } from './ui/start-run-with-readiness';
export { MODELS_BY_STAGE_ADDRESS, StartRunWithReadiness } from './ui/start-run-with-readiness';
