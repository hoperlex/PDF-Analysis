'use client';

/**
 * `UI-A-22`, `S4`: where a document page sits, as the original's strip «объект › проект › …» does in our
 * nouns — «Проекты › Проект › Документ › Версия N › Прогон › Разбор». Every step but the current one is a
 * link built by `routes`; the current one is text with `aria-current="page"`.
 *
 * `comparison` (second UX pass) is the version's comparison screen — «… › Версия N › Сравнение». It ends the strip as
 * «Блоки» does, but it is not one of the version's tabs, so it draws the strip alone: no tab row, no version choice and no
 * neighbours (and, with them, no read the comparison screen does not already make). It replaced a copy of the strip that
 * the screen kept for itself.
 *
 * Names come from reads the pages already make or that the query cache shares: the version (title and
 * number) and the run (its version). A name that is not known yet, or whose read failed, is the generic word
 * («Проект», «Документ»); the strip never invents a name and never blocks the page.
 */

import type { ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import type { DocumentUid, RunId, VersionUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import { runStatusQueryOptions } from '@/entities/audit-run';
import { useDocumentVersion, useVersionList } from '@/entities/document-version';
import { findProjectSection, useProject } from '@/entities/project';

import { SectionNeighbours } from './section-neighbours';
import { VersionTabs } from './version-tabs';

import styles from './document-context.module.css';

export type ContextLevel = 'section' | 'document' | 'version' | 'blocks' | 'comparison' | 'run' | 'review';

/** Identities as the route gave them (already shape-checked by the page). */
export interface DocumentContextProps {
  readonly projectUid: string;
  readonly current: ContextLevel;
  readonly documentUid?: string | undefined;
  readonly versionUid?: string | undefined;
  readonly runId?: string | undefined;
  /** `R-151l`: on the section page, the section's worded label. */
  readonly sectionLabel?: string | undefined;
  /**
   * `UI-A-23`: the section the document's current version is confirmed for, when the page already knows it (the
   * document page does). A version-level page takes it from the version it reads.
   */
  readonly sectionCode?: string | undefined;
  /** What the page puts at the row's end (the document page's «N из M»); drawn beside the version's own tabs. */
  readonly aside?: ReactNode | undefined;
}

export interface ContextStep {
  readonly key: string;
  readonly label: string;
  readonly href: string | null;
  /** The step's full name when its label is short (a section's abbreviation). */
  readonly title?: string | undefined;
}

export interface ContextFacts {
  readonly projectUid: string;
  readonly projectName?: string | undefined;
  readonly documentUid?: string | undefined;
  readonly documentTitle?: string | undefined;
  readonly versionUid?: string | undefined;
  readonly versionOrdinal?: number | undefined;
  readonly runId?: string | undefined;
  /** `R-151l`: the section page's own step, its label already worded. */
  readonly sectionLabel?: string | undefined;
  /**
   * `UI-A-23`: the section the document is confirmed for. The original's strip opens «<код раздела> / <имя проекта>»
   * with the section a link to its page; ours puts the section between the project and the document, a link to the
   * section page, and draws nothing for a document with no confirmed section.
   */
  readonly sectionCode?: string | undefined;
}

const ORDER: readonly ContextLevel[] = ['document', 'version', 'run', 'review'];

/** The steps of the strip, pure: the last reached level is the current one and carries no link. */
export function contextSteps(facts: ContextFacts, current: ContextLevel): readonly ContextStep[] {
  const depth = ORDER.indexOf(current);
  const steps: ContextStep[] = [
    { key: 'projects', label: 'Проекты', href: routes.projects() },
    { key: 'project', label: facts.projectName ?? 'Проект', href: routes.project(facts.projectUid) },
  ];
  if (current === 'section') {
    steps.push({ key: 'section', label: facts.sectionLabel ?? 'Раздел', href: null });
    return steps;
  }
  const section = facts.sectionCode === undefined ? null : findProjectSection(facts.sectionCode);
  if (section !== null) {
    steps.push({
      key: 'section',
      label: section.abbr,
      title: `${section.abbr} ${section.name}`,
      href: routes.projectSection(facts.projectUid, section.code),
    });
  }
  if (facts.documentUid !== undefined) {
    steps.push({
      key: 'document',
      label: facts.documentTitle ?? 'Документ',
      href: current === 'document' ? null : routes.document(facts.projectUid, facts.documentUid),
    });
  }
  if ((depth >= 1 || current === 'blocks' || current === 'comparison') && facts.versionUid !== undefined) {
    steps.push({
      key: 'version',
      label: facts.versionOrdinal === undefined ? 'Версия' : `Версия ${facts.versionOrdinal}`,
      href: current === 'version' ? null : routes.version(facts.projectUid, facts.versionUid),
    });
  }
  if (current === 'blocks') {
    // `R-151m`: the version's «Блоки» tab ends the strip.
    steps.push({ key: 'blocks', label: 'Блоки', href: null });
    return steps;
  }
  if (current === 'comparison') {
    // The version's comparison screen ends the strip; it is a place under the version, not one of its tabs.
    steps.push({ key: 'comparison', label: 'Сравнение', href: null });
    return steps;
  }
  if (depth >= 2 && facts.runId !== undefined) {
    steps.push({ key: 'run', label: 'Прогон', href: current === 'run' ? null : routes.run(facts.projectUid, facts.runId) });
  }
  if (depth >= 3 && facts.runId !== undefined) {
    steps.push({ key: 'review', label: 'Разбор', href: null });
  }
  return steps;
}


/**
 * `UI-A-24`: on the version page the strip also lets the reader move to another version of the same
 * document, as the original's V# choice does. It lists the first page of the document's versions; a
 * longer history says so instead of hiding the rest.
 */
function VersionSwitch({ projectUid, documentUid, versionUid, onBlocks }: {
  readonly projectUid: string;
  readonly documentUid: string;
  readonly versionUid: string;
  /** On the «Блоки» tab the choice stays on «Блоки» of the other version; elsewhere it opens that version. */
  readonly onBlocks: boolean;
}) {
  const router = useRouter();
  const versions = useVersionList(documentUid as DocumentUid);
  const items = versions.data?.items ?? [];
  if (items.length < 2) return null;
  const more = (versions.data?.page.next_cursor ?? null) !== null;
  return (
    <label className={styles.switch}>
      <span>Версия</span>
      <select
        value={versionUid}
        onChange={(event) => {
          router.push(onBlocks ? routes.versionBlocks(projectUid, event.target.value) : routes.version(projectUid, event.target.value));
        }}
      >
        {items.map((item, index) => (
          <option key={item.version_uid} value={item.version_uid}>
            {/* The list is newest first and the newest is the document's current version, as the original's «· текущая». */}
            {`Версия ${item.version_ordinal}${index === 0 ? ' · текущая' : ''}`}
          </option>
        ))}
      </select>
      {more ? <span className={styles.more}>показаны первые {items.length}</span> : null}
    </label>
  );
}

export function DocumentContext({ projectUid, current, documentUid, versionUid, runId, sectionLabel, sectionCode, aside }: DocumentContextProps) {
  const run = useQuery({ ...runStatusQueryOptions((runId ?? '') as RunId), enabled: runId !== undefined && versionUid === undefined });
  const knownVersion = (versionUid as VersionUid | undefined) ?? run.data?.version_uid;
  const version = useDocumentVersion(knownVersion ?? null);
  // `UI-PARITY-P0N`: the project by its identity, not looked for on the listing's first page.
  const projectName = useProject(projectUid).data?.name;
  const steps = contextSteps(
    {
      projectUid,
      projectName,
      documentUid: documentUid ?? version.data?.document_uid,
      documentTitle: version.data?.display_title ?? version.data?.source_filename ?? undefined,
      versionUid: knownVersion,
      versionOrdinal: version.data?.version_ordinal,
      runId,
      sectionLabel,
      sectionCode: sectionCode ?? version.data?.classification?.section_code,
    },
    current,
  );
  const ownDocument = documentUid ?? version.data?.document_uid;
  // `UI-A-22`, `R-151m`: as the original's strip follows its project through «Инфо», «Блоки» and «Замечания», the row
  // carries the version's tabs on the version, its «Блоки», a run and the «Разбор» of one, and `UI-A-28` the document's
  // place among the section's.
  const tabLevel = current === 'section' || current === 'document' || current === 'comparison' ? null : current;
  return (
    <div className={styles.bar} data-context-level={current}>
      <nav className={styles.strip} aria-label="Где вы находитесь">
        <ol className={styles.steps}>
          {steps.map((step) => (
            <li key={step.key} className={styles.step} data-context-step={step.key}>
              {step.href === null ? (
                <span aria-current="page" className={styles.current}>
                  {step.label}
                </span>
              ) : (
                <Link href={step.href} title={step.title}>{step.label}</Link>
              )}
            </li>
          ))}
        </ol>
        {tabLevel !== null && knownVersion !== undefined && ownDocument !== undefined ? (
          <VersionSwitch projectUid={projectUid} documentUid={ownDocument} versionUid={knownVersion} onBlocks={current === 'blocks'} />
        ) : null}
      </nav>
      {(tabLevel !== null && knownVersion !== undefined) || aside !== undefined ? (
        <div className={styles.aside}>
          {aside}
          {tabLevel !== null && knownVersion !== undefined ? (
            <>
              <SectionNeighbours projectUid={projectUid} documentUid={ownDocument ?? ''} sectionCode={ownDocument === undefined ? undefined : version.data?.classification?.section_code} />
              {/* The tabs read the version's runs, so they wait for the version itself (`D-16`: runs are asked for only once the version is known). */}
              {version.data === undefined ? null : (
                <VersionTabs projectUid={projectUid} versionUid={knownVersion} documentUid={ownDocument} current={tabLevel} />
              )}
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
