/**
 * «Обновлено ЧЧ:ММ:СС» and the line that replaces it when the data may be out of date.
 *
 * The clock is a prop, so every case fixes "now" and nothing waits. Timestamps are built from
 * local-time components because the label is local time.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { OPERATIONAL_LIST_STALE_MS } from '@/shared/config';
import { UpdateTime, updateTimeLabel } from '@/entities/execution';

const UPDATED = new Date(2026, 10, 4, 14, 5, 9).getTime();
const SECOND = 1_000;

function render(dataUpdatedAt: number, failed: boolean, now: number): string {
  return renderToStaticMarkup(createElement(UpdateTime, { dataUpdatedAt, failed, now }));
}

/** The text a person reads, without the markup around it. */
function text(markup: string): string {
  return markup.replace(/<[^>]*>/g, '');
}

describe('updateTimeLabel', () => {
  it('writes local time as two-digit ЧЧ:ММ:СС', () => {
    expect(updateTimeLabel(UPDATED)).toBe('14:05:09');
    expect(updateTimeLabel(new Date(2026, 10, 4, 0, 0, 0).getTime())).toBe('00:00:00');
    expect(updateTimeLabel(new Date(2026, 10, 4, 23, 59, 59).getTime())).toBe('23:59:59');
  });
});

describe('UpdateTime', () => {
  it('shows «Обновлено» with the time of the last successful read while the data is fresh', () => {
    const markup = render(UPDATED, false, UPDATED + 4 * SECOND);
    expect(text(markup)).toBe('Обновлено 14:05:09');
    expect(markup).toContain('data-update-state="fresh"');
    expect(markup).toContain(`dateTime="${new Date(UPDATED).toISOString()}"`);
    expect(markup).not.toContain('устареть');
    // A line that redraws every ten seconds must not be announced every ten seconds.
    expect(markup).not.toContain('role=');
  });

  it('is still fresh exactly at three intervals', () => {
    expect(render(UPDATED, false, UPDATED + OPERATIONAL_LIST_STALE_MS)).toContain('data-update-state="fresh"');
  });

  it('says the data may be out of date once the last success is older than three intervals', () => {
    const markup = render(UPDATED, false, UPDATED + OPERATIONAL_LIST_STALE_MS + 1);
    expect(text(markup)).toBe('Данные могли устареть: последнее обновление 14:05:09');
    expect(markup).toContain('data-update-state="stale"');
    expect(markup).toContain('role="status"');
    expect(text(markup)).not.toContain('Обновлено');
  });

  it('says it after a failed read even though the last success was a second ago', () => {
    const markup = render(UPDATED, true, UPDATED + SECOND);
    expect(text(markup)).toBe('Данные могли устареть: последнее обновление 14:05:09');
    expect(markup).toContain('data-update-state="stale"');
    expect(text(markup)).not.toContain('Обновлено');
  });

  it('keeps naming the last success, not the failed attempt', () => {
    const later = UPDATED + 10 * 60 * SECOND;
    expect(text(render(UPDATED, true, later))).toContain('14:05:09');
    expect(text(render(UPDATED, true, later))).not.toContain(updateTimeLabel(later));
  });

  it('draws nothing before the first successful read', () => {
    expect(render(0, false, UPDATED)).toBe('');
    expect(render(0, true, UPDATED)).toBe('');
  });
});
