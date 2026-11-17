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
 * nineteen names would keep promising the old one.
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
import { ExportBarView, ExportPanel, xlsxFailure } from '@/widgets/export-panel';
import type { ExportBarViewProps, ExportFileState, ExportPackageState } from '@/widgets/export-panel';

import { mountLive } from '../analysis-settings/live-render';
import { RUN_ID, render } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';

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

  it('renders a typed fault instead of treating an unknown state as not exportable', () => {
    const markup = panel('future_state' as RunState);
    expect(markup).toContain('data-export-fault="closed-vocabulary"');
    expect(markup).toContain('Прогон содержит неизвестное состояние.');
    expect(markup).not.toContain('data-exportable=');
    expect(markup).not.toContain('future_state');
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

/**
 * `UIP-S06-05`: the files of «Разбор» as one button «Скачать ▾» and, for an expert, «Загрузить решения», with the «?» beside them.
 * Every file, every condition under which it is offered and every refusal the panel said before it says still; the frame, the
 * title «Выгрузка» and the state badge inside the panel are gone (the header line of the page says the state and the mode).
 */
describe('the bar of «Разбор»', () => {
  const bar = (runState: RunState, overrides: Record<string, unknown> = {}) => panel(runState, { layout: 'bar', ...overrides });
  const SCOPE = 'CSV и Excel: выбранный отбор по вердикту.';
  const VERSION = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

  it('has no frame, no title and no state badge of its own', () => {
    for (const state of EXPORTABLE_RUN_STATES) {
      const markup = bar(state);
      expect(markup).not.toContain('Выгрузка');
      expect(markup).not.toContain('<h3');
      expect(markup).not.toContain('am-export__header');
      expect(markup).not.toContain('data-run-state');
      expect(markup).not.toContain('data-provider-mode');
    }
  });

  it('puts the files of an exportable run in one button, CSV and Excel in it, and nothing else on the row', () => {
    const markup = bar('published');
    expect(markup).toContain('data-export-menu');
    expect(markup).toContain('Скачать');
    expect(markup).toContain('data-intent="export"');
    expect(markup).toContain('data-intent="export-xlsx"');
    expect(markup).toContain('data-export-format="csv"');
    expect(markup).toContain('data-export-format="xlsx"');
    // The CSV is named after the run where the button used to carry the name.
    expect(markup).toContain(`title="${csvFileName(RUN_ID)}"`);
    expect(markup.indexOf('data-export-menu')).toBeLessThan(markup.indexOf('data-intent="export"'));
    expect(markup).not.toContain('export-audit-package');
    expect(markup).not.toContain('data-decision-import');
  });

  it.each(EXPORTABLE_RUN_STATES)('offers the files for %s and none of them for a run without a result', (state) => {
    expect(bar(state)).toContain('data-exportable="true"');
    for (const other of RUN_STATE_VALUES.filter((candidate) => !isExportableRunState(candidate))) {
      const markup = bar(other);
      expect(markup).toContain('data-exportable="false"');
      expect(markup).toContain('У этого прогона нет результата для выгрузки');
      expect(markup).not.toContain('data-export-menu');
      expect(markup).not.toContain('data-intent="export"');
      expect(markup).not.toContain('data-intent="export-xlsx"');
    }
  });

  it('offers the audit package only where the page names the version, in the same menu', () => {
    const markup = bar('published', { auditPackage: { versionUid: VERSION } });
    expect(markup).toContain('data-intent="export-audit-package"');
    expect(markup).toContain('data-export-format="audit-package"');
    expect(markup).toContain('Пакет аудита');
    expect(markup).toContain('title="ZIP одного прогона: CSV замечаний');
    expect(markup.indexOf('data-export-menu')).toBeLessThan(markup.indexOf('data-intent="export-audit-package"'));
    expect(bar('queued', { auditPackage: { versionUid: VERSION } })).not.toContain('export-audit-package');
  });

  it('offers «Загрузить решения» to an expert only, beside the button', () => {
    const asked = (mayImportDecisions: boolean) => renderWith(newClient(), createElement(ExportPanel, {
      runId: RUN_ID, runState: 'published', providerMode: 'recorded', onExport: () => {}, layout: 'bar', mayImportDecisions,
    }));
    const expert = asked(true);
    expect(expert).toContain('Загрузить решения');
    expect(expert).toContain('data-decision-import');
    expect(expert.indexOf('data-export-menu')).toBeLessThan(expert.indexOf('data-decision-import'));
    expect(expert.indexOf('data-decision-import')).toBeLessThan(expert.indexOf('data-export-help'));
    expect(asked(false)).not.toContain('Загрузить решения');
  });

  it('opens the sentence about the selection and the line about the file from the «?»', () => {
    const markup = bar('published', { scopeCaption: SCOPE, verdict: 'accepted' });
    const help = markup.indexOf('data-export-help');
    expect(help).toBeGreaterThan(-1);
    expect(markup.indexOf('data-export-scope="accepted"')).toBeGreaterThan(help);
    expect(markup.indexOf(SCOPE)).toBeGreaterThan(help);
    expect(markup.indexOf(`О файле: колонок ${CSV_COLUMNS.length}`)).toBeGreaterThan(help);
    // The columns are still the constant's, in order, behind that line.
    const rendered = [...markup.matchAll(/data-csv-column="([^"]+)"/g)].map((match) => match[1]);
    expect(rendered).toEqual([...CSV_COLUMNS]);
    expect(markup).toContain(CSV_ENCODING.charset);
    expect(bar('published')).not.toContain('data-export-scope');
  });

  it('says the CSV’s refusal and its file under the row, in the words it had', () => {
    const refused = bar('published', { error: { title: 'В выгрузке отказано', detail: 'Файл не создан.', correlationId: 'cid-bar-1' } });
    expect(refused).toContain('В выгрузке отказано');
    expect(refused).toContain('Файл не создан.');
    expect(refused).toContain('cid-bar-1');
    expect(refused.indexOf('В выгрузке отказано')).toBeGreaterThan(refused.indexOf('data-export-help'));
    const done = bar('published', { lastFileName: csvFileName(RUN_ID) });
    expect(done).toContain(`data-last-file="${csvFileName(RUN_ID)}"`);
    expect(done).toContain(`Скачан ${csvFileName(RUN_ID)}`);
    expect(done.indexOf('data-export-status')).toBeGreaterThan(done.indexOf('data-export-help'));
    expect(bar('published')).not.toContain('data-export-status');
    // The refusal of a run without a result is said where it always was.
    const refusedQueued = bar('queued', { error: { title: 'В выгрузке отказано' } });
    expect(refusedQueued).toContain('В выгрузке отказано');
  });
});

describe('every state a file action can say, on the bar', () => {
  const idle: ExportFileState = { pending: false, lastFileName: null, error: null, onDownload: () => {} };
  const idlePackage: ExportPackageState = { pending: false, status: null, error: null, onDownload: () => {}, onCancel: () => {} };
  const view = (over: Partial<ExportBarViewProps> = {}) => render(createElement(ExportBarView, { runId: RUN_ID, csv: idle, xlsx: idle, pack: null, ...over }));

  it('says nothing while nothing has been asked', () => {
    expect(view()).not.toContain('data-export-status');
    expect(view({ pack: idlePackage })).not.toContain('data-export-status');
  });

  it('says «Готовлю…», «Готовлю Excel…» and «Собираю пакет…» with the way to cancel it, and disables the file being made', () => {
    const csv = view({ csv: { ...idle, pending: true } });
    expect(csv).toContain('Готовлю…');
    expect(csv).toMatch(/data-intent="export"[^>]*disabled/);
    expect(csv).not.toMatch(/data-intent="export-xlsx"[^>]*disabled/);
    const xlsx = view({ xlsx: { ...idle, pending: true } });
    expect(xlsx).toContain('Готовлю Excel…');
    expect(xlsx).toMatch(/data-intent="export-xlsx"[^>]*disabled/);
    const pack = view({ pack: { ...idlePackage, pending: true, status: 'Подготовка пакета аудита…' } });
    expect(pack).toContain('Собираю пакет…');
    expect(pack).toContain('data-intent="cancel-audit-package"');
    expect(pack).toContain('data-audit-package-status');
    expect(pack).toContain('Подготовка пакета аудита…');
    expect(pack).toMatch(/data-intent="export-audit-package"[^>]*disabled/);
    expect(view({ pack: idlePackage })).not.toContain('cancel-audit-package');
  });

  it('says «Скачан …» for each file handed over, and what the package holds', () => {
    const markup = view({
      csv: { ...idle, lastFileName: 'one.csv' }, xlsx: { ...idle, lastFileName: 'two.xlsx' },
      pack: { ...idlePackage, status: 'Пакет собран: исходный PDF и манифест.' },
    });
    expect(markup).toContain('Скачан one.csv');
    expect(markup).toContain('Скачан two.xlsx');
    expect(markup).toContain('data-last-file="one.csv"');
    expect(markup).toContain('data-last-file="two.xlsx"');
    expect(markup).toContain('Пакет собран: исходный PDF и манифест.');
    expect((markup.match(/data-export-status/g) ?? []).length).toBe(1);
  });

  it('says each refusal with the words it had, under the row', () => {
    const markup = view({
      csv: { ...idle, error: { title: 'В выгрузке отказано', detail: 'Файл не создан.' } },
      xlsx: { ...idle, error: xlsxFailure(new Error('x')) },
      pack: { ...idlePackage, error: { title: 'Пакет аудита не собран', detail: 'Неполный ZIP не скачивается; повторите попытку.' } },
    });
    for (const words of ['В выгрузке отказано', 'Файл не создан.', 'Excel не выгружен', 'Пакет аудита не собран', 'Неполный ZIP не скачивается']) {
      expect(markup).toContain(words);
      expect(markup.indexOf(words)).toBeGreaterThan(markup.indexOf('data-export-help'));
    }
    expect((markup.match(/role="alert"/g) ?? []).length).toBe(3);
  });

  it('hands a press on each file to its own action, once, and does nothing for a file that is being made', async () => {
    const calls: string[] = [];
    const file = (name: string, pending = false): ExportFileState => ({ ...idle, pending, onDownload: () => { calls.push(name); } });
    const pack = (pending = false): ExportPackageState => ({ ...idlePackage, pending, onDownload: () => { calls.push('package'); }, onCancel: () => { calls.push('cancel'); } });
    const live = await mountLive(createElement(ExportBarView, { runId: RUN_ID, csv: file('csv'), xlsx: file('xlsx'), pack: pack() }));
    try {
      expect(await live.press('CSV')).toBe(true);
      expect(await live.press('Excel')).toBe(true);
      expect(await live.press('Пакет аудита')).toBe(true);
      expect(calls).toEqual(['csv', 'xlsx', 'package']);
      await live.update(createElement(ExportBarView, { runId: RUN_ID, csv: file('csv', true), xlsx: file('xlsx', true), pack: pack(true) }));
      expect(await live.press('CSV')).toBe(false);
      expect(await live.press('Excel')).toBe(false);
      expect(await live.press('Пакет аудита')).toBe(false);
      expect(await live.press('Отменить')).toBe(true);
      expect(calls).toEqual(['csv', 'xlsx', 'package', 'cancel']);
    } finally {
      await live.unmount();
    }
  });
});
