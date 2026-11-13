'use client';

/**
 * `/blocks` — page-by-page block markup, for a version a reviewer chooses.
 *
 * `R-23`'s addendum (`OWNER_RULINGS_2026-09-17.md` §3.11) ruled two halves of this
 * screen differently. The first exists in the data: `page_geometry_extraction` writes a
 * real `bbox {x0, y0, x1, y1}` in points, one per extracted text line, and
 * `W45-BLOCKS`'s reseal added `getVersionBlocks` so a screen can read it back. The
 * second — the *vector graph* of a block, `R-23`'s own second phrase — has no source
 * anywhere in this pipeline: `PC-01` does no visual detection, and the legacy corpus's
 * `polygon_points` is `null` on every one of its rows. `R-39` (ruled 2026-09-24) permits
 * a screen to say that plainly, in the words of the subject, rather than staying silent
 * or overstating what exists — so this screen does, once, below.
 *
 * **No operation is unaddressed by this screen.** `/blocks` carries no route parameter,
 * so "a version a reviewer chooses" is a chooser built into the screen: pick a project,
 * pick one of its documents (which is also its current version — `listDocuments`
 * already answers one `DocumentVersion` per document, the same shape `uploadDocument`
 * publishes into), and the block index for that version loads underneath. Nothing here
 * remembers a choice across a reload; each step re-asks the server, the same discipline
 * `D-16` put on every other screen in this product.
 *
 * **Absent is not empty, and a reviewer is meant to be able to tell which one they are
 * looking at from the screen itself, not from the length of a list.** This product's own
 * five-state vocabulary (`shared/ui/states.tsx`) already draws exactly this line:
 * `NotApplicableState` — *"distinct from empty, which means the answer is genuinely
 * nothing"* — is what renders when `status` is `"not_produced"` (no run of this version
 * has derived its geometry yet), and `EmptyState` is what renders when `status` is
 * `"produced"` and this version genuinely has no blocks. The wording differs too, on
 * purpose, beneath the badge.
 *
 * **No invented numbers.** Every count on this screen — a page number, a block's
 * character span, a coordinate — is carried on the response exactly as `getVersionBlocks`
 * answered it; nothing here is computed, rounded further or guessed at while data is
 * loading.
 *
 * **A document admitted for comparison only** (`upload_kind` `comparison_pdf`, `Q-CMP-5`;
 * `CMP-DEBT-261`) is listed in the chooser and marked as everywhere (`CMP-VERSION-MARK-01`), but its
 * «Показать блоки» is disabled with the reason beside it: it has no portal bundle, so no block of a
 * portal is read for it, and no version of it can be chosen here.
 *
 * **Two tabs since `W55B-WEB-BLOCKS`** (plan §B3.9). Once a version is chosen the screen
 * shows «Блоки портала» — what the version's portal bundle brought, page by page
 * (`widgets/portal-blocks`) — and, as the second tab, «Строки текста», the text-line index
 * this screen showed before, moved to `text-lines.tsx` unchanged. The tab is page state like
 * the choice of version, and like it does not survive a reload.
 *
 * **A tab of the version since `R-151m`.** The original shows «Блоки» as a tab of its project; ours is the
 * version's tab at `/projects/[project_uid]/versions/[version_uid]/blocks`, where this screen opens with the
 * version already chosen (from the address, never from memory) and the context strip says where it is. The
 * chooser at `/blocks` stays for a reader who comes without a version, out of the menu, and once a version is
 * chosen it offers the version's own tab.
 *
 * **The page chosen above the tiles is kept in the address** on the version's tab: `?page=N` (a PDF page) or
 * `?page=all`, read here and written with `history.replaceState` as «Разбор» writes `?finding=`, so a reload or
 * a link opens the same page. An address without it, or with a value that names no page, is «Все блоки». The
 * chooser at `/blocks` has no address of its own for a version, so it keeps the choice in the page only.
 */

import { useId, useState } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

