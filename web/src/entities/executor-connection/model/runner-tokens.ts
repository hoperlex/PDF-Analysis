/**
 * The runner tokens of a `pull` connection, as the screen reads them (`EXEC-CANDIDATE-2`,
 * `EXEC-PULL-01`, plan §2.1 and T-2).
 *
 * A token is shown to its person once, when it is issued; everything here is about the facts the
 * server keeps afterwards: the visible prefix, when it was made and expires, when it was revoked,
 * and when and from where it was last seen. The value and its hash are never returned, so none of
 * these functions can touch them.
 *
 * «На связи» is a fact about the last minute: the stand saw a call from a runner of this
 * connection (a claim, or the extend and answer that follow one) less than sixty seconds ago.
 * The waiting claim lasts at most twenty-five seconds and a new one follows at once, so an idle
 * runner stays under the limit and a stopped one leaves it within a minute.
 *
 * The screen reads this when the page opens, when the tab is returned to, after a command and by
 * «Обновить». It schedules no poll of its own: the only timer the connection reads may have is the
 * bounded probe poll that `tests/unit/run/polling.test.ts` names.
 */

import type { ExecutorConnectionDetail, RunnerTokenMetadata } from '@/shared/api';

/** How recent the last call of a runner must be for the connection to be called «на связи». */
export const RUNNER_ONLINE_WINDOW_MS = 60_000;

export type RunnerTokenState = 'active' | 'revoked' | 'expired';

export const RUNNER_TOKEN_STATE_LABELS: Readonly<Record<RunnerTokenState, string>> = {
  active: 'действует',
  revoked: 'отозван',
  expired: 'срок истёк',
};

function instant(text: string | undefined): number | null {
  if (text === undefined) return null;
  const parsed = Date.parse(text);
  return Number.isNaN(parsed) ? null : parsed;
}

/** Revoked beats expired: a token revoked and then past its expiry was still revoked. */
export function runnerTokenState(
  token: Pick<RunnerTokenMetadata, 'expires_at' | 'revoked_at'>,
  nowMs: number,
): RunnerTokenState {
  if (token.revoked_at !== undefined) return 'revoked';
  const expires = instant(token.expires_at);
  return expires !== null && expires <= nowMs ? 'expired' : 'active';
}

/** A token that can still be used by a runner. */
export function runnerTokenIsLive(
  token: Pick<RunnerTokenMetadata, 'expires_at' | 'revoked_at'>,
  nowMs: number,
): boolean {
  return runnerTokenState(token, nowMs) === 'active';
}

/** A live token whose runner called less than a minute ago. */
export function runnerTokenIsOnline(
  token: Pick<RunnerTokenMetadata, 'expires_at' | 'revoked_at' | 'last_seen_at'>,
  nowMs: number,
): boolean {
  if (!runnerTokenIsLive(token, nowMs)) return false;
  const seen = instant(token.last_seen_at);
  return seen !== null && nowMs - seen >= 0 && nowMs - seen < RUNNER_ONLINE_WINDOW_MS;
}

/** The connection has a runner «на связи»: any of its tokens was seen in the last minute. */
export function connectionRunnerIsOnline(
  detail: Pick<ExecutorConnectionDetail, 'runner_tokens'> | undefined,
  nowMs: number,
): boolean {
  return (detail?.runner_tokens ?? []).some((token) => runnerTokenIsOnline(token, nowMs));
}

/** The token a runner is told to use is one of these: the newest first. */
export function sortedRunnerTokens(tokens: readonly RunnerTokenMetadata[]): readonly RunnerTokenMetadata[] {
  return [...tokens].sort((left, right) => (left.created_at < right.created_at ? 1 : left.created_at > right.created_at ? -1 : 0));
}

/** The detail is of a `pull` connection that holds a live token. */
export function hasLiveRunnerToken(detail: ExecutorConnectionDetail | undefined, nowMs: number): boolean {
  return (detail?.runner_tokens ?? []).some((token) => runnerTokenIsLive(token, nowMs));
}
