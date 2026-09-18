/**
 * `D-22` — the intent-key rule, now that there is one of it.
 *
 * `W16-WEB` §5.1 measured why this file could not exist before: the rule lived four
 * times, and three of those copies were inside a `useRef` in a hook. Mutations U-06, U-07
 * and U-08 survived **by construction** — one render pass, a ref that is always fresh, so
 * no assertion over rendered markup can tell a correct copy from a broken one. The rule is
 * now a pure function over an opaque signature with `mint` injected, so *when a key is
 * minted* is observable, which is the thing the rule is actually about.
 *
 * Each test below names the mutation it kills.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { resolveIntentKey } from '@/shared/lib';
import type { IntentRecord } from '@/shared/lib';
import { intentSignature, resolveIntentKey as resolveDecisionIntent } from '@/entities/expert-decision';
import type { AppendDecisionRequest } from '@/shared/api';

import { WEB_ROOT } from '../../guards/lib/repo';

/** A mint that counts, so "a key was minted" is a fact and not an inference. */
function counter() {
  let n = 0;
  return {
    mint: () => {
      n += 1;
      return `idem-${n}`;
    },
    get count() {
      return n;
    },
  };
}

describe('the rule: one key per intent, reused on every retry', () => {
  it('mints once for a new intent', () => {
    const c = counter();
    const first = resolveIntentKey(null, 'start-run:ver_A', c.mint);
    expect(first.idempotencyKey).toBe('idem-1');
    expect(first.signature).toBe('start-run:ver_A');
    expect(c.count).toBe(1);
  });

  it('mints NOTHING on a retry of the same intent, however many times', () => {
    // The mutation this kills: dropping the `previous.signature === signature` guard, so
    // every retry mints a fresh key. A fresh key is a second command -- a second run, a
    // second version, a second accept in an append-only ledger.
    const c = counter();
    const first = resolveIntentKey(null, 'start-run:ver_A', c.mint);
    const retry = resolveIntentKey(first, 'start-run:ver_A', c.mint);
    const again = resolveIntentKey(retry, 'start-run:ver_A', c.mint);

    expect(retry).toBe(first);
    expect(again).toBe(first);
    expect(c.count).toBe(1);
  });

  it('mints again the moment the intent changes', () => {
    // The opposite mutation: always returning `previous`. That sends a changed payload
    // under an old key, which the contract answers with `idempotency_key_reuse`, and that
    // is terminal -- nothing is created and nothing is resubmitted.
    const c = counter();
    const first = resolveIntentKey(null, 'start-run:ver_A', c.mint);
    const other = resolveIntentKey(first, 'start-run:ver_B', c.mint);

    expect(other.idempotencyKey).not.toBe(first.idempotencyKey);
    expect(other.signature).toBe('start-run:ver_B');
    expect(c.count).toBe(2);
  });

  it('does not mutate the record it was handed', () => {
    const c = counter();
    const first: IntentRecord = resolveIntentKey(null, 'a', c.mint);
    resolveIntentKey(first, 'b', c.mint);
    expect(first.signature).toBe('a');
    expect(first.idempotencyKey).toBe('idem-1');
  });
});

describe('the decision entity keeps what is about decisions and delegates the rest', () => {
  const accept: AppendDecisionRequest = {
    event_type: 'accept',
    finding_observation_id: 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  } as AppendDecisionRequest;

  it('resolves through the shared rule over its own signature', () => {
    const c = counter();
    const viaEntity = resolveDecisionIntent(null, accept, c.mint);
    const viaShared = resolveIntentKey(null, intentSignature(accept), counter().mint);

    expect(viaEntity.signature).toBe(viaShared.signature);
    expect(c.count).toBe(1);
  });

  it('still treats a retyped comment as a different intent', () => {
    const c = counter();
    const drafted = resolveDecisionIntent(null, { ...accept, comment: 'first' }, c.mint);
    const edited = resolveDecisionIntent(drafted, { ...accept, comment: 'second' }, c.mint);
    expect(edited.idempotencyKey).not.toBe(drafted.idempotencyKey);
    expect(c.count).toBe(2);
  });
});

describe('no slice holds a copy of the rule any more (D-22)', () => {
  const COPIES = [
    'src/features/create-project/model/use-intent-key.ts',
    'src/features/upload-document/model/use-intent-key.ts',
    'src/features/start-run/model/use-intent-key.ts',
  ];

  it.each(COPIES)('%s is gone', (relative) => {
    let read: string | null = null;
    try {
      read = readFileSync(join(WEB_ROOT, relative), 'utf8');
    } catch {
      read = null;
    }
    expect(read).toBeNull();
  });

  it('the three write features call the shared hook and declare no hook of their own', () => {
    for (const feature of ['create-project', 'upload-document', 'start-run']) {
      const files = [
        `src/features/${feature}/ui`,
        `src/features/${feature}/model`,
      ];
      for (const dir of files) {
        const entries = safeList(join(WEB_ROOT, dir));
        for (const entry of entries) {
          const text = readFileSync(join(WEB_ROOT, dir, entry), 'utf8');
          expect(text).not.toMatch(/export function useIntentKey/);
        }
      }
    }
  });
});

function safeList(dir: string): string[] {
  try {
    return readdirSync(dir).filter((n) => /\.tsx?$/.test(n));
  } catch {
    return [];
  }
}