import type { DocumentVersion, Project, ProjectUid, VersionUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { pageSelectionOf } from '@/entities/block';
import type { PageSelection } from '@/entities/block';
import { looksLikeProjectUid, useProjectList } from '@/entities/project';
import {
  COMPARISON_ONLY_BLOCKS_NOTE,
  ComparisonOnlyMark,
  isComparisonOnly,
  looksLikeVersionUid,
  useDocumentList,
  useDocumentVersion,
} from '@/entities/document-version';
import { DocumentContext } from '@/widgets/document-context';
import { PortalBlocks } from '@/widgets/portal-blocks';

import { addressWithPage } from '../model/page-address';
import { DEFAULT_BLOCK_TAB } from '../model/tabs';
import type { BlockTab } from '../model/tabs';
import { BlocksTabs } from './blocks-tabs';
import { TextLines } from './text-lines';
import styles from './blocks-page.module.css';

const NO_PARAMS = new URLSearchParams();

export interface BlocksPageProps {
  /** `R-151m`: the version's tab — both given by the route; absent at the chooser `/blocks`. */
  readonly projectUid?: string | undefined;
  readonly versionUid?: string | undefined;
}

export function BlocksPage({ projectUid, versionUid }: BlocksPageProps) {
  if (projectUid !== undefined && versionUid !== undefined) {
    return <VersionBlocksScreen projectUid={projectUid} versionUid={versionUid} />;
  }
  return <BlocksChooserScreen />;
}

/** The version's «Блоки» tab: the version comes from the address, the tabs show at once. */
function VersionBlocksScreen({ projectUid, versionUid }: { readonly projectUid: string; readonly versionUid: string }) {
  if (!looksLikeProjectUid(projectUid) || !looksLikeVersionUid(versionUid)) {
    return (
      <PageShell title="Блоки" actions={<Link href={routes.projects()}>Все проекты</Link>}>
        <UnsupportedState
          title="Это не адрес версии."
          detail="Версия адресуется идентификаторами проекта и версии. Запроса не было."
        />
      </PageShell>
    );
  }
  return <VersionBlocksLoaded projectUid={projectUid} versionUid={versionUid as VersionUid} />;
}

function VersionBlocksLoaded({ projectUid, versionUid }: { readonly projectUid: string; readonly versionUid: VersionUid }) {
  const version = useDocumentVersion(versionUid);
  const [tab, setTab] = useState<BlockTab>(DEFAULT_BLOCK_TAB);
  // Outside the app router both hooks answer `null` (a static render): the list opens on «Все блоки».
  const pathname = usePathname() ?? routes.versionBlocks(projectUid, versionUid);
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const page = pageSelectionOf(searchParams.get('page'));
  const writePage = (selection: PageSelection) => {
    // Next keeps `usePathname`/`useSearchParams` in step with the native history API, so the address is
    // written without the app router, as «Разбор» writes `?finding=`.
    window.history.replaceState(window.history.state, '', addressWithPage(pathname, searchParams.toString(), selection));
  };
  let body;
  if (version.isPending) {
    body = <LoadingState what="версию" />;
  } else if (version.isError) {
    body = <ErrorState title="Версию не удалось прочитать." onRetry={() => void version.refetch()} />;
  } else if (version.data.project_uid !== projectUid) {
    body = (
      <UnsupportedState
        title="Эта версия из другого проекта."
        detail={<Link href={routes.versionBlocks(version.data.project_uid, version.data.version_uid)}>Открыть блоки в её проекте</Link>}
      />
    );
  } else if (isComparisonOnly(version.data)) {
    body = <UnsupportedState title="Блоков нет." detail={COMPARISON_ONLY_BLOCKS_NOTE} />;
  } else {
    body = <VersionBlockViews version={version.data} tab={tab} onTab={setTab} page={page} onPage={writePage} />;
  }
  return (
    <PageShell
      title="Блоки"
      surface="canvas"
      subtitle={version.data === undefined ? undefined : (version.data.display_title ?? version.data.source_filename ?? version.data.version_uid)}
    >
      <DocumentContext projectUid={projectUid} current="blocks" versionUid={versionUid} />
      <section className={styles.sectionPanel} aria-label="Блоки версии">
        {body}
      </section>
    </PageShell>
  );
}

function BlocksChooserScreen() {
  const [projectUid, setProjectUid] = useState<ProjectUid | null>(null);
  const [version, setVersion] = useState<DocumentVersion | null>(null);
  const [tab, setTab] = useState<BlockTab>(DEFAULT_BLOCK_TAB);

  return (
    <PageShell
      title="Блоки"
      subtitle={
        version === null
          ? 'Постраничная разметка документа: какие фрагменты анализ считает блоками и где они находятся.'
          : version.display_title ?? version.source_filename ?? version.version_uid
      }
    >
      <section className={styles.sectionPanel} aria-labelledby="blocks-version-title">
        <h2 id="blocks-version-title">1. Версия</h2>
        {version === null ? (
          <VersionChooser
            projectUid={projectUid}
            onChooseProject={(uid) => setProjectUid(uid)}
            onChooseVersion={(chosen) => setVersion(chosen)}
          />
        ) : (
          <div className="am-state">
            <p className="am-state__title">
              {version.display_title ?? version.source_filename ?? version.version_uid}
            </p>
            <div className="am-state__detail">
              <p>
                <code>{version.version_uid}</code> · страниц {version.page_count}
              </p>
              {/* `R-151m`: the same tabs live on the version itself; this address can be kept and shared. */}
              <p>
                <Link href={routes.versionBlocks(version.project_uid, version.version_uid)}>Открыть как вкладку версии</Link>
              </p>
            </div>
            <div className="am-state__action">
              <button
                type="button"
                className="am-button"
                onClick={() => {
                  setVersion(null);
                  setProjectUid(null);
                  setTab(DEFAULT_BLOCK_TAB);
                }}
              >
                Выбрать другую версию
              </button>
            </div>
          </div>
        )}
      </section>

      {version === null ? null : (
        <section className={styles.sectionPanel} aria-labelledby="blocks-content-title">
          <h2 id="blocks-content-title">2. Блоки</h2>
          <VersionBlockViews version={version} tab={tab} onTab={setTab} />
        </section>
      )}
    </PageShell>
  );
}

interface VersionChooserProps {
  readonly projectUid: ProjectUid | null;
  readonly onChooseProject: (projectUid: ProjectUid) => void;
  readonly onChooseVersion: (version: DocumentVersion) => void;
}

function VersionChooser({ projectUid, onChooseProject, onChooseVersion }: VersionChooserProps) {
  const projects = useProjectList();

  if (projects.isPending) return <LoadingState what="проекты" />;
  if (projects.isError) {
    return (
      <ErrorState
        title="Список проектов не удалось прочитать."
        onRetry={() => void projects.refetch()}
      />
    );
  }
  if (projects.data.items.length === 0) {
    return <EmptyState title="Проектов пока нет." detail="Сначала опубликуйте документ." />;
  }

  if (projectUid === null) {
    return (
      <ul>
        {projects.data.items.map((project: Project) => (
          <li key={project.project_uid} className="am-state">
            <p className="am-state__title">{project.name}</p>
            <div className="am-state__action">
              <button
                type="button"
                className="am-button"
                onClick={() => onChooseProject(project.project_uid)}
              >
                Выбрать проект
              </button>
            </div>
          </li>
        ))}
      </ul>
    );
  }

  return <DocumentChooser projectUid={projectUid} onChooseVersion={onChooseVersion} />;
}

export interface DocumentChooserProps {
  readonly projectUid: ProjectUid;
  readonly onChooseVersion: (version: DocumentVersion) => void;
}

/**
 * The project's documents, one «Показать блоки» each. Exported so the instruments that render one
 * static pass (the `CMP-DEBT-261` tests, the census) render the list as this page does: one pass
 * cannot click a project row first.
 */
export function DocumentChooser({ projectUid, onChooseVersion }: DocumentChooserProps) {
  const noteId = useId();
  const documents = useDocumentList(projectUid);

  if (documents.isPending) return <LoadingState what="документы проекта" />;
  if (documents.isError) {
    return (
      <ErrorState
        title="Список документов не удалось прочитать."
        onRetry={() => void documents.refetch()}
      />
    );
  }
  if (documents.data.items.length === 0) {
    return <EmptyState title="В этом проекте нет опубликованных документов." />;
  }

  const anyComparisonOnly = documents.data.items.some((doc: DocumentVersion) => isComparisonOnly(doc));
  return (
    <>
      {anyComparisonOnly ? (
        <p className="am-note" id={noteId} data-comparison-only-note="">
          {COMPARISON_ONLY_BLOCKS_NOTE}
        </p>
      ) : null}
      <ul>
        {documents.data.items.map((doc: DocumentVersion) => {
          const comparisonOnly = isComparisonOnly(doc);
          return (
            <li key={doc.version_uid} className="am-state">
              <p className="am-state__title">
                {doc.display_title ?? doc.source_filename ?? doc.version_uid}
              </p>
              <div className="am-state__detail">
                {comparisonOnly ? (
                  <p>
                    <ComparisonOnlyMark version={doc} />
                  </p>
                ) : null}
                <p>
                  <code>{doc.version_uid}</code> · страниц {doc.page_count}
                </p>
              </div>
              <div className="am-state__action">
                <button
                  type="button"
                  className="am-button"
                  disabled={comparisonOnly}
                  aria-describedby={comparisonOnly ? noteId : undefined}
                  onClick={() => onChooseVersion(doc)}
                >
                  Показать блоки
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}

export interface VersionBlockViewsProps {
  readonly version: DocumentVersion;
  readonly tab: BlockTab;
  readonly onTab: (tab: BlockTab) => void;
  /** The page chosen above the tiles when the list opens (the version's tab reads it from the address). */
  readonly page?: PageSelection | undefined;
  /** Told each time the reader chooses «Все блоки» or a page. */
  readonly onPage?: ((selection: PageSelection) => void) | undefined;
}

/**
 * The chosen version's two tabs. Exported so the instruments that render one static pass
 * (the language guard, the contrast census) render the tabs and each tab's states exactly as
 * this page does: one pass cannot click a project, a document and a tab.
 */
export function VersionBlockViews({ version, tab, onTab, page, onPage }: VersionBlockViewsProps) {
  return (
    <BlocksTabs
      active={tab}
      onSelect={onTab}
      panels={{
        portal: <PortalBlocks version={version} page={page} onPage={onPage} />,
        lines: <TextLines versionUid={version.version_uid} />,
      }}
    />
  );
}
