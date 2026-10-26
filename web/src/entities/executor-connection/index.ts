/**
 * Public API of the `executor-connection` entity (`EXEC-HTTP-01`): the reads of «Подключения»
 * and «Назначения», the words, and the rules that decide what a connection is ready for.
 *
 * Nothing here writes. The commands are in `features/manage-executor-connection`, and the key
 * is entered through `features/set-executor-secret`, whose form never makes it a JavaScript
 * value.
 */

export {
  PROBE_POLL_MS, connectionDetailQueryOptions, connectionsQueryOptions, hasOpenProbe, routesQueryOptions,
  useExecutorConnectionDetail, useExecutorConnectionDetails, useExecutorConnections,
  useExecutorRoutes,
} from './api/use-executor-connections';
export {
  CHANGE_LABELS, CHANGE_WINDOW_DAYS, recentChanges,
} from './model/changes';
export type { ChangeKind, ConnectionChange } from './model/changes';
export {
  destinationChanged, destinationOf, normalisedOrigin, sshEndpointOf,
} from './model/destination';
export { connectionFailure, connectionRefusalSentence } from './model/failure';
export {
  ROUTE_BLOCKER_SENTENCES, currentRevision, kindIsServed, probeIsOnCurrentSecret,
  requiredPurposes, routeBlocker, secretIsUnreadable, secretOfPurpose,
} from './model/readiness';
export type { RouteBlocker } from './model/readiness';
export type { ChoiceBlocker, ExecutorChoice } from './model/start-choice';
export {
  CHOICE_BLOCKER_SENTENCES, choiceCanServe, executorChoiceLabel, executorChoices,
} from './model/start-choice';
export {
  RUNNER_ONLINE_WINDOW_MS, RUNNER_TOKEN_STATE_LABELS, connectionRunnerIsOnline,
  hasLiveRunnerToken, runnerTokenIsLive, runnerTokenIsOnline, runnerTokenState, sortedRunnerTokens,
} from './model/runner-tokens';
export type { RunnerTokenState } from './model/runner-tokens';
export {
  BILLING_LABELS, FLAVOUR_LABELS, IDENTITY_BASIS_LABELS, KIND_DESCRIPTIONS, KIND_LABELS,
  PROBE_OUTCOME_HINTS, PROBE_OUTCOME_SENTENCES, PROBE_STATE_LABELS, PULL_CLIENT_LABELS,
  PURPOSE_LABELS, RATE_CHECK_LABELS, SSH_PROFILE_LABELS, TRANSPORT_LABELS, WORK_KIND_LABELS,
  probeOutcomeSentence, probeSucceeded,
} from './model/vocabulary';
