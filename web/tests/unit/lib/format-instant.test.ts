/**
 * `UIP-G-13`: the one place that prints a moment of time (`shared/lib/format-instant.ts`).
 *
 * The screens show local time in the original's form. A function that ignored the zone would still pass every test that
 * runs in one zone, and `vitest.config.ts` pins that zone to UTC, so the proof is here: the same instant is printed in
 * three explicit zones and the three strings must differ exactly as the zones do. Each case below names what a wrong
 * implementation would print instead (UTC for every zone, the process zone for every zone, the `ru-RU` locale's own
 * «14.11.2026, 09:12» with a comma, «24:00» for midnight).
 */

import { describe, expect, it } from 'vitest';

import { formatClock, formatDayMonth, formatInstant, formatInstantUtc, formatTime } from '@/shared/lib';

const MOSCOW = 'Europe/Moscow'; // UTC+3 all year
const VLADIVOSTOK = 'Asia/Vladivostok'; // UTC+10 all year
const UTC = 'UTC';

/** 2026-11-14 09:12:34 UTC. */
const MORNING = '2026-11-14T09:12:34.567Z';
/** 2026-11-14 23:30:05 UTC: the next day in both Moscow and Vladivostok. */
const LATE = '2026-11-14T23:30:05Z';

describe('formatInstant: «ДД.ММ.ГГГГ ЧЧ:ММ» in the named zone', () => {
  it('prints the same instant in each zone\'s own time', () => {
    expect(formatInstant(MORNING, UTC)).toBe('14.11.2026 09:12');
    expect(formatInstant(MORNING, MOSCOW)).toBe('14.11.2026 12:12');
    expect(formatInstant(MORNING, VLADIVOSTOK)).toBe('14.11.2026 19:12');
  });

  it('moves the date as well as the hour when the zone is on the next day', () => {
    expect(formatInstant(LATE, UTC)).toBe('14.11.2026 23:30');
    expect(formatInstant(LATE, MOSCOW)).toBe('15.11.2026 02:30');
    expect(formatInstant(LATE, VLADIVOSTOK)).toBe('15.11.2026 09:30');
  });

  it('carries across the end of a year', () => {
    expect(formatInstant('2026-12-31T22:00:00Z', MOSCOW)).toBe('01.01.2027 01:00');
    expect(formatInstant('2027-01-01T01:00:00Z', 'America/New_York')).toBe('31.12.2026 20:00');
  });

  it('follows a zone\'s summer time, which a fixed offset would not', () => {
    expect(formatInstant('2026-07-01T12:00:00Z', 'America/New_York')).toBe('01.07.2026 08:00');
    expect(formatInstant('2026-01-01T12:00:00Z', 'America/New_York')).toBe('01.01.2026 07:00');
  });

  it('is not the locale\'s own string: no comma, two-digit day and month, a dot and a space of its own', () => {
    for (const zone of [UTC, MOSCOW, VLADIVOSTOK]) {
      expect(formatInstant(MORNING, zone)).toMatch(/^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$/);
    }
    expect(formatInstant('2026-03-05T04:07:00Z', UTC)).toBe('05.03.2026 04:07');
  });

  it('prints midnight as 00:00, never 24:00', () => {
    expect(formatInstant('2026-11-14T21:00:00Z', MOSCOW)).toBe('15.11.2026 00:00');
    expect(formatInstant('2026-11-15T00:00:00Z', UTC)).toBe('15.11.2026 00:00');
  });

  it('does not let one zone\'s call leak into the next (the formatters are cached per zone)', () => {
    expect(formatInstant(MORNING, MOSCOW)).toBe('14.11.2026 12:12');
    expect(formatInstant(MORNING, UTC)).toBe('14.11.2026 09:12');
    expect(formatInstant(MORNING, VLADIVOSTOK)).toBe('14.11.2026 19:12');
    expect(formatInstant(MORNING, MOSCOW)).toBe('14.11.2026 12:12');
  });

  it('reads an offset instant as the instant it is, not as the clock it was written with', () => {
    // 12:00 at +03:00 is 09:00 UTC.
    expect(formatInstant('2026-11-14T12:00:00+03:00', UTC)).toBe('14.11.2026 09:00');
    expect(formatInstant('2026-11-14T12:00:00+03:00', VLADIVOSTOK)).toBe('14.11.2026 19:00');
  });

  it('takes the reader\'s own zone when none is named (the zone the test run pins is UTC)', () => {
    expect(formatInstant(MORNING)).toBe(formatInstant(MORNING, UTC));
  });

  it('accepts epoch milliseconds and a Date as well as the contract\'s text', () => {
    const at = Date.parse(MORNING);
    expect(formatInstant(at, MOSCOW)).toBe('14.11.2026 12:12');
    expect(formatInstant(new Date(at), MOSCOW)).toBe('14.11.2026 12:12');
  });

  it('shows what it cannot read and dashes only what is absent', () => {
    expect(formatInstant('not-an-instant', MOSCOW)).toBe('not-an-instant');
    expect(formatInstant(null, MOSCOW)).toBe('—');
    expect(formatInstant(undefined, MOSCOW)).toBe('—');
    expect(formatInstant('', MOSCOW)).toBe('—');
  });
});

