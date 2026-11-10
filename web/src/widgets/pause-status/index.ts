/**
 * Public API of the `pause-status` widget: the pause state in the frame's top strip (`R-151f`), one «Пауза» button with
 * the items «Выдача анализа» and «Векторы» (`ADR-0029` decision 8). Importers use `@/widgets/pause-status` and nothing deeper.
 */

export type { PauseStatusViewProps } from './ui/pause-status';
export {
  PAUSE_BUTTON_LABEL, PAUSED_LABEL, PauseStatus, PauseStatusLive, PauseStatusView, UNREAD_LABEL, dispatchItemLabel,
  pauseMenuProps, vectorsItemLabel,
} from './ui/pause-status';
