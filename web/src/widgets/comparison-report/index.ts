/**
 * Public API of the `comparison-report` widget (`CMP-VC-UI-02`): the window «Сформировать PDF-отчёт…» of «Сравнение версий».
 * The page that composes the tabs mounts it through the slot of the sheets tab.
 */

export type { ReportAct, ReportWindowProps, ReportWindowViewProps } from './ui/report-window';
export {
  MAX_SOURCE_NOTE,
  NO_REPORTS,
  NO_SUMMARY_HINT,
  ReportWindow,
  ReportWindowView,
  WINDOW_SUBTITLE,
  WINDOW_TITLE,
} from './ui/report-window';
export { FailureBlock, MODULE_UNAVAILABLE_TITLE } from './ui/failure-block';
