'use client';

/**
 * The version bar of the document frame (`UIP-G-09`), under the tabs on every page of the document, as the original's
 * «ВЕРСИЯ: [V2 · текущая ▾] … 📄 Просмотр PDF … ← Предыдущий 1 / 7 Следующий →»:
 *
 *   - **the version choice**, always drawn (also for a document of one version), keeping the tab: another version opens the
 *     same tab of that version (`versionChoiceLevel`), and the last entry, «Все версии…», is the document's own page. It
 *     lists the first page of the document's versions; a longer history says so instead of hiding the rest (`UI-A-24`).
 *   - **«Просмотр PDF»**. The window is the version page's drawer (`UI-A-27`) and stays as it is. Where the page hands the
 *     frame the drawer (`pdf`), the button opens it in place; where it does not, the button is a link to the version with
 *     the window open (`?pdf=1`), so the button is on every tab and the window is the same one. That the window survives
 *     a change of tab and of version is the task that moves the drawer into the frame (`UIP-S10-01`), not this one.
 *   - **the neighbours** in the section, «‹ Предыдущий · N из M · Следующий ›», opening the same tab of the neighbour.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';

import type { DocumentUid, DocumentVersion, RunStatus, VersionUid } from '@/shared/api';
import { Icon } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { runListQueryOptions } from '@/entities/audit-run';
import { useVersionList } from '@/entities/document-version';

import { levelAddress, levelNeedsRuns, targetOfRuns, versionChoiceLevel } from '../model/tab-address';
import type { TabLevel } from '../model/version-tabs';
import { SectionNeighbours } from './section-neighbours';

import styles from './document-context.module.css';

/** What the drawer is told: the version it is about, its name, its page count, and how to close it. */
export interface PdfDrawerProps {
  readonly versionUid: VersionUid;
  readonly title: string;
  readonly pageCount: number;
  readonly onClose: () => void;
}

/** The drawer a page hands the frame: how to draw it, and whether it opens with the page. */
export interface PdfSlot {
  readonly render: (drawer: PdfDrawerProps) => ReactNode;
  readonly openAtStart?: boolean | undefined;
}

export const PDF_BUTTON_LABEL = 'Просмотр PDF';
export const PDF_BUTTON_HINT = 'Весь документ, снизу';
/** The query the version page reads to open the window on arrival. */
export const PDF_OPEN_PARAM = 'pdf';
export const ALL_VERSIONS_LABEL = 'Все версии…';
const ALL_VERSIONS = '__all__';

function VersionChoice({ projectUid, documentUid, version, level }: {
  readonly projectUid: string;
  readonly documentUid: string;
  readonly version: DocumentVersion;
  readonly level: TabLevel;
}) {
  const router = useRouter();
  const client = useQueryClient();
  const versions = useVersionList(documentUid as DocumentUid);
  const listed = versions.data?.items ?? [];
  // The list is newest first and the newest is the document's current version, as the original's «· текущая».
  const options = listed.map((item, index) => ({
    versionUid: item.version_uid as string,
    label: `Версия ${item.version_ordinal}${index === 0 ? ' · текущая' : ''}`,
  }));
  // The version in view stays in the choice while the list is not read, and when it is older than the first page.
  if (!options.some((option) => option.versionUid === version.version_uid)) {
    options.push({ versionUid: version.version_uid, label: `Версия ${version.version_ordinal}` });
  }
  const more = (versions.data?.page.next_cursor ?? null) !== null;

  const choose = async (value: string) => {
    if (value === ALL_VERSIONS) {
      router.push(routes.document(projectUid, documentUid));
      return;
    }
    const wanted = versionChoiceLevel(level);
    const base = { projectUid, documentUid, versionUid: value };
    let runs: readonly RunStatus[] | undefined;
    if (levelNeedsRuns(wanted)) {
      try {
        runs = (await client.fetchQuery(runListQueryOptions(value as VersionUid))).items;
      } catch {
        // The runs could not be read: the version's «Инфо» is the place that is always there.
        runs = undefined;
      }
    }
    router.push(levelAddress(wanted, targetOfRuns(base, runs)));
  };

  return (
    <label className={styles.switch}>
      <span>Версия</span>
      <select value={version.version_uid} data-version-choice="" onChange={(event) => void choose(event.target.value)}>
        {options.map((option) => (
          <option key={option.versionUid} value={option.versionUid}>{option.label}</option>
        ))}
        <option value={ALL_VERSIONS}>{ALL_VERSIONS_LABEL}</option>
      </select>
      {more ? <span className={styles.more}>показаны первые {listed.length}</span> : null}
    </label>
  );
}

function PdfButton({ projectUid, version, pdf, open, onToggle }: {
  readonly projectUid: string;
  readonly version: DocumentVersion;
  readonly pdf: PdfSlot | undefined;
  readonly open: boolean;
  readonly onToggle: () => void;
}) {
  if (pdf === undefined) {
    return (
      <Link
        className="am-button am-button--quiet am-button--small"
        href={`${routes.version(projectUid, version.version_uid)}?${PDF_OPEN_PARAM}=1`}
        title={PDF_BUTTON_HINT}
        data-version-pdf-link=""
      >
        <Icon name="document" /> {PDF_BUTTON_LABEL}
      </Link>
    );
  }
  return (
    <button
      type="button"
      className="am-button am-button--quiet am-button--small"
      aria-pressed={open}
      title={PDF_BUTTON_HINT}
      data-version-pdf-toggle=""
      onClick={onToggle}
    >
      <Icon name="document" /> {PDF_BUTTON_LABEL}
    </button>
  );
}

export interface VersionBarProps {
  readonly projectUid: string;
  readonly documentUid: string;
  /** The version in view, as the page's reads give it. */
  readonly version: DocumentVersion;
  readonly level: TabLevel;
  readonly pdf?: PdfSlot | undefined;
}

export function VersionBar({ projectUid, documentUid, version, level, pdf }: VersionBarProps) {
  const [pdfOpen, setPdfOpen] = useState(pdf?.openAtStart === true);
  const documentTitle = version.display_title ?? version.source_filename ?? undefined;
  const drawerTitle = documentTitle === undefined ? `Версия ${version.version_ordinal}` : `${documentTitle} · Версия ${version.version_ordinal}`;
  return (
    <div className={styles.versionBar} data-version-bar="">
      <VersionChoice projectUid={projectUid} documentUid={documentUid} version={version} level={level} />
      <PdfButton projectUid={projectUid} version={version} pdf={pdf} open={pdfOpen} onToggle={() => setPdfOpen((open) => !open)} />
      <SectionNeighbours projectUid={projectUid} documentUid={documentUid} sectionCode={version.classification?.section_code} level={level} />
      {pdf !== undefined && pdfOpen
        ? pdf.render({ versionUid: version.version_uid, title: drawerTitle, pageCount: version.page_count, onClose: () => setPdfOpen(false) })
        : null}
    </div>
  );
}
