/**
 * The export panel: the right run, the right columns, and no invented CSV.
 *
 * Two things are being protected here.
 *
 * **The column contract is consumed, not restated.** `A5` froze `CSV_COLUMNS` in the shared
 * layer against `P02_SEAMS.md` §6 and checks it there with a contract test. The panel's job
 * is to display what the server will send, so it reads that constant — and this suite
 * asserts the rendered list *is* that constant, in order. A renamed column then changes
 * what the panel shows and this test with it; a panel carrying its own copy of the
 * seventeen names would keep promising the old one.
 *
 * **The browser never builds a CSV.** There is no row assembly, no encoding and no
 * serialization anywhere in this session's tree. The panel states the encoding facts and
 * downloads the server's bytes.
 */

import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import type { DownloadSink } from '@/features/export-run';
import { deliverDownload } from '@/features/export-run';
import type { RunState } from '@/shared/api';
import {
  CSV_COLUMNS,
  CSV_ENCODING,
  EXPORTABLE_RUN_STATES,
  RUN_STATE_VALUES,
  csvFileName,
  exportRunCsv,
  isExportableRunState,
} from '@/shared/api';
import { ExportPanel } from '@/widgets/export-panel';

import { RUN_ID, render } from '../review/fixtures';

function panel(runState: RunState, overrides: Record<string, unknown> = {}) {
  return render(
    createElement(ExportPanel, {
      runId: RUN_ID,
      runState,
      providerMode: 'recorded',
      onExport: () => {},
      ...overrides,
    }),
  );
}

describe('which runs are offered an export', () => {
  it.each(EXPORTABLE_RUN_STATES)('offers it for %s', (state) => {
    const markup = panel(state);
    expect(markup).toContain('data-exportable="true"');
    expect(markup).toContain('data-intent="export"');
  });

  it.each(RUN_STATE_VALUES.filter((state) => !isExportableRunState(state)))(
    'does not offer it for %s',
    (state) => {
      const markup = panel(state);
      expect(markup).toContain('data-exportable="false"');
      expect(markup).not.toContain('data-intent="export"');
      // No retry affordance: no retry changes a terminal, and a non-terminal run is not
      // refused, it is simply not finished.
      expect(markup).not.toContain('Повторить');
    },
  );

  it('exports a partial run rather than refusing it', () => {
    // OD-11: a `partial` run is exported with its degradation carried in the `run_state`
    // column, not refused and not silently emptied.
    expect(isExportableRunState('partial')).toBe(true);
    const markup = panel('partial');
    expect(markup).toContain('data-exportable="true"');
    expect(markup).toContain('data-run-state="partial"');
  });

  it('covers every contract run state in one branch or the other', () => {
    // A state added to the contract without a decision here would otherwise silently fall
    // into the not-exportable branch.
    for (const state of RUN_STATE_VALUES) {
      const markup = panel(state);
      const exportable = markup.includes('data-exportable="true"');
      expect(exportable).toBe(isExportableRunState(state));
    }
  });
});

describe('the column contract is consumed, not restated', () => {
  it('renders exactly CSV_COLUMNS, in order', () => {
    const markup = panel('published');
    const rendered = [...markup.matchAll(/data-csv-column="([^"]+)"/g)].map((match) => match[1]);
    expect(rendered).toEqual([...CSV_COLUMNS]);
  });

  it('states the column count from the constant', () => {
    expect(panel('published')).toContain(`Колонок: ${CSV_COLUMNS.length}`);
  });

  it('states the encoding facts the seam fixes', () => {
    const markup = panel('published');
    expect(markup).toContain(CSV_ENCODING.charset);
    expect(CSV_ENCODING.byteOrderMark).toBe(true);
    // The BOM is there because the intended reader opens the file in Excel, which
    // otherwise mis-decodes Cyrillic — so the panel says so rather than leaving the user
    // to discover it.
    expect(markup).toContain('меткой порядка байтов');
    expect(markup).toContain(CSV_ENCODING.quoting);
  });

  it('builds no CSV of its own', () => {
    // The panel prints column *names*; it never prints a delimiter-joined row. If this
    // ever fails, something started assembling a file in the browser from cached data.
    const markup = panel('published');
    expect(markup).not.toContain(CSV_ENCODING.lineEnding);
    expect(markup).not.toContain('project_uid,document_uid');
  });
});

describe('the download targets the exact run', () => {
  it('names the file after the run id', () => {
    expect(csvFileName(RUN_ID)).toBe(`${RUN_ID}-findings.csv`);
    expect(panel('published')).toContain(csvFileName(RUN_ID));
  });

  it('requests GET /runs/{run_id}/export.csv and nothing else', async () => {
    const calls: string[] = [];
    await exportRunCsv(
      { path: { run_id: RUN_ID } },
      {
        baseUrl: 'https://api.test',
        fetch: async (url) => {
          calls.push(url);
          return new Response(new Blob(['﻿project_uid\r\n']), {
            status: 200,
            headers: { 'Content-Type': 'text/csv', 'X-Correlation-Id': 'corr-9' },
          });
        },
      },
    );
    // The project and version this file covers are the ones the run belongs to. There is
    // no way to ask for a mismatched triple, because the operation takes only `run_id`.
    expect(calls).toEqual([`https://api.test/runs/${RUN_ID}/export.csv`]);
  });

  it('reports the download once it has happened', () => {
    const markup = panel('published', { lastFileName: csvFileName(RUN_ID) });
    expect(markup).toContain(`data-last-file="${csvFileName(RUN_ID)}"`);
  });
});

describe('delivering the bytes', () => {
  function fakeSink(overrides: Partial<DownloadSink> = {}): DownloadSink & { saved: string[] } {
    const saved: string[] = [];
    return {
      saved,
      createObjectUrl: vi.fn(() => 'blob:https://app.test/csv'),
      saveAs: vi.fn((_url: string, fileName: string) => {
        saved.push(fileName);
      }),
      revokeObjectUrl: vi.fn(),
      ...overrides,
    } as DownloadSink & { saved: string[] };
  }

  it('creates, saves and revokes', () => {
    const sink = fakeSink();
    deliverDownload(sink, new Blob(['x']), 'run-findings.csv');

    expect(sink.createObjectUrl).toHaveBeenCalledTimes(1);
    expect(sink.saveAs).toHaveBeenCalledWith('blob:https://app.test/csv', 'run-findings.csv');
    expect(sink.revokeObjectUrl).toHaveBeenCalledWith('blob:https://app.test/csv');
  });

  it('revokes even when saving throws', () => {
    // An object URL that is not revoked pins the whole CSV in memory for the lifetime of
    // the document, and the throw is exactly the case where nobody is around to clean up.
    const sink = fakeSink({
      saveAs: vi.fn(() => {
        throw new Error('the browser refused the download');
      }),
    });

    expect(() => deliverDownload(sink, new Blob(['x']), 'run-findings.csv')).toThrow(
      'the browser refused the download',
    );
    expect(sink.revokeObjectUrl).toHaveBeenCalledWith('blob:https://app.test/csv');
  });
});

describe('the panel holds no polling state', () => {
  it('offers no progress, no status and nothing to poll', () => {
    // The export endpoint is synchronous: nothing is created, so there is no export
    // resource, no export identity and nothing to poll (seam §7).
    const markup = panel('published');
    expect(markup).not.toContain('polling');
    expect(markup).not.toContain('progress');
    expect(markup).not.toContain('export_id');
  });
});
