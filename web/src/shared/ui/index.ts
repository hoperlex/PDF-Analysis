/**
 * Public API of `shared/ui`.
 *
 * Presentation primitives only: they take contract values and render them, and they hold
 * no query, no mutation and no domain rule. `B7` and `B8` compose them; neither edits
 * them, and neither adds a sixth mandatory state.
 */

export type {
  EmptyStateProps,
  ErrorStateProps,
  LoadingStateProps,
  NotApplicableStateProps,
  UnsupportedStateProps,
} from './states';
export {
  EmptyState,
  ErrorState,
  LoadingState,
  NotApplicableState,
  UnsupportedState,
} from './states';

export type { RunStateBadgeProps } from './run-state-badge';
export { RunStateBadge } from './run-state-badge';

export type { StageStatusBadgeProps } from './stage-status-badge';
export { StageStatusBadge } from './stage-status-badge';

export type { PageShellProps } from './page-shell';
export { PageShell } from './page-shell';

export type { RoutePlaceholderProps } from './route-placeholder';
export { RoutePlaceholder } from './route-placeholder';

export type { IconName, IconProps } from './icon';
export { FEATHER_SOURCE, ICON_NAMES, Icon } from './icon';
