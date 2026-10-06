/**
 * Public API of `shared/config`.
 *
 * This is the only module in `web/` that reads `process.env`. A guard test enforces it,
 * because an environment lookup scattered through a slice is how a localhost default
 * gets reintroduced.
 */

export { MissingConfigurationError, getApiBaseUrl, getInstanceLabel, hasApiBaseUrl } from './env';
export { RUN_POLLING, pollDelayMs } from './polling';

// `W50-PLAN.md` §3.1: the only list of screens, and the one validator for `next`/`from`.
export type {
  RouteParams,
  ScreenAccess,
  ScreenAccessOf,
  ScreenAddress,
  ScreenEntry,
  ScreenGroup,
  ScreenRoles,
} from './screen-registry';
export {
  CHANGE_PASSWORD_SCREEN,
  FORBIDDEN_SCREEN,
  FROM_PARAM,
  HOME_SCREEN,
  NEXT_PARAM,
  PROFILE_SCREEN,
  RETURN_PATH_MAX_LENGTH,
  SCREEN_ACCESS_LEVELS,
  SCREEN_GROUPS,
  SCREEN_REGISTRY,
  SIGN_IN_SCREEN,
  concreteAddress,
  requiredRolesFor,
  safeReturnPath,
  screenAt,
  screenMatching,
} from './screen-registry';
