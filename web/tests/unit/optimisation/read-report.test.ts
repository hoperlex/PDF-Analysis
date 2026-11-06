/**
 * `UI-PARITY-DENSE`: «Как прочитан файл» on the project's optimisation tab is a block a reader needs when the file was
 * not read whole, and one click away when it was. It was seven lines open under every price list.
 *
 * The report's text stays in the markup either way (a `<details>` is closed, not removed), so the render tests that look for
 * a column or a skipped row still find them; what changes is that the block is open exactly when something was skipped, left
 * unread or warned about.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { PriceListPositionsView } from '@/widgets/project-optimisation';

import { newClient, renderScreen } from '../screens/harness';
import { positionPage } from './fixtures';

const noop = (): void => undefined;

function report(overrides: Partial<ReturnType<typeof positionPage>['parse_report']>): string {
  const base = positionPage();
  return renderScreen(
    newClient(),
    createElement(PriceListPositionsView, { page: { ...base, parse_report: { ...base.parse_report, ...overrides } }, onOffset: noop }),
  );
}

const CLEAN = { skipped_rows: 0, skipped: [], skipped_by_reason: [], warnings: [], warnings_by_reason: [], ambiguous_columns: [] };

describe('how the file was read', () => {
  it('is open when a row was skipped, a column left unread or a warning raised', () => {
    expect(report({})).toMatch(/<details[^>]*data-price-list-report=""[^>]*\sopen=""/);
    expect(report({ ...CLEAN, skipped_rows: 2 })).toMatch(/data-price-list-report=""[^>]*\sopen=""/);
    expect(report({ ...CLEAN, warnings: [{ row: 5, reason: 'section_unrecognised' }] })).toMatch(/data-price-list-report=""[^>]*\sopen=""/);
    expect(report({ ...CLEAN, ambiguous_columns: [{ field: 'mark', headers: ['Марка', 'Тип'] }] })).toMatch(/data-price-list-report=""[^>]*\sopen=""/);
  });

  it('is closed, and still in the markup, when the file was read whole', () => {
    const markup = report(CLEAN);
    expect(markup).toMatch(/<details[^>]*data-price-list-report=""/);
    expect(markup).not.toMatch(/data-price-list-report=""[^>]*\sopen=""/);
    expect(markup).toContain('<summary>Как прочитан файл</summary>');
    expect(markup).toContain('Наименование');
  });
});
