/**
 * A dot of «Календарь запаса» is a link, as the original's dot opens the project: it leads to the assignment's document, or
 * to its project when the assignment names no document. An administrator selects with Ctrl/Cmd+click or the space bar and
 * Esc clears the selection (the handlers need a browser; the static render shows the link and the selection mark).
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { NO_ENGINEER_FILTER } from '@/entities/work-schedule';
import { ReserveCalendarView } from '@/widgets/reserve-calendar';
import { newClient, renderScreen } from '../screens/harness';

import { assignmentUid, reserveFixture } from './fixtures';

const draw = (admin: boolean, initialSelection: readonly string[] = []) => renderScreen(newClient(), createElement(ReserveCalendarView, {
  reserve: reserveFixture(), admin, today: '2026-11-04', filter: NO_ENGINEER_FILTER, onStart: () => {}, onEngineer: () => {}, initialSelection,
} as unknown as Parameters<typeof ReserveCalendarView>[0]));

describe('the dots of the reserve', () => {
  it('lead to the document of the assignment, or to its project when it names none, for an expert as well as for an administrator', () => {
    for (const admin of [false, true]) {
      const markup = draw(admin);
      expect(markup).toContain('href="/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q06"');
      expect(markup).toContain('href="/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B"');
      expect(markup).not.toContain('aria-pressed');
    }
  });

  it('mark the selected dots for an administrator only, and say how to select', () => {
    const first = assignmentUid(1);
    expect(draw(true, [first])).toContain('aria-current="true"');
    expect(draw(true)).toContain('Esc снимает выбор');
    expect(draw(false, [first])).not.toContain('aria-current="true"');
    expect(draw(false)).not.toContain('Esc снимает выбор');
  });
});
