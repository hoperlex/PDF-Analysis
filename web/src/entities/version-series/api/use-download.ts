'use client';

/**
 * The files of the comparison that a reader downloads: the PDF of a report, its source MD, the MD summary of a series and the MD of
 * one sheet (`streamComparisonReportPdf`, `streamComparisonReportSourceMd`, `streamComparisonSeriesSummary`,
 * `streamComparisonSheetDescriptionMd`). A download is a read: it starts nothing and spends nothing. The bytes arrive through the
 * generated client (the BFF carries the credential), are turned into an object URL for the moment of the click and revoked at once.
 */

import { useMutation } from '@tanstack/react-query';

import type { ComparisonReportId, ComparisonSeriesId, ComparisonSheetPairId } from '@/shared/api';
import {
  streamComparisonReportPdf,
  streamComparisonReportSourceMd,
  streamComparisonSeriesSummary,
  streamComparisonSheetDescriptionMd,
  streamComparisonTechnicalReport,
} from '@/shared/api';

export type DownloadTarget =
  | { readonly kind: 'report-pdf'; readonly reportId: ComparisonReportId; readonly fileName: string }
  | { readonly kind: 'report-md'; readonly reportId: ComparisonReportId; readonly fileName: string }
  | { readonly kind: 'summary-md'; readonly seriesId: ComparisonSeriesId; readonly fileName: string }
  | { readonly kind: 'sheet-md'; readonly pairId: ComparisonSheetPairId; readonly fileName: string }
  | { readonly kind: 'technical'; readonly seriesId: ComparisonSeriesId; readonly format: 'xlsx' | 'html'; readonly fileName: string };

async function bytesOf(target: DownloadTarget): Promise<Blob> {
  switch (target.kind) {
    case 'technical': {
      const body = (await streamComparisonTechnicalReport({ path: { comparison_series_id: target.seriesId }, query: { format: target.format } })).data;
      return body instanceof Blob ? body : new Blob([body]);
    }
    case 'report-pdf': {
      const body = (await streamComparisonReportPdf({ path: { comparison_report_id: target.reportId } })).data;
      return body instanceof Blob ? body : new Blob([body], { type: 'application/pdf' });
    }
    case 'report-md':
      return new Blob([(await streamComparisonReportSourceMd({ path: { comparison_report_id: target.reportId } })).data], { type: 'text/markdown' });
    case 'summary-md':
      return new Blob([(await streamComparisonSeriesSummary({ path: { comparison_series_id: target.seriesId } })).data], { type: 'text/markdown' });
    case 'sheet-md':
      return new Blob([(await streamComparisonSheetDescriptionMd({ path: { comparison_sheet_pair_id: target.pairId } })).data], { type: 'text/markdown' });
  }
}

/** Fetch the file and hand it to the browser; the object URL is revoked whatever happens. */
export function useDownload() {
  return useMutation<void, unknown, DownloadTarget>({
    mutationFn: async (target) => {
      const blob = await bytesOf(target);
      const url = URL.createObjectURL(blob);
      try {
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = target.fileName;
        anchor.rel = 'noopener';
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
      } finally {
        URL.revokeObjectURL(url);
      }
    },
    retry: false,
  });
}
