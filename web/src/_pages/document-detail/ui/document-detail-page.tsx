'use client';

/**
 * `/projects/{project_uid}/documents/{document_uid}` — one document and its versions.
 *
 * **Whether this route earns its place is argued in `docs/program/reviews/W19-SHELL.md`,
 * not assumed here.** The short form: through this surface a document has exactly one
 * version, so as a *step* in the journey this screen is a click that shows a list of one,
 * and the project screen therefore links straight past it to the version. It exists as an
 * *address*, because `document_uid` is a value this product prints — a column of the
 * exported CSV, a field of every `DocumentVersion` body, the subject of a `404` envelope —
 * and an identifier a product prints and cannot open is the shape of `D-16` itself.
 *
 * It fetches `listVersions` on mount and reads nothing from a previous screen.
 */

import Link from 'next/link';

import { PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import { looksLikeDocumentUid } from '@/entities/document-version';
import { VersionList } from '@/widgets/version-list';

export interface DocumentDetailPageProps {
  readonly projectUid: string;
  readonly documentUid: string;
}

export function DocumentDetailPage({ projectUid, documentUid }: DocumentDetailPageProps) {
  if (!looksLikeProjectUid(projectUid) || !looksLikeDocumentUid(documentUid)) {
    return (
      <PageShell title="Document" actions={<Link href={routes.projects()}>All projects</Link>}>
        <UnsupportedState
          title="That is not a document address."
          detail="A project and a document are each addressed by an opaque identifier. Nothing was requested."
        />
      </PageShell>
    );
  }

  return (
    <PageShell
      title="Document"
      subtitle={<code>{documentUid}</code>}
      actions={
        <>
          <Link href={routes.project(projectUid)}>Back to project</Link>{' '}
          <Link href={routes.projects()}>All projects</Link>
        </>
      }
    >
      <h2>Published versions</h2>
      <VersionList projectUid={projectUid} documentUid={documentUid} />
    </PageShell>
  );
}
