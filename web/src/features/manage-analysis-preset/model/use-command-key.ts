'use client';

import { useRef } from 'react';

import { newIdempotencyKey } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

/**
 * One idempotency key per intent, for a control that sends one command at a time
 * (`web/docs/PC01_UI_SEAM.md` §4.3, `shared/lib/intent-key.ts`).
 *
 * `keyFor(signature)` keeps the held key while the signature is unchanged — an explicit repeat after
 * an unknown outcome is the same command — and mints a new one when the signature changes.
 * `release()` is called when the command is settled (it succeeded, or the server refused it for
 * good): the next press of the same button is a new command and must not replay the old answer.
 */
export function useCommandKey() {
  const held = useRef<IntentRecord | null>(null);
  return {
    keyFor(signature: string): string {
      held.current = resolveIntentKey(held.current, signature, newIdempotencyKey);
      return held.current.idempotencyKey;
    },
    release(): void {
      held.current = null;
    },
  };
}
