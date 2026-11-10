/**
 * Public API of the `connect-remote-agent` feature slice (`EXEC2-WEB-WIZARD-01`).
 *
 * «Добавить подключение» for the universal agent (ADR-0026 decisions 4 to 9, `R-149b`): the wizard
 * with its two equal choices («Удалённый Ubuntu-агент», «API-провайдер»), the two equal ways to
 * install the agent (over SSH, or by one command shown once), the OpenRouter preset, the lifecycle
 * both paths share (ожидает регистрации → агент в сети → клиент найден → вход → проба → готово), the
 * administrator's integration mark, and moving an agent to another server.
 *
 * The commands themselves are in `features/manage-executor-connection`; the key of a connection never
 * passes through this slice — it goes through `features/set-executor-secret`. The views are exported
 * beside the stateful components so a test can render a screen in a state a static render cannot reach
 * by pressing buttons.
 */

export { EMPTY_COMMAND_BOX, commandBoxReducer } from './model/command-box';
export type { CommandBox, CommandBoxAction } from './model/command-box';
export { agentFailure, agentRefusalSentence } from './model/failure';
export {
  AGENT_STEP_ORDER, JOIN_WINDOW_MS, agentIsMoving, agentLifecycle, currentStep, enrollmentIsExpired,
  enrollmentIsPending, isAgentConnection, tokenIsOnline,
} from './model/lifecycle';
export type {
  AgentLifecycle, AgentStep, AgentStepId, AgentStepReasons, AgentStepState, AgentSteps, CliReading,
} from './model/lifecycle';
export {
  OPENROUTER_BASE_URL, agentRevisionRequest, installSignature, openRouterRevisionRequest, readIdentity,
  readInstall,
} from './model/agent-settings';
export type { AgentIdentity, IdentityReading, InstallReading } from './model/agent-settings';
export { agentProbeHint, stepSentence } from './model/step-sentences';
export {
  agentInstallQueryKey, hostHasReported, installIsMoving, useAgentInstall, useAgentStatusPoll, useHostArrivalPoll,
  useHostInstall,
} from './model/use-agent-polls';
export { useEnsureConnection } from './model/use-ensure-connection';
export type { ConnectionSpec } from './model/use-ensure-connection';
export {
  AGENT_PROBE_HINTS, CLI_AUTH_LABELS, CLI_NAMES, COMMAND_EXPIRED_TITLE, COMMAND_UNKNOWN_OUTCOME,
  CONFLICT_SENTENCES, DEPENDENCY_SENTENCES, ENROLLMENT_STATE_LABELS, INSTALL_FAILURE_SENTENCES,
  INSTALL_STATE_LABELS, INTEGRATION_NOTE, KIND_CHOICES, LOGIN_COMMANDS, MOVE_LABEL, MOVE_PENDING_NOTE,
  MOVE_TEXT, OLD_TOKEN_CONFIRM_TEXT, OLD_TOKEN_REVOKE_LABEL, OLD_TOKEN_TEXT, PATH_CHOICES, STEP_LABELS,
  VALIDATION_SENTENCES, WIZARD_OPEN_LABEL,
} from './model/words';

export { AgentSetup } from './ui/agent-setup';
export type { AgentSetupProps } from './ui/agent-setup';
export { AgentLifecyclePanel } from './ui/agent-lifecycle-panel';
export type { AgentLifecyclePanelProps } from './ui/agent-lifecycle-panel';
export { AgentProgressLine } from './ui/agent-progress-line';
export { KindChoiceView, PathChoiceView } from './ui/choices';
export type { KindChoice, PathChoice } from './ui/choices';
export { ConnectWizard, ConnectWizardLauncher } from './ui/connect-wizard';
export type { ConnectWizardProps } from './ui/connect-wizard';
export { CopyBox } from './ui/copy-box';
export { EnrollmentCommandControl, EnrollmentCommandView } from './ui/enrollment-command';
export { IntegrationMark, IntegrationMarkView } from './ui/integration-mark';
export { MoveAgentControl, SupersededTokens, SupersededTokensView } from './ui/move-agent';
export { OpenRouterFixedFacts, OpenRouterKeyStep, OpenRouterSetup } from './ui/openrouter-setup';
export { SshInstallForm } from './ui/ssh-install-form';
export { SshInstallSession, SshInstallSessionView } from './ui/ssh-install-session';
