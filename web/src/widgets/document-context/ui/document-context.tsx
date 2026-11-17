'use client';

/**
 * `UI-A-22`, `S4`, `UIP-G-09`: the frame of a document's pages, one widget on all of them — the original's card of a
 * document in our nouns. Three rows:
 *
 *   1. **where the page sits**: «раздел › документ», the section a link to its page and the document a link to its own page
 *      (the list of its versions), as the original's «EOM / МК7-РД-ЭОМ1». A run and the «Разбор» of one add their step; the
 *      comparison adds its version. A document with no confirmed section opens with its object instead, so the row
 *      always has a way up. The version, and its code, are not in the row: the version is the bar's.
 *   2. **the tabs** on the right of it, «Инфо · Блоки N · Лог · Разбор N · Оптимизация N» (`VersionTabs`).
 *   3. **the version bar** (`VersionBar`): the version choice, «Просмотр PDF» and the neighbours in the section; a change of
 *      version or of document keeps the tab.
 *
 * The frame is drawn on the document's own page, its «Оптимизация», the version, its «Блоки», the log and the run, and
 * «Разбор». The section page and the comparison draw the row alone: they have no version in view, so no tab, no bar and
 * no read the screen does not already make.
 *
 * Names come from reads the pages already make or that the query cache shares: the version (title and number) and the
 * run (its version). A page that holds the version (the document page holds its newest) hands it in (`version`) and the
 * frame reads none for the names. The numbers on «Блоки» and «Оптимизация» (`UIP-S04-02`) are the version's own read, the
 * same entry, so the frame reads it for them even then: a version held from a listing carries neither (`useVersionFigures`).
 * A name that is not known yet, or whose read failed, is the generic word («Объект», «Документ»); the row never invents a
 * name and never blocks the page, and a number the read did not give is not drawn.
 */

import type { ReactNode } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import type { DocumentVersion, RunId, VersionUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import { runStatusQueryOptions } from '@/entities/audit-run';
import { useDocumentVersion } from '@/entities/document-version';
import { findProjectSection, useProject } from '@/entities/project';

import type { TabLevel } from '../model/version-tabs';
import { useVersionFigures } from '../api/use-version-figures';
import { VersionBar } from './version-bar';
import type { PdfSlot } from './version-bar';
import { VersionTabs } from './version-tabs';

import styles from './document-context.module.css';

/** The places a frame can be on: the levels of the tabs, and the two that draw the row alone. */
export type ContextLevel = TabLevel | 'section' | 'comparison';

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
  /** The version the page already holds (the document page's newest); the frame then reads none of its own. */
  readonly version?: DocumentVersion | undefined;
  /** The PDF window of the page, when the page has one; the button of the bar opens it in place. */
  readonly pdf?: PdfSlot | undefined;
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
   * with the section a link to its page; ours opens with the section, a link to the section page, and draws the
   * object in its place for a document with no confirmed section.
   */
  readonly sectionCode?: string | undefined;
}

/** The levels that draw the tabs and the version bar: the pages of one document, each with its version in view. */
const FRAMED: readonly ContextLevel[] = ['document', 'optimisation', 'version', 'blocks', 'log', 'run', 'review'];

/**
 * The steps of the row, pure: the last reached level is the current one and carries no link. «раздел › документ», then the
 * step of the level when it is under the document and not a tab (a run, the «Разбор» of one, the comparison).
 */
export function contextSteps(facts: ContextFacts, current: ContextLevel): readonly ContextStep[] {
  const object: ContextStep = { key: 'project', label: facts.projectName ?? 'Объект', href: routes.project(facts.projectUid) };
  if (current === 'section') {
    return [object, { key: 'section', label: facts.sectionLabel ?? 'Раздел', href: null }];
  }
  const section = facts.sectionCode === undefined ? null : findProjectSection(facts.sectionCode);
  const steps: ContextStep[] = [
    section === null
      ? object
      : {
          key: 'section',
          label: section.abbr,
          title: `${section.abbr} ${section.name}`,
          href: routes.projectSection(facts.projectUid, section.code),
        },
  ];
  if (facts.documentUid !== undefined) {
    steps.push({
      key: 'document',
      label: facts.documentTitle ?? 'Документ',
      href: current === 'document' ? null : routes.document(facts.projectUid, facts.documentUid),
    });
  }
  switch (current) {
    case 'comparison':
      // The version's comparison screen ends the row; it is a place under the version, not one of the tabs.
      if (facts.versionUid !== undefined) {
        steps.push({
          key: 'version',
          label: facts.versionOrdinal === undefined ? 'Версия' : `Версия ${facts.versionOrdinal}`,
          href: routes.version(facts.projectUid, facts.versionUid),
        });
      }
      steps.push({ key: 'comparison', label: 'Сравнение', href: null });
      break;
    case 'run':
      if (facts.runId !== undefined) steps.push({ key: 'run', label: 'Прогон', href: null });
      break;
    case 'log':
    case 'review':
      if (facts.runId !== undefined) steps.push({ key: 'run', label: 'Прогон', href: routes.run(facts.projectUid, facts.runId) });
      if (current === 'review' && facts.runId !== undefined) steps.push({ key: 'review', label: 'Разбор', href: null });
      break;
    default:
      break;
  }
  return steps;
}

export function DocumentContext({
  projectUid, current, documentUid, versionUid, runId, sectionLabel, sectionCode, version: held, pdf,
}: DocumentContextProps) {
  const run = useQuery({ ...runStatusQueryOptions((runId ?? '') as RunId), enabled: runId !== undefined && versionUid === undefined });
  const knownVersion = (versionUid as VersionUid | undefined) ?? held?.version_uid ?? run.data?.version_uid;
  const read = useDocumentVersion(held === undefined ? (knownVersion ?? null) : null);
  const version = held ?? read.data;
  // `UI-PARITY-P0N`: the project by its identity, not looked for on the listing's first page.
  const projectName = useProject(projectUid).data?.name;
  const ownDocument = documentUid ?? version?.document_uid;
  const steps = contextSteps(
    {
      projectUid,
      projectName,
      documentUid: ownDocument,
      documentTitle: version?.display_title ?? version?.source_filename ?? undefined,
      versionUid: knownVersion,
      versionOrdinal: version?.version_ordinal,
      runId,
      sectionLabel,
      sectionCode: sectionCode ?? version?.classification?.section_code,
    },
    current,
  );
  // The tabs read the version's runs, so they wait for the version itself (`D-16`: runs are asked for only once the version is known).
  const framed = FRAMED.includes(current) && knownVersion !== undefined && version !== undefined && ownDocument !== undefined;
  const level = current as TabLevel;
  // `UIP-S04-02`: the numbers of «Блоки» and «Оптимизация» are the version's own read, held or not; none while it has not answered.
  const figures = useVersionFigures(framed ? knownVersion : undefined);
  let tabs: ReactNode = null;
  let bar: ReactNode = null;
  if (framed) {
    tabs = (
      <VersionTabs
        projectUid={projectUid}
        versionUid={knownVersion}
        documentUid={ownDocument}
        current={level}
        blockCount={figures?.blockCount}
        optimisation={figures?.optimisation}
      />
    );
    bar = <VersionBar projectUid={projectUid} documentUid={ownDocument} version={version} level={level} pdf={pdf} />;
  }
  return (
    <div className={styles.frame} data-context-level={current}>
      <div className={styles.bar}>
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
        </nav>
        {tabs === null ? null : <div className={styles.aside}>{tabs}</div>}
      </div>
      {bar}
    </div>
  );
}
