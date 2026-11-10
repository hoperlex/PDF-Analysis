/**
 * One press of «Отозвать» / «Вернуть» (`D-503`): the command goes out once, however many presses arrive before the answer.
 *
 * Pure of React so that a unit test can press twice in the same tick, which a static render cannot. A press with no reason sends
 * nothing (the control also holds its button until a reason is chosen). The mutation keeps its own failure for the screen to
 * say, so a rejection here is only the gate reopening.
 */

import type { SingleFlight } from './single-flight';
import type { StandingChange } from './use-change-standing';

/** Whether this press sent the command. */
export function pressStanding(
  flight: SingleFlight,
  command: StandingChange | null,
  send: (command: StandingChange) => Promise<unknown>,
  onSent: () => void,
): boolean {
  if (command === null) return false;
  return flight.run(() => send(command).then(onSent, () => undefined));
}
