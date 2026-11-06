/** Public API of the `work-schedule` page slice (`UI-PARITY-P0P`, «График работ»). */

export type { ScheduleAddress, ScheduleTab } from './model/address';
export { RESERVE_DAYS, readScheduleAddress, scheduleSearch } from './model/address';
export type { WorkSchedulePageProps } from './ui/work-schedule-page';
export { WorkSchedulePage } from './ui/work-schedule-page';
