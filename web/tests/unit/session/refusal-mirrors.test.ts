/**
 * The two copies of the sign-in refusal set are one set, and the registration door's set is
 * the closed six `W49-PLAN.md` §3.5 names.
 *
 * `SIGN_IN_REFUSALS` in `@/features/sign-in/model/exchange.ts` is what the screen can render.
 * `type Refusal` in `web/src/app/bff/v1/[...path]/route.ts` is what the handler can redirect
 * with, and it is a **copy** on purpose: the handler holds the deployment secret and must not
 * import a feature's React tree to obtain a list of strings (the handler's own comment says
 * so). A copy is only safe if something compares it with its original, and a type cannot be
 * imported into a running test — so the union is read out of the handler's source, the way
 * `change-password.test.ts` reads the outcomes the handler produces.
 *
 * Three readings, because a mirror can drift three ways: the declared union and the feature's
 * list disagree; the handler redirects with a value the union does not declare (the compiler
 * catches that, and this test says it in words); or the screen offers a sentence the handler
 * can never produce, which is dead vocabulary that a later reader takes for a live branch.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { SIGN_IN_REFUSALS } from '@/features/sign-in';

import { WEB_ROOT } from '../../guards/lib/repo';

const HANDLER = readFileSync(join(WEB_ROOT, 'src/app/bff/v1/[...path]/route.ts'), 'utf8');

/** The string literals of `type <name> = ...;` in `source`, in order. */
function unionMembers(source: string, name: string): string[] {
  const declaration = source.match(new RegExp(`\\btype ${name} =([^;]+);`));
  if (declaration === null) throw new Error(`no \`type ${name}\` in the handler`);
  return [...(declaration[1] ?? '').matchAll(/'([a-z_]+)'/g)].map((match) => match[1] as string);
}

/** The literal arguments of every `<call>('…')` in `source`. */
function literalArguments(source: string, call: string): string[] {
  return [...source.matchAll(new RegExp(`\\b${call}\\(\\s*'([a-z_]+)'`, 'g'))].map(
    (match) => match[1] as string,
  );
}

/** What the comparison says about two lists: empty when they are one set. */
function drift(declared: readonly string[], published: readonly string[]): string[] {
  const left = new Set(declared);
  const right = new Set(published);
  return [
    ...[...left].filter((value) => !right.has(value)).map((value) => `only in the handler: ${value}`),
    ...[...right].filter((value) => !left.has(value)).map((value) => `only in the feature: ${value}`),
  ];
}

describe('the sign-in refusal set has one value list, held in two places', () => {
  it('declares in the handler exactly the values the screen publishes', () => {
    const declared = unionMembers(HANDLER, 'Refusal');
    expect(declared.length).toBeGreaterThan(0);
    expect(new Set(declared).size).toBe(declared.length);
    expect(drift(declared, SIGN_IN_REFUSALS)).toEqual([]);
  });

  it('includes the two values W49 added, in both places', () => {
    for (const added of ['pending', 'throttled']) {
      expect(unionMembers(HANDLER, 'Refusal')).toContain(added);
      expect(SIGN_IN_REFUSALS as readonly string[]).toContain(added);
    }
  });

  it('redirects with every value the screen can render, and with no other', () => {
    const produced = new Set(literalArguments(HANDLER, 'refuseSignIn'));
    // `refuseSignIn(pending ? 'pending' : 'credentials')` carries two literals in one call.
    for (const match of HANDLER.matchAll(/refuseSignIn\(\s*\w+\s*\?\s*'([a-z_]+)'\s*:\s*'([a-z_]+)'/g)) {
      produced.add(match[1] as string);
      produced.add(match[2] as string);
    }
    expect([...produced].sort()).toEqual([...SIGN_IN_REFUSALS].sort());
  });

  it('can fail: the comparison names a value one side gained alone', () => {
    const doctored = HANDLER.replace("| 'throttled'", "| 'throttled' | 'locked'");
    expect(drift(unionMembers(doctored, 'Refusal'), SIGN_IN_REFUSALS)).toEqual([
      'only in the handler: locked',
    ]);
    const shrunk = HANDLER.replace(" | 'pending'", '');
    expect(drift(unionMembers(shrunk, 'Refusal'), SIGN_IN_REFUSALS)).toEqual([
      'only in the feature: pending',
    ]);
  });
});

describe('the registration door answers with the closed six and nothing else', () => {
  const CLOSED = ['validation', 'login_taken', 'request_pending', 'queue_full', 'throttled', 'upstream'];

  it('declares exactly the six W49-PLAN.md §3.5 names', () => {
    expect(unionMembers(HANDLER, 'RegistrationRefusal')).toEqual(CLOSED);
  });

  it('redirects only with declared values', () => {
    const produced = literalArguments(HANDLER, 'refuseRegistration');
    expect(produced.length).toBeGreaterThan(0);
    for (const value of produced) expect(CLOSED).toContain(value);
  });
});
