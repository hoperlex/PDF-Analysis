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
export { COST_BASIS_LABELS, PROVIDER_MODE_LABELS, PROVIDER_MODE_UNKNOWN_LABEL, STATE_LABELS, RunStateBadge } from './run-state-badge';

export type { StageStatusBadgeProps } from './stage-status-badge';
export { StageStatusBadge } from './stage-status-badge';

export { STAGE_LABELS } from './stage-label';

export type { PageShellProps } from './page-shell';
export { PageShell } from './page-shell';

export type { RoutePlaceholderProps } from './route-placeholder';
export { RoutePlaceholder } from './route-placeholder';

export type { IconName, IconProps } from './icon';
export { FEATHER_SOURCE, ICON_NAMES, Icon } from './icon';

/*
 * The shell's three primitives (`W50-SHELL-UI`). `W50-SHELL-FRAME` composes them for the
 * navigation groups, the stacked menu and the account menu. Each takes labels, links, items,
 * initials and a colour key — never a session, a query or a registry row.
 */
export type { DisclosureLink, DisclosureProps } from './disclosure';
export { Disclosure } from './disclosure';
export type { DisclosureEvent, DisclosureFocus, DisclosureTransition } from './disclosure-state';
export { disclosureTransition } from './disclosure-state';

export type { MenuItem, MenuProps } from './menu';
export { Menu } from './menu';
export type { MenuEvent, MenuFocus, MenuState, MenuTransition } from './menu-state';
export { MENU_CLOSED, menuTransition } from './menu-state';

export type { AvatarProps } from './avatar';
export { Avatar, AvatarInitialsError } from './avatar';
export { AVATAR_PALETTE_SIZE, avatarColourIndex, normaliseColourKey } from './avatar-colour';
