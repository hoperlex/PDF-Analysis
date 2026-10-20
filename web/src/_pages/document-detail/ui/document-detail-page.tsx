'use client';

/**
 * `/projects/{project_uid}/documents/{document_uid}` — one document and its versions.
 *
 * **Why this route exists is argued in `docs/program/reviews/W19-SHELL.md`.** It is an
 * *address*, because `document_uid` is a value this product prints — a column of the exported
 * CSV, a field of every `DocumentVersion` body, the subject of a `404` envelope — and an
 * identifier a product prints and cannot open is the shape of `D-16` itself.
 *
 * Since `W59-VERSION-UPLOAD-01` it is also a *step*: the next version of the document is
 * uploaded here («Загрузить новую версию»). The new version becomes the document's current
 * one and inherits no stage or section, so on success the screen leads to that version's
 * stage-and-section panel, where an expert confirms them before any run.
 *
 * It fetches `listVersions` on mount and reads nothing from a previous screen.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';

import type { DocumentVersion } from '@/shared/api';
import { PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import { looksLikeDocumentUid } from '@/entities/document-version';
import { UploadVersionPanel } from '@/widgets/upload-panel';
import { VersionList } from '@/widgets/version-list';

export interface DocumentDetailPageProps {
  readonly projectUid: string;
  readonly documentUid: string;
}

export function DocumentDetailPage({ projectUid, documentUid }: DocumentDetailPageProps) {
  const router = useRouter();

  if (!looksLikeProjectUid(projectUid) || !looksLikeDocumentUid(documentUid)) {
    return (
      <PageShell title="Документ" actions={<Link href={routes.projects()}>Все проекты</Link>}>
        <UnsupportedState
          title="Это не адрес документа."
          detail="Проект и документ адресуются непрозрачными идентификаторами. Запроса не было."
        />
      </PageShell>
    );
  }

  // The new version's address comes from the server's answer, never from this screen's own
  // path: the version is read back there, with its empty classification panel in front.
  const goToNewVersion = (version: DocumentVersion) => {
    router.push(routes.versionClassification(version.project_uid, version.version_uid));
  };

  return (
    <PageShell
      title="Документ"
      subtitle={<code>{documentUid}</code>}
      actions={
        <>
          <Link href={routes.project(projectUid)}>К проекту</Link>{' '}
          <Link href={routes.projects()}>Все проекты</Link>
        </>
      }
    >
      <h2>Опубликованные версии</h2>
      <VersionList projectUid={projectUid} documentUid={documentUid} />
      <UploadVersionPanel
        projectUid={projectUid}
        documentUid={documentUid}
        onUploaded={goToNewVersion}
      />
    </PageShell>
  );
}
