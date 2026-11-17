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
 * page. `UIP-G-09`: the button is the frame's, in its version bar on every page of the document; this page hands the frame the
 * drawer (`pdf`), the PDF page viewer (`widgets/evidence-viewer`, pdf.js), mounted through a lazy boundary only once the button is
 * pressed, so neither the viewer's code nor the document's bytes are asked for before. A button pressed on another page of the
 * document leads here with `?pdf=1`, and the window opens on arrival; the address is then cleaned of it.
 *
 * `UIP-G-09`: the page's header carries no code and no links: the frame names the document and its version, the version's code is in
 * «Сведения о версии и файле», and the way up is the frame's row.
 *
 * `UIP-S04-03`: the first card of the page is «Последний прогон» (`widgets/run-list`): the version's last run, the row of its stages, the way into
 * the run and «Запустить» with its line under it; the table of runs below it is the table alone.
 *
 * `UIP-S04-04`: the order is the card, the line «Стадия и раздел» (`widgets/version-classification`), the table «Прогоны», «Сведения о версии и
 * файле»; one column. A version whose section nobody has confirmed has the confirmation form first, above the card.
 *
 * `CMP-VERSION-MARK-01`: a version admitted for comparison only (`upload_kind`
 * `comparison_pdf`) carries the mark «PDF без пакета портала» in its panel; its run list
 * offers the ordinary cost-approved section start.
 */

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import type { Role, RunStatus } from '@/shared/api';
import { ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import {
  VersionPanel,
  looksLikeVersionUid,
  useDocumentVersion,
} from '@/entities/document-version';
import { LastRunCard, RunList } from '@/widgets/run-list';
import { VersionClassification } from '@/widgets/version-classification';
import { DocumentContext, PDF_OPEN_PARAM } from '@/widgets/document-context';
import type { PdfDrawerProps } from '@/widgets/document-context';
import { LazyDocumentViewer } from './version-pdf-chunk';
import styles from './version-detail-page.module.css';

export interface VersionDetailPageProps {
  readonly projectUid: string;
  readonly versionUid: string;
  /** The session's roles, as the route's guard read them. */
  readonly roles: readonly Role[];
}

/** The address without the one-time request to open the PDF window (`?pdf=1`); everything else of it stays. */
export function withoutPdfRequest(search: string): string {
  const params = new URLSearchParams(search);
  params.delete(PDF_OPEN_PARAM);
  const rest = params.toString();
  return rest === '' ? '' : `?${rest}`;
}

/** The window is drawn by the frame, through this page's lazy boundary. */
const renderPdf = (drawer: PdfDrawerProps) => <LazyDocumentViewer {...drawer} />;

export function VersionDetailPage({ projectUid, versionUid, roles }: VersionDetailPageProps) {
  const router = useRouter();
  const wellFormed = looksLikeProjectUid(projectUid) && looksLikeVersionUid(versionUid);
  const version = useDocumentVersion(wellFormed ? versionUid : null);
  // `UIP-G-09`: a button of another page of the document asked for the window (`?pdf=1`); outside the app router there is no address.
  const searchParams = useSearchParams();
  const [openAtStart] = useState(() => searchParams?.get(PDF_OPEN_PARAM) === '1');
  useEffect(() => {
    if (!openAtStart) return;
    window.history.replaceState(window.history.state, '', `${window.location.pathname}${withoutPdfRequest(window.location.search)}${window.location.hash}`);
  }, [openAtStart]);

  if (!wellFormed) {
    return (
      <PageShell title="Версия" actions={<Link href={routes.projects()}>Все объекты</Link>}>
        <UnsupportedState
          title="Это не адрес версии."
          detail="Объект и версия адресуются непрозрачными идентификаторами. Запроса не было."
        />
      </PageShell>
    );
  }

  const ownerProjectUid = version.data?.project_uid ?? projectUid;
  // `UIP-S04-04`: a confirmed section is a line under the last run's card; an unconfirmed one is the form above it.
  const confirmed = version.data?.classification !== undefined;
  const classification = version.data === undefined ? null : (
    <VersionClassification
      address={{
        projectUid: version.data.project_uid,
        documentUid: version.data.document_uid,
        versionUid: version.data.version_uid,
      }}
      roles={roles}
    />
  );
  // `UI-A-22`: the page is named by its document and its number, as the original's version bar names the folder.
  const documentTitle = version.data === undefined ? undefined : (version.data.display_title ?? version.data.source_filename);
  const title = version.data === undefined
    ? 'Версия'
    : `Версия ${version.data.version_ordinal}${documentTitle === undefined || documentTitle === null ? '' : ` · ${documentTitle}`}`;

  return (
    <PageShell title={title}>
      <DocumentContext
        projectUid={ownerProjectUid}
        versionUid={versionUid}
        current="version"
        pdf={{ render: renderPdf, openAtStart }}
      />
      {version.isPending ? <LoadingState what="эту версию" /> : null}
      {version.isError ? (
        <ErrorState
          title="Эту версию не удалось прочитать."
          detail="Адрес может указывать на несуществующую версию, либо API не ответил."
          onRetry={() => void version.refetch()}
        />
      ) : null}
      {version.data === undefined ? null : (
        <div className={styles.stack}>
          {/*
            `UIP-S04-04`: the order of «Инфо»: the card «Последний прогон», the line «Стадия и раздел», the table of runs, the file's facts.
            A section nobody has confirmed puts the confirmation form first: no run starts without it, and the card's «Запустить» would
            only refuse.
          */}
          {confirmed ? null : classification}
          {/* `UIP-S04-03`: the first card of «Инфо»: the last run, its stages, «Запустить»; the table of runs below is the table alone. */}
          <LastRunCard
            projectUid={ownerProjectUid}
            versionUid={versionUid}
            uploadKind={version.data.upload_kind}
            onRunStarted={(run: RunStatus) => router.push(routes.run(run.project_uid, run.run_id))}
          />
          {confirmed ? classification : null}
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
              startElsewhere
            />
          </section>
          {/* The file's identity and manifest are for proof, not for the first look: one click away. */}
          <details className={styles.facts} data-version-facts="">
            <summary>Сведения о версии и файле</summary>
            <VersionPanel version={version.data} />
          </details>
        </div>
      )}
    </PageShell>
  );
}
