/**
 * Contract guard: the frontend's idea of the CSV column list is the seam document's.
 *
 * `OD-11` freezes seventeen columns in one order in `docs/program/P02_SEAMS.md` section 6.
 * `B5` produces them and `B8` downloads them, and the two never meet in code — so the
 * only thing that keeps them agreeing is a check that reads the frozen table and compares.
 *
 * The seam document is read-only here. If this fails, either the table moved and the
 * frontend constant must follow, or someone edited the constant and should not have.
 */

import { describe, expect, it } from 'vitest';

import { CSV_COLUMNS, CSV_ENCODING } from '@/shared/api';
import { SEAMS_PATH, readText } from '../guards/lib/repo';

/** Pull the ordered column names out of the section 6 markdown table. */
function columnsFromSeamDocument(): string[] {
  const document = readText(SEAMS_PATH);
  const section = document.slice(
    document.indexOf('## 6. The CSV column contract'),
    document.indexOf('## 7. API seam'),
  );
  expect(section.length, 'section 6 of P02_SEAMS.md was not found').toBeGreaterThan(200);

  const columns: string[] = [];
  for (const line of section.split('\n')) {
    // Rows look like: | 1 | `project_uid` | `finding.project_uid` |
    const match = /^\|\s*(\d+)\s*\|\s*`([a-z0-9_]+)`\s*\|/.exec(line.trim());
    if (match !== null) {
      expect(Number(match[1]), 'column numbers must run 1..n in order').toBe(columns.length + 1);
      columns.push(match[2] as string);
    }
  }
  return columns;
}

describe('the CSV column contract', () => {
  const fromDocument = columnsFromSeamDocument();

  it('parses seventeen columns out of the seam document', () => {
    expect(fromDocument).toHaveLength(17);
  });

  it('matches the frontend constant exactly, in order', () => {
    expect([...CSV_COLUMNS]).toEqual(fromDocument);
  });

  it('starts with the identity columns and ends with the decision projection', () => {
    expect(CSV_COLUMNS[0]).toBe('project_uid');
    expect(CSV_COLUMNS[16]).toBe('decision_recorded_at');
  });

  it('carries the run state explicitly, so a partial export is not silently empty', () => {
    expect(CSV_COLUMNS).toContain('run_state');
  });

  it('records the bytes the seam document fixes', () => {
    expect(CSV_ENCODING.byteOrderMark).toBe(true);
    expect(CSV_ENCODING.lineEnding).toBe('\r\n');
    expect(CSV_ENCODING.delimiter).toBe(',');
    expect(CSV_ENCODING.nullRepresentation).toBe('');
  });
});

describe('the column check goes red on drift', () => {
  const fromDocument = columnsFromSeamDocument();

  it('detects a reordering', () => {
    const reordered = [...fromDocument];
    [reordered[0], reordered[1]] = [reordered[1] as string, reordered[0] as string];
    expect(reordered).not.toEqual([...CSV_COLUMNS]);
  });

  it('detects a dropped column', () => {
    expect(fromDocument.filter((c) => c !== 'run_state')).not.toEqual([...CSV_COLUMNS]);
  });

  it('detects a renamed column', () => {
    expect(fromDocument.map((c) => (c === 'current_verdict' ? 'verdict' : c))).not.toEqual([
      ...CSV_COLUMNS,
    ]);
  });
});
