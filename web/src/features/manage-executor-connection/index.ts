/**
 * Public API of the `manage-executor-connection` feature slice (`EXEC-HTTP-01`).
 *
 * The administrator's commands on a connection: create with its first settings, revise,
 * archive, probe, generate an SSH key, confirm an observed host key, name a route, and (for a
 * `pull` connection) issue and revoke runner tokens. The key of a connection is **not** here — it goes through `features/set-executor-secret`.
 */

export {
  useArchiveExecutorConnection,
  useCreateExecutorConnection,
  useGenerateExecutorSshKey,
  useIssueRunnerToken,
  useRequestExecutorProbe,
  useReviseExecutorConnection,
  useRevokeRunnerToken,
} from './model/use-manage-executor-connection';
export { useSetExecutorRoute } from './model/use-set-executor-route';
export { useCommandKey } from './model/use-command-key';
export { FIELD_NAMES, draftMovesTheKey, initialSettings, readRevision, requestFromRevision } from './model/settings';
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
