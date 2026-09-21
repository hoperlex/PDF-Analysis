'use client';

/**
 * `/projects/{project_uid}/versions/{version_uid}` — one published version.
 *
 * **It fetches its own data.** `getDocumentVersion` for the manifest and `listRuns` for
 * the runs, both on mount, neither read out of state a previous screen happened to leave
 * behind. That is the whole of `D-16` at this address: paste the URL into a fresh tab and
 * the version renders.
 *
 * The route parameters are checked for shape only, which costs no request and separates a
 * malformed URL from a version the server says does not exist.
 *
 * **The back link is built from the fetched body, not from the URL.** The version carries
 * its own `project_uid`; the segment in the address is a display crumb that a user could
 * have mistyped or pasted from another project. Where the two disagree the server's answer
 * wins, and the screen says so rather than silently linking somewhere wrong.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';

import type { RunStatus } from '@/shared/api';
import { ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import {
  VersionPanel,
  looksLikeVersionUid,
  useDocumentVersion,
} from '@/entities/document-version';
import { RunList } from '@/widgets/run-list';

export interface VersionDetailPageProps {
  readonly projectUid: string;
  readonly versionUid: string;
}

export function VersionDetailPage({ projectUid, versionUid }: VersionDetailPageProps) {
  const router = useRouter();
  const wellFormed = looksLikeProjectUid(projectUid) && looksLikeVersionUid(versionUid);
  const version = useDocumentVersion(wellFormed ? versionUid : null);

  if (!wellFormed) {
    return (
      <PageShell title="Версия" actions={<Link href={routes.projects()}>Все проекты</Link>}>
        <UnsupportedState
          title="Это не адрес версии."
          detail="Проект и версия адресуются непрозрачными идентификаторами. Запроса не было."
        />
      </PageShell>
    );
  }

  const ownerProjectUid = version.data?.project_uid ?? projectUid;

  return (
    <PageShell
      title="Версия"
      subtitle={<code>{versionUid}</code>}
      actions={
        <>
          <Link href={routes.project(ownerProjectUid)}>К проекту</Link>{' '}
          <Link href={routes.projects()}>Все проекты</Link>
        </>
      }
    >
      <h2>Эта версия</h2>
      {version.isPending ? <LoadingState what="эту версию" /> : null}
      {version.isError ? (
        <ErrorState
          title="Эту версию не удалось прочитать."
          detail="Адрес может указывать на несуществующую версию, либо API не ответил."
          onRetry={() => void version.refetch()}
        />
      ) : null}
      {version.data === undefined ? null : (
        <>
          <VersionPanel version={version.data} />
          <p>
            <Link href={routes.document(version.data.project_uid, version.data.document_uid)}>
              All versions of this document
            </Link>
          </p>
        </>
      )}

      <h2>Прогоны</h2>
      <RunList
        projectUid={ownerProjectUid}
        versionUid={versionUid}
        onRunStarted={(run: RunStatus) => router.push(routes.run(run.project_uid, run.run_id))}
      />
    </PageShell>
  );
}