describe('formatClock, formatTime and formatDayMonth: the short forms in the named zone', () => {
  it('formatClock prints «ЧЧ:ММ:СС», with the seconds', () => {
    expect(formatClock(MORNING, UTC)).toBe('09:12:34');
    expect(formatClock(MORNING, MOSCOW)).toBe('12:12:34');
    expect(formatClock(MORNING, VLADIVOSTOK)).toBe('19:12:34');
    expect(formatClock('2026-11-14T21:00:00Z', MOSCOW)).toBe('00:00:00');
  });

  it('formatTime prints «ЧЧ:ММ»', () => {
    expect(formatTime(MORNING, UTC)).toBe('09:12');
    expect(formatTime(MORNING, MOSCOW)).toBe('12:12');
    expect(formatTime(MORNING, VLADIVOSTOK)).toBe('19:12');
    expect(formatTime('2026-11-14T23:59:59Z', UTC)).toBe('23:59');
  });

  it('formatDayMonth prints «ДД.ММ» of the zone\'s own day', () => {
    expect(formatDayMonth(LATE, UTC)).toBe('14.11');
    expect(formatDayMonth(LATE, MOSCOW)).toBe('15.11');
    expect(formatDayMonth(LATE, VLADIVOSTOK)).toBe('15.11');
    expect(formatDayMonth('2026-03-05T04:07:00Z', UTC)).toBe('05.03');
  });

  it('agree with formatInstant on the same instant and zone', () => {
    for (const zone of [UTC, MOSCOW, VLADIVOSTOK]) {
      const stamp = formatInstant(LATE, zone);
      expect(stamp).toBe(`${formatDayMonth(LATE, zone)}.2026 ${formatTime(LATE, zone)}`);
      expect(formatClock(LATE, zone)).toBe(`${formatTime(LATE, zone)}:05`);
    }
  });

  it('take the reader\'s own zone when none is named, accept every input, and treat absent and unreadable alike', () => {
    expect(formatClock(MORNING)).toBe(formatClock(MORNING, UTC));
    expect(formatTime(Date.parse(MORNING))).toBe('09:12');
    expect(formatDayMonth(new Date(MORNING))).toBe('14.11');
    for (const short of [formatClock, formatTime, formatDayMonth]) {
      expect(short(null)).toBe('—');
      expect(short(undefined)).toBe('—');
      expect(short('')).toBe('—');
      expect(short('not-an-instant')).toBe('not-an-instant');
    }
  });
});

describe('formatInstantUtc: the stamp that reads the same everywhere', () => {
  it('prints «ГГГГ-ММ-ДД ЧЧ:ММ:СС UTC», byte for byte what formatInstant printed before UIP-G-13', () => {
    expect(formatInstantUtc(MORNING)).toBe('2026-11-14 09:12:34 UTC');
    expect(formatInstantUtc('2026-09-10T09:00:00.000Z')).toBe('2026-09-10 09:00:00 UTC');
    expect(formatInstantUtc('2026-01-01T00:00:00Z')).toBe('2026-01-01 00:00:00 UTC');
  });

  it('converts an offset instant to UTC and drops, not rounds, the sub-second part', () => {
    expect(formatInstantUtc('2026-09-10T12:00:00+03:00')).toBe('2026-09-10 09:00:00 UTC');
    expect(formatInstantUtc('2026-09-10T09:00:00.987Z')).toBe('2026-09-10 09:00:00 UTC');
  });

  it('does not depend on a zone: the local functions of the same instant differ, this one does not', () => {
    expect(formatInstant(LATE, MOSCOW)).not.toBe(formatInstant(LATE, UTC));
    expect(formatInstantUtc(LATE)).toBe('2026-11-14 23:30:05 UTC');
    expect(formatInstantUtc(new Date(LATE))).toBe('2026-11-14 23:30:05 UTC');
    expect(formatInstantUtc(Date.parse(LATE))).toBe('2026-11-14 23:30:05 UTC');
  });

  it('shows what it cannot read and dashes only what is absent', () => {
    expect(formatInstantUtc('not-an-instant')).toBe('not-an-instant');
    expect(formatInstantUtc(null)).toBe('—');
    expect(formatInstantUtc(undefined)).toBe('—');
    expect(formatInstantUtc('')).toBe('—');
  });
});
