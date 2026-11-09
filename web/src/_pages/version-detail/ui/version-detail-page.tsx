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
 *
 * **`W59-SECTION-UI-01`: the stage and section.** Once the version has answered, its
 * stage-and-section panel reads `getVersionSectionReview` at the address the version's own
 * body names (project, document, version) and shows the confirmed classification, the
 * expert's confirmation form, or a read-only sentence. The session's roles arrive from the
 * route, which has just checked them; they decide only which of those is drawn.
 *
 * `UI-A-27` «Просмотр PDF»: the original's button in the version bar opens the version's PDF in a drawer from the bottom of the
 * page. The button is in the page's actions; the drawer is the PDF page viewer (`widgets/evidence-viewer`, pdf.js), mounted through a
 * lazy boundary only once the button is pressed, so neither the viewer's code nor the document's bytes are asked for before.
 *
 * `CMP-VERSION-MARK-01`: a version admitted for comparison only (`upload_kind`
 * `comparison_pdf`) carries the mark «PDF без пакета портала» in its panel; its run list
 * offers the ordinary cost-approved section start.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import type { Role, RunStatus } from '@/shared/api';
import { ErrorState, Icon, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import {
  VersionPanel,
  looksLikeVersionUid,
  useDocumentVersion,
} from '@/entities/document-version';
import { RunList } from '@/widgets/run-list';
import { VersionClassification } from '@/widgets/version-classification';
import { DocumentContext } from '@/widgets/document-context';
import { LazyDocumentViewer } from './version-pdf-chunk';
import styles from './version-detail-page.module.css';

export interface VersionDetailPageProps {
  readonly projectUid: string;
  readonly versionUid: string;
  /** The session's roles, as the route's guard read them. */
  readonly roles: readonly Role[];
}

export function VersionDetailPage({ projectUid, versionUid, roles }: VersionDetailPageProps) {
  const router = useRouter();
  const wellFormed = looksLikeProjectUid(projectUid) && looksLikeVersionUid(versionUid);
  const version = useDocumentVersion(wellFormed ? versionUid : null);
  // `UI-A-27`: nothing of the drawer exists until this is true.
  const [pdfOpen, setPdfOpen] = useState(false);

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
  // `UI-A-22`: the page is named by its document and its number, as the original's version bar names the folder.
  const documentTitle = version.data === undefined ? undefined : (version.data.display_title ?? version.data.source_filename);
  const title = version.data === undefined
    ? 'Версия'
    : `Версия ${version.data.version_ordinal}${documentTitle === undefined || documentTitle === null ? '' : ` · ${documentTitle}`}`;

  return (
    <PageShell
      title={title}
      subtitle={<code>{versionUid}</code>}
      actions={
        <>
          {version.data === undefined ? null : (
            <>
              <button
                type="button"
                className="am-button am-button--quiet am-button--small"
                aria-pressed={pdfOpen}
                title="Открыть PDF этой версии снизу"
                data-version-pdf-toggle=""
                onClick={() => setPdfOpen((open) => !open)}
              >
                <Icon name="document" /> Просмотр PDF
              </button>{' '}
              <Link href={routes.document(version.data.project_uid, version.data.document_uid)}>Все версии документа</Link>{' '}
            </>
          )}
          <Link href={routes.project(ownerProjectUid)}>К проекту</Link>{' '}
          <Link href={routes.projects()}>Все проекты</Link>
        </>
      }
    >
      <DocumentContext projectUid={ownerProjectUid} versionUid={versionUid} current="version" />
      {version.isPending ? <LoadingState what="эту версию" /> : null}
      {version.isError ? (
        <ErrorState
          title="Эту версию не удалось прочитать."
          detail="Адрес может указывать на несуществующую версию, либо API не ответил."
          onRetry={() => void version.refetch()}
        />
      ) : null}
      {version.data === undefined ? null : (
        <div className={styles.columns}>
          <div className={styles.stack}>
            <section className={styles.panel} aria-label="Стадия и раздел">
              <VersionClassification
                address={{
                  projectUid: version.data.project_uid,
                  documentUid: version.data.document_uid,
                  versionUid: version.data.version_uid,
                }}
                roles={roles}
              />
            </section>
            {/* The file's identity and manifest are for proof, not for the first look: one click away. */}
            <details className={styles.facts} data-version-facts="">
              <summary>Сведения о версии и файле</summary>
              <VersionPanel version={version.data} />
            </details>
          </div>

          <section className={styles.panel} aria-labelledby="version-runs-title">
            <h2 id="version-runs-title">Прогоны</h2>
            <p className="am-note">
              <Link href={routes.comparison(ownerProjectUid, versionUid)}>Сравнить два прогона</Link> —
              что изменилось в анализе одной и той же версии.
              {' '}<Link href={routes.versionComparison()}>Сравнение версий</Link>{' · '}
              <Link href={routes.stageComparison()}>Сравнение стадий</Link>
            </p>
            <RunList
              projectUid={ownerProjectUid}
              versionUid={versionUid}
              sectionCode={version.data.classification?.section_code}
              uploadKind={version.data.upload_kind}
              onRunStarted={(run: RunStatus) => router.push(routes.run(run.project_uid, run.run_id))}
            />
          </section>
        </div>
      )}
      {pdfOpen && version.data !== undefined ? (
        <LazyDocumentViewer
          versionUid={version.data.version_uid}
          title={documentTitle === undefined || documentTitle === null ? `Версия ${version.data.version_ordinal}` : `${documentTitle} · Версия ${version.data.version_ordinal}`}
          pageCount={version.data.page_count}
          onClose={() => setPdfOpen(false)}
        />
      ) : null}
    </PageShell>
  );
}
