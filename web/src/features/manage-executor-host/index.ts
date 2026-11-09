/**
 * Public API of the `manage-executor-host` feature slice (`HOSTS-WEB-01`, ADR-0028).
 *
 * The administrator's commands on a server: the switch «Использовать», «Удалить», the places of a provider and «Подробнее»,
 * and the window «Подключить сервер» (a line for the terminal, or an install over SSH with the fingerprint to confirm). No
 * model is asked anywhere. The views are exported beside the stateful components so a test can render a screen in a state a
 * static render cannot reach by pressing buttons.
 */

export { arrivalOf, hostOf } from './model/arrival';
export type { Arrival } from './model/arrival';
export { useArrival } from './model/use-arrival';
export {
  useArchiveExecutorHost, useConfirmExecutorHostAgentInstallHostKey, useCreateExecutorHostAgentInstall,
  useIssueExecutorHostEnrollment, useSetExecutorHostEnabled, useSetExecutorHostSlots,
} from './model/use-manage-executor-host';
export {
  CONNECT_LABEL, DELETE_CANCEL_LABEL, DELETE_CONFIRM_LABEL, INSTALL_STEP_IDS, INSTALL_STEP_LABELS, TAB_COMMAND, TAB_SSH,
  installSteps,
} from './model/words';

export { ConnectServer, ConnectWindow, ConnectWindowView, CommandTabView, SshFormView, readSshForm } from './ui/connect-server';
export type { ConnectTab } from './ui/connect-server';
export { DeleteHostControl, DeleteHostView } from './ui/delete-host-control';
export { HostDetails, HostDetailsView, SlotsView } from './ui/host-details';
export { HostEnabledSwitch, HostEnabledSwitchView } from './ui/host-enabled-switch';
export { HostFailure } from './ui/host-failure';
export { InstallSession, InstallSessionView } from './ui/install-session';
