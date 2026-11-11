/**
 * `RUN-DELETE-01`: the sentence under the confirmation when the server refuses or the request does not arrive.
 *
 * The two refusals the screen can say more precisely about keep their own sentence; every other failure is the shared reading, behind
 * «Прогон не удалён:».
 */

import { failureMessage } from '@/shared/api';

import { DELETE_RUN_GONE, DELETE_RUN_NOT_DELETABLE } from './words';

export function deleteFailureText(error: unknown): string {
  const failure = failureMessage(error, {
    state_transition_not_allowed: DELETE_RUN_NOT_DELETABLE,
    not_found: DELETE_RUN_GONE,
  });
  return failure.kind === 'state_transition_not_allowed' || failure.kind === 'not_found'
    ? failure.detail
    : `Прогон не удалён: ${failure.detail}`;
}
