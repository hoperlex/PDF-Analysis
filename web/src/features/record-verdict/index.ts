/** Public API of the `record-verdict` feature: append an accept or a reject. */

export type { VerdictRefusal, VerdictRequestCheck, VerdictRequestInput } from './model/verdict-request';
export {
  VERDICT_REFUSALS,
  buildVerdictRequest,
  verdictIntentOf,
  verdictRefusalMessage,
} from './model/verdict-request';

export type {
  RecordVerdictApi,
  RecordVerdictArgs,
  VerdictIntent,
  VerdictSeverity,
} from './model/use-record-verdict';
export { useRecordVerdict } from './model/use-record-verdict';
