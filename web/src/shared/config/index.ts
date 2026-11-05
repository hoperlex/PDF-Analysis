/**
 * Public API of `shared/config`.
 *
 * This is the only module in `web/` that reads `process.env`. A guard test enforces it,
 * because an environment lookup scattered through a slice is how a localhost default
 * gets reintroduced.
 */

export { MissingConfigurationError, getApiBaseUrl, getInstanceLabel, getWebBuildId, hasApiBaseUrl } from './env';
export {
  AGENT_INSTALL_POLL_MS, AGENT_STATUS_POLL_MS, AI_POLL_MS, AI_QUEUE_POLL_MS, MATRIX_BUILD_POLL_MS,
  OPERATIONAL_LIST_POLLING, OPERATIONAL_LIST_STALE_MS, OVERVIEW_BUSY_POLL_MS, OVERVIEW_IDLE_POLL_MS,
  PROBE_POLL_MS, RUN_POLLING, SERIES_POLL_MS, SPECIFICATION_POLL_MS, STAGE_REVIEW_POLL_MS,
  STAGE_TEXT_POLL_MS, UPLOAD_POLL_MS,
  isOperationalListStale, operationalListInterval, pollDelayMs,
} from './polling';
export type { OperationalListFreshness, OperationalListPollState } from './polling';
export { SHOW_REVIEW_INDICATION } from './review-indication';

// `W50-PLAN.md` §3.1: the only list of screens, and the one validator for `next`/`from`.
export type {
  RouteParams,
  ScreenAccess,
  ScreenAccessOf,
  ScreenAddress,
  ScreenDecision,
  ScreenDecisionSubject,
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
  screenDecision,
  screenMatching,
} from './screen-registry';
