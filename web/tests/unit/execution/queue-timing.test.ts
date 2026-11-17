/**
 * The queue row's timing line (`widgets/execution-queue/model/timing.ts`): the original's «ЧЧ:ММ → ЧЧ:ММ · длительность»,
 * in the reader's time, with the day where it is not the same day. The zone is the one `vitest.config.ts` pins (UTC) unless a test
 * names one.
 */

import { describe, expect, it } from 'vitest';

import { durationLabel, queueTiming } from '@/widgets/execution-queue/model/timing';
import { QUEUE_PERIOD_OPTIONS, isQueuePeriod, queuePeriodStart } from '@/_pages/queue/model/period';

describe('the duration', () => {
  it('prints the two largest units that are not zero', () => {
    expect(durationLabel(0)).toBe('0 с');
    expect(durationLabel(45_000)).toBe('45 с');
    expect(durationLabel(60_000)).toBe('1 мин');
    expect(durationLabel(510_000)).toBe('8 мин 30 с');
    expect(durationLabel(3_600_000)).toBe('1 ч');
    expect(durationLabel(7_500_000)).toBe('2 ч 5 мин');
    expect(durationLabel(-5)).toBe('0 с');
  });
});

describe('the timing of a job', () => {
  it('has none for a job that neither started nor finished', () => {
    expect(queueTiming({}, 1)).toBeNull();
    expect(queueTiming({ started_at: 'not a time' }, null)).toBeNull();
  });

  it('names start, end and the span of a finished job; the end carries a day only on another day', () => {
    expect(queueTiming({ started_at: '2026-10-09T10:01:00Z', finished_at: '2026-10-09T10:09:30Z' }, null))
      .toEqual({ start: '09.10 10:01', end: '10:09', duration: '8 мин 30 с' });
    expect(queueTiming({ started_at: '2026-10-09T23:50:00Z', finished_at: '2026-10-10T00:20:00Z' }, null))
      .toEqual({ start: '09.10 23:50', end: '10.10 00:20', duration: '30 мин' });
  });

  it('measures a running job to the last read, and not at all without one', () => {
    const asOf = Date.parse('2026-10-09T10:05:00Z');
    expect(queueTiming({ started_at: '2026-10-09T10:01:00Z' }, asOf)).toEqual({ start: '09.10 10:01', end: null, duration: '4 мин' });
    expect(queueTiming({ started_at: '2026-10-09T10:01:00Z' }, null)).toEqual({ start: '09.10 10:01', end: null, duration: null });
  });

  it('reads the clock and the day in the reader\'s zone, so a job across the reader\'s midnight carries its end day', () => {
    // 23:50 and 00:20 UTC are 02:50 and 03:20 in Moscow (the same day there), and 09:50 and 10:20 in Vladivostok.
    const job = { started_at: '2026-10-09T23:50:00Z', finished_at: '2026-10-10T00:20:00Z' };
    expect(queueTiming(job, null, 'Europe/Moscow')).toEqual({ start: '10.10 02:50', end: '03:20', duration: '30 мин' });
    expect(queueTiming(job, null, 'Asia/Vladivostok')).toEqual({ start: '10.10 09:50', end: '10:20', duration: '30 мин' });
    // 20:50Z to 21:20Z crosses Moscow's midnight but not UTC's.
    const evening = { started_at: '2026-10-09T20:50:00Z', finished_at: '2026-10-09T21:20:00Z' };
    expect(queueTiming(evening, null, 'UTC')).toEqual({ start: '09.10 20:50', end: '21:20', duration: '30 мин' });
    expect(queueTiming(evening, null, 'Europe/Moscow')).toEqual({ start: '09.10 23:50', end: '10.10 00:20', duration: '30 мин' });
  });

  it('keeps the end of a job that finished without ever starting', () => {
    expect(queueTiming({ finished_at: '2026-10-09T10:09:30Z' }, null)).toEqual({ start: null, end: '09.10 10:09', duration: null });
  });
});

describe('the period filter', () => {
  const now = new Date('2026-10-09T12:00:00Z');

  it('offers four choices and knows only them', () => {
    expect(QUEUE_PERIOD_OPTIONS.map((option) => option.value)).toEqual(['all', 'today', 'week', 'month']);
    expect(isQueuePeriod('week')).toBe(true);
    expect(isQueuePeriod('year')).toBe(false);
  });

  it('begins at no instant for «За всё время» and at a whole number of days back for the others', () => {
    expect(queuePeriodStart('all', now)).toBeUndefined();
    expect(queuePeriodStart('week', now)).toBe('2026-10-02T12:00:00.000Z');
    expect(queuePeriodStart('month', now)).toBe('2026-09-09T12:00:00.000Z');
  });

  it('begins «Сегодня» at a midnight that is not after now and less than a day before it', () => {
    const start = Date.parse(queuePeriodStart('today', now) ?? '');
    expect(start).toBeLessThanOrEqual(now.getTime());
    expect(now.getTime() - start).toBeLessThan(24 * 60 * 60 * 1000 + 60 * 60 * 1000);
    expect(new Date(start).getMinutes() % 60).toBe(0);
  });
});
