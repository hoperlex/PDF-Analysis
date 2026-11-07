'use client';

/**
 * «Скачать пакет аудита» and its own outcome: one package at a time, cancellable, with the line of progress the
 * builder reports and no archive on any failure. Plain component state, as `useExportRunXlsx`: the export panel is drawn
 * on screens, and in the guards' static renders, that have no query client, and a download caches nothing.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import type { RunId, VersionUid } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { browserDownloadSink, deliverDownload } from '@/features/export-run';
import type { DownloadSink } from '@/features/export-run';

import type { AuditPackageDeps } from './audit-package';
import { auditPackageDoneLine, auditPackageFailure, auditPackageProgressLine, buildAuditPackage } from './audit-package';

export interface UseAuditPackageArgs {
  readonly runId: RunId;
  readonly versionUid: VersionUid;
  /** Injected by tests. Production uses the browser sink and the server. */
  readonly sink?: DownloadSink | undefined;
  readonly deps?: AuditPackageDeps | undefined;
}

export interface UseAuditPackage {
  readonly download: () => void;
  readonly cancel: () => void;
  readonly isPending: boolean;
  /** The line under the button: the phase while it builds, what the package holds or that it was cancelled after. */
  readonly status: string | null;
  readonly error: ErrorStateProps | null;
}

export function useAuditPackage({ runId, versionUid, sink, deps }: UseAuditPackageArgs): UseAuditPackage {
  const active = useRef<AbortController | null>(null);
  const [isPending, setPending] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<ErrorStateProps | null>(null);

  // Leaving the screen stops the build: nothing is downloaded for a page that is gone.
  useEffect(() => () => { active.current?.abort(); active.current = null; }, []);

  const download = useCallback(() => {
    if (active.current !== null) return;
    const controller = new AbortController();
    active.current = controller;
    setPending(true);
    setError(null);
    setStatus('Подготовка пакета аудита…');
    void (async () => {
      try {
        const built = await buildAuditPackage({
          runId,
          versionUid,
          signal: controller.signal,
          deps,
          onProgress: (progress) => { if (active.current === controller) setStatus(auditPackageProgressLine(progress)); },
        });
        if (controller.signal.aborted) throw new DOMException('Отменено', 'AbortError');
        if (active.current !== controller) return;
        deliverDownload(sink ?? browserDownloadSink(), built.blob, built.summary.fileName);
        setStatus(auditPackageDoneLine(built.summary));
      } catch (failure) {
        if (active.current !== controller) return;
        if (controller.signal.aborted || failure instanceof Error && failure.name === 'AbortError') {
          setStatus('Подготовка пакета отменена. Пакет не скачивался.');
        } else {
          setStatus(null);
          setError(auditPackageFailure(failure));
        }
      } finally {
        if (active.current === controller) {
          active.current = null;
          setPending(false);
        }
      }
    })();
  }, [runId, versionUid, sink, deps]);

  const cancel = useCallback(() => { active.current?.abort(); }, []);

  return { download, cancel, isPending, status, error };
}
