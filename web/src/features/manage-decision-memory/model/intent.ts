import type { DecisionMemoryCaseId } from '@/shared/api';
import type { MemoryReason } from '@/entities/decision-memory';

import type { StandingKind } from './use-change-standing';

/**
 * The signature of one standing change, from which `useIntentKey` keeps or mints the idempotency key. The kind, the case and the
 * reason are the whole payload of the call: a different reason is a different intent, and sending it under the earlier key would
 * be `idempotency_key_reuse`. Parts are length-prefixed so that no value can run into the next one.
 */
export function standingIntentSignature(kind: StandingKind, caseId: DecisionMemoryCaseId, reason: MemoryReason | ''): string {
  return [kind, caseId, reason].map((part) => `${part.length}:${part}`).join('|');
}
