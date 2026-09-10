/**
 * Public API of `shared/config`.
 *
 * This is the only module in `web/` that reads `process.env`. A guard test enforces it,
 * because an environment lookup scattered through a slice is how a localhost default
 * gets reintroduced.
 */

export { MissingConfigurationError, getApiBaseUrl, getInstanceLabel, hasApiBaseUrl } from './env';
export { RUN_POLLING, pollDelayMs } from './polling';
