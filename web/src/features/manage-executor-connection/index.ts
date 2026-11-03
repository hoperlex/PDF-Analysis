/**
 * Public API of the `manage-executor-connection` feature slice (`EXEC-HTTP-01`).
 *
 * The administrator's commands on a connection: create with its first settings, revise,
 * archive, probe, generate an SSH key, confirm an observed host key, name a route, and (for a
 * `pull` connection) issue and revoke runner tokens. The key of a connection is **not** here — it goes through `features/set-executor-secret`.
 *
 * `EXEC2-WEB-WIZARD-01` adds the commands of the universal agent (issue an enrollment, start an
 * install over SSH, confirm its host key, set the integration mark); the wizard that uses them is
 * `features/connect-remote-agent`.
 */

export {
  useArchiveExecutorConnection,
  useConfirmExecutorAgentInstallHostKey,
  useCreateExecutorAgentInstall,
  useCreateExecutorConnection,
  useGenerateExecutorSshKey,
  useIssueExecutorEnrollment,
  useIssueRunnerToken,
  useRequestExecutorProbe,
  useReviseExecutorConnection,
  useRevokeRunnerToken,
  useSetExecutorIntegrationAuthorisation,
} from './model/use-manage-executor-connection';
export { useSetExecutorRoute } from './model/use-set-executor-route';
export { useCommandKey } from './model/use-command-key';
export {
  ANSWER_DEADLINE_DEFAULT_SECONDS, CLAIMED_TASKS_DEFAULT, FIELD_NAMES, PARALLEL_DEFAULT, SSH_PORT_DEFAULT,
  TIMEOUT_DEFAULT_SECONDS, draftMovesTheKey, initialSettings, readRevision, readSshEndpoint, requestFromRevision,
} from './model/settings';
export type { SettingsReading } from './model/settings';

export { ArchiveControl } from './ui/archive-control';
export { CommandFailure } from './ui/command-failure';
export { CreateConnectionForm } from './ui/create-connection-form';
export { HostKeyControl } from './ui/host-key-control';
export { ProbeButton } from './ui/probe-button';
export { ReviseConnectionForm } from './ui/revise-connection-form';
export { IssuedTokenView, RunnerTokenPanel } from './ui/runner-token-panel';
export { SettingsFields } from './ui/settings-fields';
export { SshKeyControl } from './ui/ssh-key-control';
