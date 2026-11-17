'use client';

/**
 * «Скачать пакеты аудита» of a section and its own outcome (`UIP-S02-05`): one common ZIP at a time, cancellable, with the line of
 * progress per document and no archive on any failure. Plain component state, as `useAuditPackage` beside it: a download caches nothing
 * and the bar that holds it is drawn in static renders that have no query client.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import type { ErrorStateProps } from '@/shared/ui';
import { browserDownloadSink, deliverDownload } from '@/features/export-run';
import type { DownloadSink } from '@/features/export-run';

import type { AuditPackagesDeps, AuditPackagesDocument, AuditPackagesSummary } from './audit-packages-bulk';
import { auditPackagesDoneLine, auditPackagesFailure, auditPackagesProgressLine, buildAuditPackages } from './audit-packages-bulk';

export interface UseAuditPackagesArgs {
  /** Injected by tests. Production uses the browser sink and the server. */
  readonly sink?: DownloadSink | undefined;
  readonly deps?: AuditPackagesDeps | undefined;
}

export interface UseAuditPackages {
  /** Build the common ZIP of `documents` and hand it to the browser as `fileName`. Does nothing while one is being built. */
  readonly download: (documents: readonly AuditPackagesDocument[], fileName: string) => void;
  readonly cancel: () => void;
  readonly isPending: boolean;
  /** The line of the phase while it builds, what the archive holds or that it was cancelled after. */
  readonly status: string | null;
  /** What the last finished archive holds, for the list of the skipped documents. */
  readonly summary: AuditPackagesSummary | null;
  readonly error: ErrorStateProps | null;
  /** Forget the outcome of the last download. */
  readonly dismiss: () => void;
}

export function useAuditPackages({ sink, deps }: UseAuditPackagesArgs = {}): UseAuditPackages {
  const active = useRef<AbortController | null>(null);
  const [isPending, setPending] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [summary, setSummary] = useState<AuditPackagesSummary | null>(null);
  const [error, setError] = useState<ErrorStateProps | null>(null);

  // Leaving the screen stops the build: nothing is downloaded for a page that is gone.
  useEffect(() => () => { active.current?.abort(); active.current = null; }, []);

  const download = useCallback((documents: readonly AuditPackagesDocument[], fileName: string) => {
    if (active.current !== null) return;
    const controller = new AbortController();
    active.current = controller;
    setPending(true);
    setError(null);
    setSummary(null);
    setStatus('Подготовка пакетов аудита…');
    void (async () => {
      try {
        const built = await buildAuditPackages({
          documents,
          fileName,
          signal: controller.signal,
          deps,
          onProgress: (progress) => { if (active.current === controller) setStatus(auditPackagesProgressLine(progress)); },
        });
        if (controller.signal.aborted) throw new DOMException('Отменено', 'AbortError');
        if (active.current !== controller) return;
        deliverDownload(sink ?? browserDownloadSink(), built.blob, built.summary.fileName);
        setSummary(built.summary);
        setStatus(auditPackagesDoneLine(built.summary));
      } catch (failure) {
        if (active.current !== controller) return;
        if (controller.signal.aborted || failure instanceof Error && failure.name === 'AbortError') {
          setStatus('Сборка пакетов отменена. Архив не скачивался.');
        } else {
          setStatus(null);
          setError(auditPackagesFailure(failure));
        }
      } finally {
        if (active.current === controller) {
          active.current = null;
          setPending(false);
        }
      }
    })();
  }, [sink, deps]);

  const cancel = useCallback(() => { active.current?.abort(); }, []);
  const dismiss = useCallback(() => {
    if (active.current !== null) return;
    setStatus(null);
    setSummary(null);
    setError(null);
  }, []);

  return { download, cancel, isPending, status, summary, error, dismiss };
}
