/**
 * Two small rules with no test at all before the `W12-WEB` sweep.
 *
 * **`formatInstant` and `formatInstantUtc`** are rendered by the decision history and by every stage row, and they
 * are the strings an operator uses to line a screen up with a log. Replacing a body with `toLocaleString()`, and
 * turning an unparseable value into an em dash, both left the suite green. The first is also a React hydration
 * mismatch -- the server renders one locale and the browser another -- and the second silently destroys the only
 * evidence an operator has of what the server actually sent. Since `UIP-G-13` the stamp on a screen is the
 * reader's local time (`ДД.ММ.ГГГГ ЧЧ:ММ`) and the exact UTC stamp is `formatInstantUtc`; the conversion
 * itself, across zones, is `tests/unit/lib/format-instant.test.ts`. This file keeps the two rules' edge cases
 * (an unreadable value is shown, only an absent one is a dash) and runs in the zone `vitest.config.ts` pins (UTC).
 *
 * **`looksLikeProjectUid`** separates "the URL is malformed" from "the server says not
 * found". The generated pattern is anchored; stripping the anchors off it left the suite
 * green, so `/projects/xxprj_01J9.../edit` would have been spent on a request.
 *
 * Both are pinned to literals. The instant strings are chosen so a UTC render and a
 * local-time render cannot coincide where it matters: the fixture is written in a non-zero offset.
 */

import { describe, expect, it } from 'vitest';

import { formatInstant, formatInstantUtc } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

describe('an instant renders in the reader\'s time, and as a stable UTC stamp for a tooltip', () => {
  it('renders a Z instant as `ДД.ММ.ГГГГ ЧЧ:ММ`', () => {
    expect(formatInstant('2026-09-10T09:00:00.000Z')).toBe('10.09.2026 09:00');
  });

  it('converts an offset instant to the reader\'s time rather than printing it as given', () => {
    // 12:00 at +03:00 is 09:00 UTC, and the pinned zone is UTC.
    expect(formatInstant('2026-09-10T12:00:00+03:00')).toBe('10.09.2026 09:00');
  });

  it('drops the seconds rather than rounding them', () => {
    expect(formatInstant('2026-09-10T09:00:59.987Z')).toBe('10.09.2026 09:00');
  });

  it('renders the exact UTC stamp for a tooltip, with `UTC` in the string so the reader does not have to assume', () => {
    expect(formatInstantUtc('2026-09-10T09:00:00.000Z')).toBe('2026-09-10 09:00:00 UTC');
    expect(formatInstantUtc('2026-09-10T12:00:00+03:00')).toBe('2026-09-10 09:00:00 UTC');
    expect(formatInstantUtc('2026-09-10T09:00:00.987Z')).toBe('2026-09-10 09:00:00 UTC');
    expect(formatInstantUtc('2026-01-01T00:00:00Z')).toBe('2026-01-01 00:00:00 UTC');
  });
});

describe('an instant that cannot be parsed is shown, not hidden', () => {
  it('returns the value the server sent', () => {
    // The em dash means "there was nothing here". A value that arrived and could not be
    // parsed is a different fact, and it is the one an operator needs in order to report it.
    expect(formatInstant('not-an-instant')).toBe('not-an-instant');
    expect(formatInstant('2026-13-45T99:99:99Z')).toBe('2026-13-45T99:99:99Z');
    expect(formatInstantUtc('not-an-instant')).toBe('not-an-instant');
  });

  it('uses the em dash only for an absent instant', () => {
    expect(formatInstant(null)).toBe('—');
    expect(formatInstant(undefined)).toBe('—');
    expect(formatInstant('')).toBe('—');
    expect(formatInstantUtc(null)).toBe('—');
  });
});

describe('a project address is recognised only when the whole string is one', () => {
  it('accepts exactly the contract shape', () => {
    expect(looksLikeProjectUid(`prj_${ULID}`)).toBe(true);
  });

  it('refuses a contract shape with anything before or after it', () => {
    expect(looksLikeProjectUid(`xxprj_${ULID}`)).toBe(false);
    expect(looksLikeProjectUid(`prj_${ULID}yy`)).toBe(false);
    expect(looksLikeProjectUid(`/projects/prj_${ULID}`)).toBe(false);
    expect(looksLikeProjectUid(`prj_${ULID}\nprj_${ULID}`)).toBe(false);
  });

  it('refuses the other aggregates prefixes and a truncated body', () => {
    expect(looksLikeProjectUid(`run_${ULID}`)).toBe(false);
    expect(looksLikeProjectUid(`proj_${ULID}`)).toBe(false);
    expect(looksLikeProjectUid(`prj_${ULID.slice(0, 25)}`)).toBe(false);
    expect(looksLikeProjectUid('prj_')).toBe(false);
    expect(looksLikeProjectUid('')).toBe(false);
  });
});
