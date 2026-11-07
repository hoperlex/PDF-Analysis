'use client';

/** @jsxRuntime automatic */

/**
 * «Скачать пакет аудита» beside «Скачать CSV» and «Скачать Excel» (UI-A-76): the ZIP of one run. What the package holds is
 * `model/audit-package.ts`'s to say, and the button's tooltip says it before the first press; the line under the button
 * says what was packed after it, or why nothing was.
 */

import type { RunId, VersionUid } from '@/shared/api';
import { ErrorState } from '@/shared/ui';

import { AUDIT_PACKAGE_TITLE } from '../model/audit-package';
import type { UseAuditPackageArgs } from '../model/use-audit-package';
import { useAuditPackage } from '../model/use-audit-package';

export interface AuditPackageDownloadProps extends Pick<UseAuditPackageArgs, 'sink' | 'deps'> {
  readonly runId: RunId;
  readonly versionUid: VersionUid;
}

export function AuditPackageDownload({ runId, versionUid, sink, deps }: AuditPackageDownloadProps) {
  const pack = useAuditPackage({ runId, versionUid, sink, deps });
  return (
    <div data-export-format="audit-package">
      <button
        type="button"
        className="am-button am-button--quiet"
        data-intent="export-audit-package"
        title={AUDIT_PACKAGE_TITLE}
        disabled={pack.isPending}
        onClick={pack.download}
      >
        {pack.isPending ? 'Собираю пакет…' : 'Скачать пакет аудита'}
      </button>
      {pack.isPending ? (
        <button type="button" className="am-button am-button--quiet" data-intent="cancel-audit-package" onClick={pack.cancel}>
          Отменить
        </button>
      ) : null}
      {pack.status === null ? null : (
        <p className="am-export__last" role="status" aria-live="polite" data-audit-package-status="">
          {pack.status}
        </p>
      )}
      {pack.error === null ? null : <ErrorState {...pack.error} />}
    </div>
  );
}
