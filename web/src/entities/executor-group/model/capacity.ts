/**
 * The capacity of a group and the standing of each member, in words (`EXEC2-WEB-GROUPS-01`,
 * ADR-0026 decisions 1, 14 and 19).
 *
 * The reading is derived by the server from the database each time it is asked and stored
 * nowhere: `capacity` sums the units of the members still in service, `used` the units in use,
 * `waiting` the work admitted on any revision of the group that is still waiting to be sent. As
 * on a connection's card, **no sentence here says a place is «свободно»**: a unit held by work
 * whose remote outcome is unresolved is counted as in use, and a screen that printed «свободно»
 * beside it would offer a place that does not exist. A reading whose figures are not whole
 * non-negative numbers is drawn as nothing at all rather than as a guess.
 */

import type { ExecutorGroupCapacity, ExecutorGroupMemberStatus } from '@/shared/api';
import { occupancyReading, occupancySentence } from '@/entities/executor-connection';

import { MEMBER_ISSUE_SENTENCES } from './vocabulary';

const isCount = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0;

/**
 * «Занято 2 из 4, ждут отправки в работу: 1.» — or `null` when the reading is not whole.
 * Work that waits is named only when there is some.
 */
export function groupCapacitySentence(
  capacity: Pick<ExecutorGroupCapacity, 'capacity' | 'used' | 'waiting'>,
): string | null {
  if (!isCount(capacity.capacity) || !isCount(capacity.used) || !isCount(capacity.waiting)) return null;
  const waiting = capacity.waiting > 0 ? `, ждут отправки в работу: ${capacity.waiting}` : '';
  return `Занято ${capacity.used} из ${capacity.capacity}${waiting}.`;
}

/**
 * «Подходит для выбора» or «Сейчас не будет выбрано: все места подключения заняты» — the verdict
 * of dispatch on one member. A member that is not eligible and carries no reason is said as such,
 * and no reason is invented.
 */
export function memberStatusSentence(status: ExecutorGroupMemberStatus): string {
  if (status.eligible) return 'Подходит для выбора';
  if (status.ineligible_reason === undefined) return 'Сейчас не будет выбрано';
  return `Сейчас не будет выбрано: ${MEMBER_ISSUE_SENTENCES[status.ineligible_reason]}`;
}

/** The occupancy of one member as a connection's card words it, or `null` when it carries none. */
export function memberOccupancySentence(status: ExecutorGroupMemberStatus): string | null {
  const reading = occupancyReading(status.occupancy === undefined ? {} : { occupancy: status.occupancy });
  return reading === null ? null : occupancySentence(reading);
}
