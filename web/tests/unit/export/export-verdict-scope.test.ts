import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (original) => ({
  ...await original<Record<string, unknown>>(),
  exportRunCsv: vi.fn(async () => ({ data: new Blob(['csv']), correlationId: 'csv-scope' })),
  exportRunXlsx: vi.fn(async () => ({ data: new Blob(['xlsx']), correlationId: 'xlsx-scope' })),
}));

import { exportRunCsv, exportRunXlsx } from '@/shared/api';
import { useExportRun, useExportRunXlsx } from '@/features/export-run';
import type { ExportRunArgs } from '@/features/export-run';

import { mountLive } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { RUN_ID } from '../review/fixtures';

afterEach(() => vi.clearAllMocks());

describe.each(['csv', 'xlsx'] as const)('%s export scope', (format) => {
  const exporter = format === 'csv' ? exportRunCsv : exportRunXlsx;
  const useDownload = format === 'csv' ? useExportRun : useExportRunXlsx;

  function Download({ verdict }: Pick<ExportRunArgs, 'verdict'>) {
    const download = useDownload({ runId: RUN_ID, verdict, sink: { createObjectUrl: () => 'blob:scope', saveAs: () => {}, revokeObjectUrl: () => {} } });
    return createElement('button', { onClick: download.download }, 'Скачать');
  }

  it.each(['active', 'rejected', undefined] as const)('sends the chosen verdict %s and preserves an omitted legacy query', async (verdict) => {
    const live = await mountLive(createElement(QueryClientProvider, { client: newClient() }, createElement(Download, { verdict })));
    try {
      await live.press('Скачать');
      expect(exporter).toHaveBeenCalledWith({ path: { run_id: RUN_ID }, ...(verdict === undefined ? {} : { query: { verdict } }) });
    } finally { await live.unmount(); }
  });
});
