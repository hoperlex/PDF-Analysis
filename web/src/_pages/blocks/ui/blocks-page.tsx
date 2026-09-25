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
 */

import { useState } from 'react';

import type { BlockGeometry, DocumentVersion, Project, ProjectUid, VersionUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, NotApplicableState, PageShell } from '@/shared/ui';
import { useProjectList } from '@/entities/project';
import { useDocumentList } from '@/entities/document-version';

import { useVersionBlocks } from '../api/use-version-blocks';

export function BlocksPage() {
  const [projectUid, setProjectUid] = useState<ProjectUid | null>(null);
  const [version, setVersion] = useState<DocumentVersion | null>(null);

  return (
    <PageShell
      title="Блоки"
      subtitle={
        version === null
          ? 'Постраничная разметка документа: какие фрагменты анализ считает блоками и где они находятся.'
          : version.display_title ?? version.source_filename ?? version.version_uid
      }
    >
      <p>
        Векторный граф блока здесь пока не строится: приложение вычисляет прямоугольные
        границы блока на странице, но не его контур. Ниже показано то, что есть.
      </p>

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
          <BlockMarkup versionUid={version.version_uid} />
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

interface DocumentChooserProps {
  readonly projectUid: ProjectUid;
  readonly onChooseVersion: (version: DocumentVersion) => void;
}

function DocumentChooser({ projectUid, onChooseVersion }: DocumentChooserProps) {
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

  return (
    <ul>
      {documents.data.items.map((doc: DocumentVersion) => (
        <li key={doc.version_uid} className="am-state" style={{ marginBottom: '0.5rem' }}>
          <p className="am-state__title">
            {doc.display_title ?? doc.source_filename ?? doc.version_uid}
          </p>
          <div className="am-state__detail">
            <p>
              <code>{doc.version_uid}</code> · страниц {doc.page_count}
            </p>
          </div>
          <div className="am-state__action">
            <button type="button" className="am-button" onClick={() => onChooseVersion(doc)}>
              Показать блоки
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

interface BlockMarkupProps {
  readonly versionUid: VersionUid;
}

function BlockMarkup({ versionUid }: BlockMarkupProps) {
  const blocks = useVersionBlocks(versionUid);

  if (blocks.isPending) return <LoadingState what="разметку блоков" />;
  if (blocks.isError) {
    return (
      <ErrorState
        title="Разметку блоков не удалось прочитать."
        onRetry={() => void blocks.refetch()}
      />
    );
  }

  const index = blocks.data;

  if (index.status === 'not_produced') {
    return (
      <NotApplicableState
        title="Разметка блоков для этой версии ещё не построена."
        detail="Ни один прогон этой версии ещё не дошёл до вычисления геометрии страниц. Это не то же самое, что «блоков нет» — как только прогон её вычислит, здесь появится разметка."
      />
    );
  }

  if (index.blocks.length === 0) {
    return (
      <EmptyState
        title="Блоков не обнаружено."
        detail="Геометрия для этой версии вычислена, и в документе не нашлось ни одного блока."
      />
    );
  }

  const byPage = new Map<number, BlockGeometry[]>();
  for (const block of index.blocks) {
    const page = byPage.get(block.page_number) ?? [];
    page.push(block);
    byPage.set(block.page_number, page);
  }
  const pageNumbers = [...byPage.keys()].sort((a, b) => a - b);

  return (
    <div>
      {pageNumbers.map((pageNumber) => {
        const pageBlocks = (byPage.get(pageNumber) ?? []).slice().sort(
          (a, b) => a.block_ordinal - b.block_ordinal,
        );
        return (
          <section key={pageNumber} style={{ marginBottom: '1rem' }}>
            <h3>
              Страница {pageNumber} · блоков {pageBlocks.length}
            </h3>
            <ul>
              {pageBlocks.map((block) => (
                <li key={block.block_id} className="am-state" style={{ marginBottom: '0.25rem' }}>
                  <div className="am-state__detail">
                    <p>
                      <code>{block.block_id}</code>
                    </p>
                    <p>
                      x0 {block.bbox.x0} · y0 {block.bbox.y0} · x1 {block.bbox.x1} · y1{' '}
                      {block.bbox.y1} {block.bbox_unit} · начало координат {block.bbox_origin}
                    </p>
                    <p>
                      символы {block.char_start}–{block.char_end}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
