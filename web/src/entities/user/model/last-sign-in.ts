import { formatInstant } from '@/shared/lib';

/**
 * «Последний вход» of an account (contract 1.36.0, `UI-A-92`): the instant of its latest successful sign-in, as the
 * server read it from the access journal. `null` is not a failure: the account never signed in, or signed in before
 * the journal began, and it is said so rather than drawn as a blank.
 */
export const NEVER_SIGNED_IN = 'Входов не было';

export function lastSignInText(lastSignInAt: string | null): string {
  return lastSignInAt === null ? NEVER_SIGNED_IN : formatInstant(lastSignInAt);
}
