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
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import type { DocumentUid, DocumentVersion, ProjectUid, Role } from '@/shared/api';
import { PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import { looksLikeDocumentUid, useVersionList } from '@/entities/document-version';
import { useMayActAsExpert } from '@/entities/account';
import { DocumentLifecycle, DocumentTags } from '@/features/manage-document';
import { UploadVersionPanel } from '@/widgets/upload-panel';
import { VersionList } from '@/widgets/version-list';
import { DocumentContext } from '@/widgets/document-context';
import { OptimisationProposals } from '@/widgets/optimisation-proposals';
import styles from './document-detail-page.module.css';

export interface DocumentDetailPageProps {
  readonly projectUid: string;
  readonly documentUid: string;
  /** The session's roles, as the route's guard read them (`R-151r`: the optimisation tab acts by role). */
  readonly roles?: readonly Role[] | undefined;
}

/**
 * `R-151r`: the document's two places, in the address as `?tab=`; an absent or unknown value is «Версии». `UIP-G-09`: the
 * choice between them is the frame's: «Оптимизация» is its tab, and the list of versions is the page the document's own
 * name in the frame leads to, so the page draws no tab row of its own.
 */
export type DocumentTab = 'versions' | 'optimisation';

/**
 * The address after choosing a tab: leaving «Оптимизация» drops what belongs to it — the pass, the proposals'
 * layout and their decision filter (`UI-B-02`, `D-440`); other parameters stay.
 */
export function tabAddress(current: URLSearchParams | { toString(): string }, next: DocumentTab): URLSearchParams {
  const params = new URLSearchParams(current.toString());
  params.set('tab', next);
  if (next !== 'optimisation') {
    params.delete('pass');
    params.delete('layout');
    params.delete('decision');
  }
  return params;
}

/** The address after choosing a pass: another pass starts from «Все», so the decision filter goes (`D-440`). */
export function passAddress(current: URLSearchParams | { toString(): string }, next: string | null): URLSearchParams {
  const params = new URLSearchParams(current.toString());
  params.set('tab', 'optimisation');
  if (next === null) params.delete('pass');
  else params.set('pass', next);
  params.delete('decision');
  return params;
}

export function documentTabOf(value: string | null): DocumentTab {
  return value === 'optimisation' ? 'optimisation' : 'versions';
}

const NO_PARAMS = new URLSearchParams();

export function DocumentDetailPage({ projectUid, documentUid, roles = [] }: DocumentDetailPageProps) {
  const router = useRouter();
  // Outside the app router both hooks answer `null`: the first tab, written onto the document's own address.
  const pathname = usePathname() ?? routes.document(projectUid, documentUid);
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const tab = documentTabOf(searchParams.get('tab'));
  // `UI-B-02`: the chosen pass is in the address too (`?pass=`), so a link or a reload opens it. Only the
  // optimisation tab reads it; leaving that tab drops it, because a pass belongs to that tab — and so do the
  // proposals' layout (`?layout=`) and decision filter (`?decision=`). The decision filter belongs to the pass:
  // another pass starts from «Все» (`D-440`), as it did while the filter was the widget's own state.
  const pass = searchParams.get('pass');
  const writeAddress = (params: URLSearchParams) => {
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };
  const setPass = (next: string | null) => writeAddress(passAddress(searchParams, next));

  if (!looksLikeProjectUid(projectUid) || !looksLikeDocumentUid(documentUid)) {
    return (
      <PageShell title="Документ" actions={<Link href={routes.projects()}>Все объекты</Link>}>
        <UnsupportedState
          title="Это не адрес документа."
          detail="Объект и документ адресуются непрозрачными идентификаторами. Запроса не было."
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
    <DocumentScreen
      projectUid={projectUid as ProjectUid}
      documentUid={documentUid as DocumentUid}
      roles={roles}
      tab={tab}
      pass={pass}
      setPass={setPass}
      goToNewVersion={goToNewVersion}
    />
  );
}

/**
 * The document's screen once its address is well formed. `R-151a`: the title is the document's own (the newest
 * version's read carries it), with rename and archive for a session that may act, and a note while it is archived.
 */
function DocumentScreen({
  projectUid, documentUid, roles, tab, pass, setPass, goToNewVersion,
}: {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly roles: readonly Role[];
  readonly tab: DocumentTab;
  /** `UI-B-02`: the pass the address names, and the write of another one onto it. */
  readonly pass: string | null;
  readonly setPass: (next: string | null) => void;
  readonly goToNewVersion: (version: DocumentVersion) => void;
}) {
  const versions = useVersionList(documentUid);
  const mayAct = useMayActAsExpert();
  const newest = versions.data?.items[0];
  const title = newest?.display_title ?? newest?.source_filename ?? 'Документ';
  const archived = newest?.archived_at !== undefined;
  return (
    <PageShell
      title={title}
      subtitle={<code>{documentUid}</code>}
      actions={
        <>
          <Link href={routes.project(projectUid)}>К объекту</Link>{' '}
          <Link href={routes.projects()}>Все объекты</Link>
        </>
      }
    >
      {/*
        `UIP-G-09`: the same frame as on every page of the document, with the newest version in view (the page holds it, so the
        frame reads none). «Оптимизация» is its tab; the neighbours between the documents of the section (`UI-A-28`) and the
        section the current version is confirmed for (`UI-A-23`) are the frame's, from that version.
      */}
      <DocumentContext
        projectUid={projectUid}
        documentUid={documentUid}
        current={tab === 'optimisation' ? 'optimisation' : 'document'}
        sectionCode={newest?.classification?.section_code}
        version={newest}
      />
      {/* The document's own controls share one row: rename and archive, and its tags. */}
      <div className={styles.toolbar}>
        {newest === undefined ? null : mayAct ? (
          <DocumentLifecycle projectUid={projectUid} documentUid={documentUid} title={title} archived={archived} />
        ) : archived ? (
          <p className="am-note" role="status">Документ в архиве: его нет в списках объекта.</p>
        ) : null}
        {newest === undefined ? null : (
          <DocumentTags projectUid={projectUid} documentUid={documentUid} tags={newest.tags ?? []} mayEdit={mayAct} />
        )}
      </div>
      {tab === 'optimisation' ? (
        <section className={styles.panel} aria-label="Оптимизация документа">
          <OptimisationProposals
            projectUid={projectUid as ProjectUid}
            documentUid={documentUid as DocumentUid}
            roles={roles}
            passId={pass}
            onPassChange={setPass}
          />
        </section>
      ) : (
      <div className={styles.stack}>
        <section className={styles.panel} aria-labelledby="document-versions-title">
          <h2 id="document-versions-title">Опубликованные версии</h2>
          {/* `UI-A-45`: the current version's audit chip comes from its section's listing, the one the strip above reads. */}
          <VersionList projectUid={projectUid} documentUid={documentUid} sectionCode={newest?.classification?.section_code} />
        </section>
        <section className={styles.panel} aria-label="Загрузить новую версию">
          <UploadVersionPanel
            projectUid={projectUid}
            documentUid={documentUid}
            onUploaded={goToNewVersion}
          />
        </section>
      </div>
      )}
    </PageShell>
  );
}
