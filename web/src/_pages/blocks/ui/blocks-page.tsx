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
 */

import { useId, useState } from 'react';

import type { DocumentVersion, Project, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, PageShell } from '@/shared/ui';
import { useProjectList } from '@/entities/project';
import {
  COMPARISON_ONLY_START_NOTE,
  ComparisonOnlyMark,
  isComparisonOnly,
  useDocumentList,
} from '@/entities/document-version';
import { PortalBlocks } from '@/widgets/portal-blocks';

import { DEFAULT_BLOCK_TAB } from '../model/tabs';
import type { BlockTab } from '../model/tabs';
import { BlocksTabs } from './blocks-tabs';
import { TextLines } from './text-lines';

export function BlocksPage() {
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
      <h2>1. Версия</h2>
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

      {version === null ? null : (
        <>
          <h2>2. Блоки</h2>
          <VersionBlockViews version={version} tab={tab} onTab={setTab} />
        </>
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
          <li key={project.project_uid} className="am-state" style={{ marginBottom: '0.5rem' }}>
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
          {COMPARISON_ONLY_START_NOTE}
        </p>
      ) : null}
      <ul>
        {documents.data.items.map((doc: DocumentVersion) => {
          const comparisonOnly = isComparisonOnly(doc);
          return (
            <li key={doc.version_uid} className="am-state" style={{ marginBottom: '0.5rem' }}>
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
}

/**
 * The chosen version's two tabs. Exported so the instruments that render one static pass
 * (the language guard, the contrast census) render the tabs and each tab's states exactly as
 * this page does: one pass cannot click a project, a document and a tab.
 */
export function VersionBlockViews({ version, tab, onTab }: VersionBlockViewsProps) {
  return (
    <BlocksTabs
      active={tab}
      onSelect={onTab}
      panels={{
        portal: <PortalBlocks version={version} />,
        lines: <TextLines versionUid={version.version_uid} />,
      }}
    />
  );
}
