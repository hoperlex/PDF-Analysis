/**
 * What the box that shows an install command holds, and how it changes (`EXEC2-WEB-WIZARD-01`,
 * ADR-0026 decision 4).
 *
 * The command is shown **once**: the stand keeps only a hash of its secret, so no operation can show
 * it again, and the screen must not either. The box is therefore a small state machine with two moves
 * and nothing else, written as a pure reducer so the rule is a function a test calls:
 *
 * - `issued`: a command arrived. It **replaces** whatever the box held — a new grant revokes the
 *   previous unredeemed one on the stand, so only the newest command works, and the box never holds two.
 * - `closed`: the person closed the box. The command is gone from the state, and `everShown` is the
 *   only trace left (it only changes the label of the button that asks for the next command).
 *
 * The state is the only place the command lives. It is not written to a storage, an address or a log,
 * and a state after `closed` contains no part of it.
 */

import type { IssuedExecutorEnrollment } from '@/shared/api';

export interface CommandBox {
  readonly issued: IssuedExecutorEnrollment | null;
  /** The command now shown replaced an earlier one that was shown in this box. */
  readonly replaced: boolean;
  /** A command was shown at least once; the command itself is not kept. */
  readonly everShown: boolean;
}

export type CommandBoxAction =
  | { readonly type: 'issued'; readonly issued: IssuedExecutorEnrollment }
  | { readonly type: 'closed' };

export const EMPTY_COMMAND_BOX: CommandBox = { issued: null, replaced: false, everShown: false };

export function commandBoxReducer(state: CommandBox, action: CommandBoxAction): CommandBox {
  switch (action.type) {
    case 'issued':
      return { issued: action.issued, replaced: state.issued !== null, everShown: true };
    case 'closed':
      return { issued: null, replaced: false, everShown: state.everShown };
  }
}
