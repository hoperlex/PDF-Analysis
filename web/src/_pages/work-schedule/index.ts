/** Public API of the `work-schedule` page slice (`UI-PARITY-P0P`, «График работ»). */

export type { ScheduleAddress, ScheduleMode, ScheduleTab } from './model/address';
export { RESERVE_DAYS, SCHEDULE_MODES, openAbsences, readScheduleAddress, scheduleSearch, withoutMode } from './model/address';
export type { WorkSchedulePageProps } from './ui/work-schedule-page';
export { WorkSchedulePage } from './ui/work-schedule-page';
