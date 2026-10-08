/**
 * The guest throttle: a token bucket per client on the two forms a stranger can post.
 *
 * `W49-PLAN.md` §3.5. `POST /bff/v1/session` (the exchange) and `POST /bff/v1/registration`
 * are reached without a session, and each costs the API real work — a failed sign-in is two
 * PBKDF2 derivations (the exchange and the registration status read), an application is one
 * more and a row. So each request a guest makes takes one token from that guest's bucket;
 * an empty bucket refuses the request **before** the body is read or anything is sent, and
 * the route handler answers the form with `303` to its screen and the `throttled` refusal.
 * Both doors share one bucket per client: they are the same guest spending the same API's
 * work, and two buckets would simply double what a guest may spend by alternating.
 *
 * ## Whose bucket
 *
 * A Next 15 route handler is handed no peer address, so the key is the `X-Real-IP` header —
 * which both proxy configurations **set** from `$remote_addr` — and it is believed **only**
 * when the deployment says a proxy is in front (`AUDITMANAGER_BEHIND_PROXY=1`, read by
 * `@/shared/config/proxy-trust`). Without that flag a client could write the header itself,
 * so every request shares **one** bucket: stricter, never looser.
 *
 * **`X-Forwarded-For` is never read.** Its first element is whatever the client wrote — nginx
 * appends to it — so a key taken from it would give a guest a fresh bucket per request for
 * the price of a header. `web/tests/unit/session/guest-throttle.test.ts` forges it and
 * asserts the bucket does not move.
 *
 * ## What the refusal says, and why it may say it
 *
 * `W40-LIMIT` decided **not** to tell a sign-in screen that an *account* is throttled: that
 * would say "this account exists and somebody is attacking it right now". This bucket is
 * about the **caller**, not about any account — the same refusal comes back whichever login
 * was typed, or none — so it reveals nothing about anybody but the person reading it.
 *
 * ## Memory
 *
 * Process memory, on `globalThis` for the register's reason (two module graphs, one process).
 * The table is bounded: past {@link MAX_TRACKED_CLIENTS} the least recently seen client is
 * forgotten. That gives a guest who controls that many addresses a fresh bucket — and a guest
 * with that many addresses has already defeated any per-address limit, so the bound costs
 * nothing a per-address throttle ever bought. A restart forgets every bucket, which forgives
 * every guest at once; that is a throttle's ordinary failure direction, not a fault.
 */

/** How many requests a guest may make at once before waiting. */
export const GUEST_BUCKET_CAPACITY = 10;

/** One token comes back every this many milliseconds: ten a minute, sustained. */
export const GUEST_BUCKET_REFILL_MS = 6_000;

/** How many clients the table remembers before forgetting the least recently seen. */
export const MAX_TRACKED_CLIENTS = 10_000;

/** The header the proxy sets from the peer address. Lowercase, as `Headers` reads it. */
export const CLIENT_ADDRESS_HEADER = 'x-real-ip';

/** The key every request shares when no proxy is trusted. Not an address, so never a collision. */
export const SHARED_BUCKET_KEY = '(every guest: no proxy is trusted)';

/**
 * The key for a request that came through a trusted proxy without a usable address.
 *
 * The proxy always sets the header, so this is a misconfiguration; such requests share one
 * bucket rather than each getting a fresh one.
 */
export const UNIDENTIFIED_BUCKET_KEY = '(behind the proxy, no address)';

/** Longer than any textual IP address; a value past it is not one the proxy wrote. */
const MAX_ADDRESS_LENGTH = 64;

interface Bucket {
  readonly tokens: number;
  readonly updatedAt: number;
}

const BUCKETS_KEY = Symbol.for('auditmanager.web.guest-throttle');

function buckets(): Map<string, Bucket> {
  const host = globalThis as unknown as Record<symbol, Map<string, Bucket> | undefined>;
  const existing = host[BUCKETS_KEY];
  if (existing !== undefined) return existing;
  const created = new Map<string, Bucket>();
  host[BUCKETS_KEY] = created;
  return created;
}

/**
 * Whose bucket a request spends from.
 *
 * `behindProxy` is a parameter rather than a read so that the rule is visible in one line and
 * testable without the environment; the route handler passes `isBehindProxy()`.
 */
export function guestClientKey(request: Request, behindProxy: boolean): string {
  if (!behindProxy) return SHARED_BUCKET_KEY;
  const address = request.headers.get(CLIENT_ADDRESS_HEADER)?.trim() ?? '';
  if (address.length === 0 || address.length > MAX_ADDRESS_LENGTH) return UNIDENTIFIED_BUCKET_KEY;
  return `ip:${address}`;
}

/**
 * Take one token from `key`'s bucket. True when the request is admitted.
 *
 * A refused request takes nothing — there is nothing to take — but its time is recorded, so
 * the fraction of a token that has come back is carried rather than lost.
 */
export function admitGuest(key: string, now: number = Date.now()): boolean {
  const table = buckets();
  const previous = table.get(key);
  const elapsed = previous === undefined ? 0 : Math.max(0, now - previous.updatedAt);
  const available =
    previous === undefined
      ? GUEST_BUCKET_CAPACITY
      : Math.min(GUEST_BUCKET_CAPACITY, previous.tokens + elapsed / GUEST_BUCKET_REFILL_MS);
  const admitted = available >= 1;
  // Deleted and re-inserted, so the map's insertion order is least-recently-seen first.
  table.delete(key);
  table.set(key, { tokens: admitted ? available - 1 : available, updatedAt: now });
  while (table.size > MAX_TRACKED_CLIENTS) {
    const oldest = table.keys().next().value;
    if (oldest === undefined) break;
    table.delete(oldest);
  }
  return admitted;
}

/** Forget every bucket. For tests, and for nothing else. */
export function forgetEveryGuestBucket(): void {
  buckets().clear();
}

/** How many clients the table remembers. For a test of the bound, never for a decision. */
export function trackedGuestCount(): number {
  return buckets().size;
}
