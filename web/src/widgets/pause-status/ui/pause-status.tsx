'use client';

/**
 * The pause state in the frame's top strip (`R-151f`, `UI-PARITY-P0E`; one «Пауза» button with two items, `ADR-0029`
 * decision 8). The markup is `pause-status-view.tsx`, the connected strip `pause-status-live.tsx`; this is the gate the
 * frame mounts and the public names of the three.
 *
 * The original keeps «Пауза/Продолжить» in its header. Ours shows the state to everyone the queue is open to (`expert`,
 * `admin`; `viewer` never reads it, `R-150w`) and offers the switches to those who may pause (`canExecute(roles, 'pause')`,
 * an administrator). The original's «interrupt now» mode is not here: it is a later contract.
 */

import { useEffect, useState } from 'react';

import { PauseStatusLive } from './pause-status-live';

export type { PauseStatusViewProps } from './pause-status-view';
export {
  PAUSE_BUTTON_LABEL, PAUSED_LABEL, PauseStatusView, UNREAD_LABEL, dispatchItemLabel, pauseMenuProps, vectorsItemLabel,
} from './pause-status-view';
export { PauseStatusLive } from './pause-status-live';

/**
 * The indicator as the frame mounts it: nothing until the client has mounted (a server render and the
 * style census have no query client, and the state is not known there anyway), then
 * {@link PauseStatusLive}. Mount it only for a session the queue is open to.
 */
export function PauseStatus() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? <PauseStatusLive /> : null;
}
